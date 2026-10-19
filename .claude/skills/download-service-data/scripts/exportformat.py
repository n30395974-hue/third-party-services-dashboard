"""Rules from localStorageFormats.md, as code. Shared by save_items.py and validate_exports.py."""

import hashlib
import re
from datetime import datetime, timezone

SCHEMA_VERSION = 1

SERVICES = ("gmail", "github", "notion", "slack")

ALLOWED_TYPES = {
    "gmail": ("email",),
    "github": ("repository", "issue", "pull_request"),
    "notion": ("page",),
    "slack": ("message",),
}

ENVELOPE_KEYS = (
    "schemaVersion", "service", "type", "sourceId", "title", "author",
    "primaryTime", "url", "exportedAt", "exportedVia", "fields",
)

_ISSUE_FIELDS = ("repository", "number", "state", "labels", "assignees", "createdAt")
REQUIRED_FIELDS = {
    ("gmail", "email"): ("from", "to", "receivedAt", "threadId", "labels", "attachments"),
    ("github", "repository"): ("owner", "name", "fullName", "description", "visibility", "createdAt"),
    ("github", "issue"): _ISSUE_FIELDS,
    ("github", "pull_request"): _ISSUE_FIELDS,
    ("notion", "page"): ("parent", "createdTime", "lastEditedTime", "properties"),
    ("slack", "message"): ("channel", "user", "ts", "threadTs", "replyCount"),
}

# Fields holding timestamps, normalized to ISO 8601 UTC on save.
TIME_FIELDS = ("receivedAt", "createdAt", "updatedAt", "pushedAt", "closedAt",
               "createdTime", "lastEditedTime")

ITEM_DIR_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})__([a-z0-9-]{1,60})__([0-9a-f]{8})$")

# Things that look like credentials. Exports must never contain these.
SECRET_RE = re.compile(
    r"(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|gho_[A-Za-z0-9]{20,}"
    r"|xox[abprs]-[A-Za-z0-9-]{10,}|ya29\.[A-Za-z0-9_-]{20,}|ntn_[A-Za-z0-9]{20,}"
    r"|secret_[A-Za-z0-9]{30,}|Bearer\s+[A-Za-z0-9._-]{20,})"
)


def to_utc_iso(value):
    """Normalize an ISO string or epoch number (s or ms) to 'YYYY-MM-DDTHH:MM:SSZ'."""
    if value is None:
        return None
    if isinstance(value, (int, float)) or (isinstance(value, str) and re.fullmatch(r"\d+(\.\d+)?", value)):
        seconds = float(value)
        if seconds > 1e11:  # milliseconds
            seconds /= 1000.0
        dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
    else:
        text = value.strip().replace("Z", "+00:00").replace("z", "+00:00")
        # Python < 3.11 only accepts 0, 3 or 6 fractional digits.
        text = re.sub(r"\.(\d+)", lambda m: "." + (m.group(1) + "000000")[:6], text)
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_to_folder_stamp(iso):
    return iso.replace("T", "_").replace(":", "-").rstrip("Z")


def slugify(text):
    s = (text or "").lower().replace("@", "-at-").replace(".", "-dot-")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    s = s[:60].strip("-")
    return s or "untitled"


def id8(service, source_id):
    return hashlib.sha1(f"{service}:{source_id}".encode("utf-8")).hexdigest()[:8]


def primary_time(service, item_type, fields):
    """The instant an item is filed under, derived from its service-specific fields."""
    if service == "gmail":
        return to_utc_iso(fields["receivedAt"])
    if service == "github":
        return to_utc_iso(fields["createdAt"])
    if service == "notion":
        return to_utc_iso(fields["createdTime"])
    if service == "slack":
        return to_utc_iso(fields["ts"])
    raise ValueError(f"unknown service {service!r}")


def slug_source(service, item_type, title, fields):
    if service == "gmail":
        return fields["from"]["email"]
    if service == "github":
        if item_type == "repository":
            return f"{item_type}-{fields['owner']}-{fields['name']}"
        return f"{item_type}-{fields['repository']}-{fields['number']}"
    if service == "notion":
        return title
    if service == "slack":
        return f"{fields['channel']['name']}-{fields['user']['name']}"
    raise ValueError(f"unknown service {service!r}")


def folder_name(service, item_type, source_id, title, fields):
    stamp = iso_to_folder_stamp(primary_time(service, item_type, fields))
    slug = slugify(slug_source(service, item_type, title, fields))
    return f"{stamp}__{slug}__{id8(service, source_id)}"


def content_heading(service, title, fields):
    if service == "slack":
        return f"#{fields['channel']['name']} — {fields['user']['name']}"
    return title


def check_item(service, item_type, fields):
    """Return a list of problems with the service/type/required-fields combination."""
    problems = []
    if service not in SERVICES:
        return [f"unknown service {service!r} (expected one of {', '.join(SERVICES)})"]
    if item_type not in ALLOWED_TYPES[service]:
        return [f"type {item_type!r} not allowed for {service} (expected one of {', '.join(ALLOWED_TYPES[service])})"]
    if not isinstance(fields, dict):
        return ["'fields' must be an object"]
    for key in REQUIRED_FIELDS[(service, item_type)]:
        if key not in fields:
            problems.append(f"missing required field fields.{key} (use null or [] if the service has no value)")
    if service == "gmail" and isinstance(fields.get("from"), dict) and not fields["from"].get("email"):
        problems.append("fields.from.email is required")
    if service == "slack":
        for key in ("channel", "user"):
            if isinstance(fields.get(key), dict) and not fields[key].get("name"):
                problems.append(f"fields.{key}.name is required")
    return problems
