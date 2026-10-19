#!/usr/bin/env python3
"""Write downloaded items to dataExports/ in the format defined by localStorageFormats.md.

Usage:
    python3 .claude/skills/download-service-data/scripts/save_items.py BATCH.json [--root REPO_ROOT]

BATCH.json:
{
  "service": "gmail",
  "request": "download emails received in the past 30 minutes",
  "tools": ["search_threads", "get_thread"],
  "items": [
    {"type": "email", "sourceId": "...", "title": "...", "author": "...",
     "url": "...", "fields": {...}, "content": "plain text / markdown body"}
  ]
}

The folder name, primaryTime, schemaVersion, exportedAt, exportedVia and the content.md
heading are derived here, so callers can't get them wrong. Re-saving an item overwrites
its folder. Exits 1 if any item was rejected.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import exportformat as fmt

REPO_ROOT = Path(__file__).resolve().parents[4]


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build(service, item, request, tools, exported_at):
    """Return (folder_name, metadata, content_md) or raise ValueError with all problems."""
    problems = []
    for key in ("type", "sourceId", "title", "author", "fields"):
        if key not in item:
            problems.append(f"missing item.{key}")
    if problems:
        raise ValueError("; ".join(problems))

    item_type, fields = item["type"], dict(item["fields"])
    problems = fmt.check_item(service, item_type, fields)
    if problems:
        raise ValueError("; ".join(problems))

    for key in fmt.TIME_FIELDS:
        if fields.get(key) is not None:
            fields[key] = fmt.to_utc_iso(fields[key])

    title = str(item["title"]).strip() or "(no title)"
    metadata = {
        "schemaVersion": fmt.SCHEMA_VERSION,
        "service": service,
        "type": item_type,
        "sourceId": str(item["sourceId"]),
        "title": title,
        "author": str(item["author"]),
        "primaryTime": fmt.primary_time(service, item_type, fields),
        "url": item.get("url"),
        "exportedAt": exported_at,
        "exportedVia": {"mcpServer": service, "tools": list(tools), "request": request},
        "fields": fields,
    }

    body = (item.get("content") or "").strip()
    if not body:
        body = "_No README._" if item_type == "repository" else "_No content._"
    content_md = f"# {fmt.content_heading(service, title, fields)}\n\n{body}\n"

    serialized = json.dumps(metadata, ensure_ascii=False) + content_md
    leaked = fmt.SECRET_RE.search(serialized)
    if leaked:
        raise ValueError(f"refusing to write: looks like a credential ({leaked.group(0)[:12]}...)")

    folder = fmt.folder_name(service, item_type, metadata["sourceId"], title, fields)
    return folder, metadata, content_md


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("batch", type=Path, help="JSON batch file (see docstring)")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repo root containing dataExports/")
    args = parser.parse_args()

    batch = json.loads(args.batch.read_text(encoding="utf-8"))
    service = batch.get("service")
    if service not in fmt.SERVICES:
        sys.exit(f"error: batch.service must be one of {', '.join(fmt.SERVICES)}, got {service!r}")
    request = batch.get("request") or ""
    if not request:
        sys.exit("error: batch.request (the natural-language download request) is required")
    tools = batch.get("tools") or []
    items = batch.get("items") or []

    service_dir = args.root / "dataExports" / service
    service_dir.mkdir(parents=True, exist_ok=True)
    exported_at = now_iso()

    created, updated, failed = [], [], 0
    for index, item in enumerate(items):
        try:
            folder, metadata, content_md = build(service, item, request, tools, exported_at)
        except (ValueError, KeyError, TypeError) as exc:
            failed += 1
            print(f"REJECTED item {index} ({item.get('sourceId', '?')}): {exc}", file=sys.stderr)
            continue
        item_dir = service_dir / folder
        (updated if item_dir.exists() else created).append(folder)
        item_dir.mkdir(exist_ok=True)
        (item_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (item_dir / "content.md").write_text(content_md, encoding="utf-8")

    if created or updated:
        log_line = {
            "exportedAt": exported_at,
            "request": request,
            "itemCount": len(created) + len(updated),
            "created": created,
            "updated": updated,
        }
        with open(service_dir / "_export-log.jsonl", "a", encoding="utf-8") as log:
            log.write(json.dumps(log_line, ensure_ascii=False) + "\n")

    print(f"{service}: {len(created)} created, {len(updated)} updated, {failed} rejected -> {service_dir}")
    for folder in created:
        print(f"  + {folder}")
    for folder in updated:
        print(f"  ~ {folder}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
