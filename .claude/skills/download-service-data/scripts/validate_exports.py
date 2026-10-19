#!/usr/bin/env python3
"""Check dataExports/ against localStorageFormats.md. Exits 1 if anything is invalid.

Usage:
    python3 .claude/skills/download-service-data/scripts/validate_exports.py [--root REPO_ROOT]
"""

import argparse
import json
import sys
from pathlib import Path

import exportformat as fmt

REPO_ROOT = Path(__file__).resolve().parents[4]
MIN_ITEMS = 5  # assignment minimum per service


def validate_item(service, item_dir):
    errors = []
    match = fmt.ITEM_DIR_RE.match(item_dir.name)
    if not match:
        return [f"folder name does not match <YYYY-MM-DD_HH-MM-SS>__<slug>__<id8>"]

    meta_path, content_path = item_dir / "metadata.json", item_dir / "content.md"
    if not meta_path.is_file():
        errors.append("missing metadata.json")
    if not content_path.is_file():
        errors.append("missing content.md")
    extras = sorted(p.name for p in item_dir.iterdir() if p.name not in ("metadata.json", "content.md"))
    if extras:
        errors.append(f"unexpected files: {', '.join(extras)}")
    if errors:
        return errors

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"metadata.json is not valid JSON: {exc}"]

    missing = [k for k in fmt.ENVELOPE_KEYS if k not in meta]
    if missing:
        return [f"metadata.json missing envelope keys: {', '.join(missing)}"]
    if meta["schemaVersion"] != fmt.SCHEMA_VERSION:
        errors.append(f"schemaVersion is {meta['schemaVersion']}, expected {fmt.SCHEMA_VERSION}")
    if meta["service"] != service:
        errors.append(f"service is {meta['service']!r} but item is in the {service}/ folder")

    problems = fmt.check_item(service, meta["type"], meta["fields"])
    if problems:
        return errors + problems

    try:
        expected_time = fmt.primary_time(service, meta["type"], meta["fields"])
        expected_name = fmt.folder_name(service, meta["type"], meta["sourceId"], meta["title"], meta["fields"])
    except (ValueError, KeyError, TypeError) as exc:
        return errors + [f"cannot derive folder name from metadata: {exc}"]
    if meta["primaryTime"] != expected_time:
        errors.append(f"primaryTime {meta['primaryTime']} does not match fields ({expected_time})")
    if item_dir.name != expected_name:
        errors.append(f"folder should be named {expected_name}")

    for key in ("exportedAt", "primaryTime"):
        try:
            if fmt.to_utc_iso(meta[key]) != meta[key]:
                errors.append(f"{key} must be ISO 8601 UTC like 2026-10-19T08:15:59Z")
        except (ValueError, TypeError, AttributeError):
            errors.append(f"{key} is not a valid timestamp")

    content = content_path.read_text(encoding="utf-8")
    if not content.startswith("# "):
        errors.append("content.md must start with a '# ' heading line")
    if fmt.SECRET_RE.search(meta_path.read_text(encoding="utf-8") + content):
        errors.append("contains something that looks like a credential")
    return errors


def validate_log(log_path):
    errors = []
    for number, line in enumerate(log_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"{log_path.name} line {number}: not valid JSON")
            continue
        for key in ("exportedAt", "request", "itemCount", "created", "updated"):
            if key not in entry:
                errors.append(f"{log_path.name} line {number}: missing {key}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repo root containing dataExports/")
    args = parser.parse_args()

    exports = args.root / "dataExports"
    if not exports.is_dir():
        sys.exit(f"error: {exports} does not exist")

    total_errors = 0
    for entry in sorted(exports.iterdir()):
        if entry.name.startswith(".") or not entry.is_dir():
            continue
        if entry.name not in fmt.SERVICES:
            print(f"ERROR dataExports/{entry.name}: not a known service folder ({', '.join(fmt.SERVICES)})")
            total_errors += 1
    for service in fmt.SERVICES:
        service_dir = exports / service
        if not service_dir.is_dir():
            print(f"WARN  {service}: folder missing")
            continue
        count = 0
        for item_dir in sorted(service_dir.iterdir()):
            if item_dir.name.startswith(("_", ".")):
                if item_dir.name == "_export-log.jsonl":
                    for err in validate_log(item_dir):
                        print(f"ERROR {service}/{err}")
                        total_errors += 1
                continue
            if not item_dir.is_dir():
                print(f"ERROR {service}/{item_dir.name}: stray file (items must be folders)")
                total_errors += 1
                continue
            count += 1
            for err in validate_item(service, item_dir):
                print(f"ERROR {service}/{item_dir.name}: {err}")
                total_errors += 1
        note = f"  (assignment needs at least {MIN_ITEMS})" if count < MIN_ITEMS else ""
        print(f"{'WARN ' if note else 'OK   '} {service}: {count} items{note}")

    print("valid" if total_errors == 0 else f"{total_errors} error(s)")
    sys.exit(1 if total_errors else 0)


if __name__ == "__main__":
    main()
