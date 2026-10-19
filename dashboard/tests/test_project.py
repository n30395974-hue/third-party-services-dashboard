"""Tests for the download skill scripts and the dashboard server.

Run from the repo root:  python3 -m unittest discover -s dashboard/tests -v

Uses the clearly-labelled fake batches in fixture_batches/ and writes only to temp dirs,
never to the real dataExports/.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / ".claude" / "skills" / "download-service-data" / "scripts"
BATCHES = Path(__file__).resolve().parent / "fixture_batches"
SERVICES = ("gmail", "github", "notion", "slack")

sys.path.insert(0, str(REPO / "dashboard"))
import server  # noqa: E402


def run(script, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True)


class SkillScriptsTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        for service in SERVICES:
            result = run("save_items.py", BATCHES / f"{service}.json", "--root", self.root)
            self.assertEqual(result.returncode, 0, result.stderr)

    def item_dirs(self, service):
        return sorted(p for p in (self.root / "dataExports" / service).iterdir() if p.is_dir())

    def write_batch(self, batch):
        path = self.root / "batch.json"
        path.write_text(json.dumps(batch))
        return path

    def test_fixtures_validate(self):
        result = run("validate_exports.py", "--root", self.root)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("valid", result.stdout)

    def test_every_item_has_exactly_metadata_and_content(self):
        for service in SERVICES:
            for item_dir in self.item_dirs(service):
                self.assertEqual(sorted(p.name for p in item_dir.iterdir()), ["content.md", "metadata.json"])

    def test_redownload_overwrites_instead_of_duplicating(self):
        before = self.item_dirs("gmail")
        result = run("save_items.py", BATCHES / "gmail.json", "--root", self.root)
        self.assertIn("0 created, 2 updated", result.stdout)
        self.assertEqual(self.item_dirs("gmail"), before)
        log = (self.root / "dataExports" / "gmail" / "_export-log.jsonl").read_text().splitlines()
        self.assertEqual(len(log), 2)

    def test_timestamps_normalized_to_utc(self):
        issue = next(d for d in self.item_dirs("github") if "__issue-" in d.name)
        meta = json.loads((issue / "metadata.json").read_text())
        self.assertEqual(meta["primaryTime"], "2026-10-01T07:00:00Z")  # was 09:00+02:00
        self.assertTrue(issue.name.startswith("2026-10-01_07-00-00__"))

    def test_missing_required_field_is_rejected(self):
        batch = json.loads((BATCHES / "gmail.json").read_text())
        del batch["items"][0]["fields"]["threadId"]
        result = run("save_items.py", self.write_batch(batch), "--root", self.root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("fields.threadId", result.stderr)

    def test_credentials_are_never_written(self):
        batch = json.loads((BATCHES / "slack.json").read_text())
        batch["items"][0]["sourceId"] = "C0FIXTURE/9999999999.000100"
        batch["items"][0]["fields"]["ts"] = "9999999999.000100"
        batch["items"][0]["content"] = "token: xoxb-1234567890-abcdefghij"
        result = run("save_items.py", self.write_batch(batch), "--root", self.root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("credential", result.stderr)
        self.assertEqual(len(self.item_dirs("slack")), 1)

    def test_validator_catches_renamed_folder(self):
        item = self.item_dirs("notion")[0]
        item.rename(item.with_name(item.name.replace("reading-list", "renamed")))
        result = run("validate_exports.py", "--root", self.root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("folder should be named", result.stdout)

    def test_dashboard_loads_all_fixture_items(self):
        items, warnings = server.load_items(self.root / "dataExports")
        self.assertEqual(warnings, [])
        self.assertEqual(sorted({i["service"] for i in items}), sorted(SERVICES))
        self.assertEqual(len(items), 6)
        self.assertEqual([i["time"] for i in items], sorted((i["time"] for i in items), reverse=True))

    def test_dashboard_skips_broken_item_with_warning(self):
        (self.item_dirs("github")[0] / "metadata.json").write_text("{not json")
        items, warnings = server.load_items(self.root / "dataExports")
        self.assertEqual(len(items), 5)
        self.assertEqual(len(warnings), 1)


class DashboardServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(tempfile.mkdtemp())
        run("save_items.py", BATCHES / "gmail.json", "--root", cls.root)
        server.Handler.data_dir = cls.root / "dataExports"
        server.Handler.log_message = lambda *args: None
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        shutil.rmtree(cls.root)

    def get(self, path):
        try:
            with urllib.request.urlopen(self.base + path) as response:
                return response.status, response.headers, response.read()
        except urllib.error.HTTPError as err:
            return err.code, err.headers, err.read()

    def test_api_returns_items(self):
        status, headers, body = self.get("/api/items")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(len(data["items"]), 2)
        self.assertIn("Content-Security-Policy", headers)

    def test_static_files_served(self):
        for path in ("/", "/app.js", "/styles.css"):
            self.assertEqual(self.get(path)[0], 200, path)

    def test_no_access_outside_static_whitelist(self):
        for path in ("/../server.py", "/static/../server.py", "/%2e%2e/server.py", "/dataExports"):
            self.assertEqual(self.get(path)[0], 404, path)


if __name__ == "__main__":
    unittest.main()
