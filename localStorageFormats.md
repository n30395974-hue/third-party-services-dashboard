# Local Storage Formats

This document is the **single source of truth** for how data downloaded from third-party
services (through their official MCP servers) is stored on disk in this project.

- The download skill (`.claude/skills/download-service-data/`) writes files in this format.
- The validator (`.claude/skills/download-service-data/scripts/validate_exports.py`) checks it.
- The dashboard (`dashboard/`) reads it.

If this document changes, bump `schemaVersion` and update all three.

---

## 1. Folder layout

```
dataExports/
├── gmail/
│   ├── _export-log.jsonl
│   ├── 2026-10-19_08-15-59__joe-at-example-dot-com__5289bf79/
│   │   ├── metadata.json
│   │   └── content.md
│   └── ...
├── github/
├── notion/
└── slack/
```

- One sub-folder of `dataExports/` per service, named with the service's lowercase name:
  `gmail`, `github`, `notion`, `slack`.
- **One folder per downloaded item** (one email, one repository, one Notion page, one Slack
  message). Every item folder contains exactly two files:
  - `metadata.json` — all metadata, machine-readable (section 3).
  - `content.md` — the human-readable body of the item (section 4).
- Files or folders whose names start with `_` are bookkeeping, not items
  (for example `_export-log.jsonl`, section 5).

### Why this design

| Choice | Reason |
|---|---|
| One folder per item | Each item is self-contained: easy to open, inspect, or delete without touching anything else. |
| Metadata separate from content | Metadata is small, structured JSON that programs (the dashboard) can read reliably. Content can be long free text and is easier to read as its own file. |
| Folder names start with a timestamp | Items sort chronologically in any file browser. |
| Readable slug in the folder name | You can tell what an item is (who sent it, which repo) without opening it. |
| Deterministic short ID in the folder name | Two items can never collide, and **re-downloading the same item writes to the same folder** instead of creating a duplicate. |

---

## 2. Item folder names

```
<YYYY-MM-DD_HH-MM-SS>__<slug>__<id8>
```

Three parts separated by **double underscores** (`__`), so a single `_` or `-` inside a slug
can never be confused with a separator.

| Part | Rule |
|---|---|
| `YYYY-MM-DD_HH-MM-SS` | The item's `primaryTime` (see table below) in **UTC**. UTC is used so the name is the same no matter which time zone the downloading computer is in. |
| `slug` | Built from the service's slug source (table below): lowercased; `@` → `-at-`; `.` → `-dot-`; every other run of characters that is not `a-z` or `0-9` → a single `-`; leading/trailing `-` removed; cut to at most 60 characters. Empty result → `untitled`. |
| `id8` | First 8 hex characters of `sha1("<service>:<sourceId>")`. Deterministic, so the same item always gets the same folder. |

| Service | `primaryTime` is… | Slug source | Example folder name |
|---|---|---|---|
| gmail | when the email was received | sender's email address | `2026-10-19_08-15-59__joe-at-example-dot-com__5289bf79` |
| github | when the repo/issue/PR was created | `<type>-<owner>-<repo>[-<number>]` | `2026-09-30_14-02-11__repository-hw2-test-user-recipe-box__81d0b6aa` |
| notion | when the page was created | page title | `2026-10-02_17-40-00__spring-semester-reading-list__0c4be771` |
| slack | when the message was posted | `<channel>-<user>` | `2026-10-18_21-03-44__general-alice-test__5e27d9f0` |

---

## 3. `metadata.json`

UTF-8 JSON, 2-space indentation. Every item uses the same **envelope**; service-specific
metadata goes inside `fields`.

### 3.1 Envelope (all services)

| Key | Type | Required | Meaning |
|---|---|---|---|
| `schemaVersion` | integer | yes | Version of this spec. Currently `1`. |
| `service` | string | yes | `gmail`, `github`, `notion`, or `slack`. Must match the parent folder. |
| `type` | string | yes | Kind of item (allowed values per service in 3.2). |
| `sourceId` | string | yes | The item's ID in the original service (Gmail message ID, GitHub `owner/repo` or `owner/repo#number`, Notion page ID, Slack `channelId/ts`). |
| `title` | string | yes | Short human title: email subject, repo full name, issue title, page title, or first line of a Slack message. |
| `author` | string | yes | Who created it: email sender, repo owner / issue author, page creator, message poster. |
| `primaryTime` | string | yes | ISO 8601 UTC timestamp with `Z`, e.g. `2026-10-19T08:15:59Z`. Same instant as the folder-name timestamp. |
| `url` | string or null | yes | Link back to the item in the original service, if one exists. |
| `exportedAt` | string | yes | ISO 8601 UTC time this item was last written to disk. |
| `exportedVia` | object | yes | How it was downloaded: `{ "mcpServer": "...", "tools": ["..."], "request": "<the natural-language request>" }`. |
| `fields` | object | yes | Service-specific metadata (3.2). |

### 3.2 `fields` per service

Fields marked **(req)** must be present (use `null` or `[]` when the service has no value).
Others are recorded when the MCP server provides them.

#### gmail — `type: "email"`

| Field | Type | |
|---|---|---|
| `from` | `{ "name": string\|null, "email": string }` | (req) |
| `to` | array of `{ name, email }` | (req) |
| `cc`, `bcc` | array of `{ name, email }` | |
| `receivedAt` | ISO 8601 UTC | (req) |
| `dateHeader` | the raw `Date:` header | |
| `threadId` | string | (req) |
| `labels` | array of strings, e.g. `["INBOX","UNREAD"]` | (req) |
| `snippet` | string | |
| `attachments` | array of `{ filename, mimeType, sizeBytes }` | (req) — metadata only, attachment bytes are not downloaded |

#### github — `type: "repository" | "issue" | "pull_request"`

Repository:

| Field | Type | |
|---|---|---|
| `owner`, `name`, `fullName` | string | (req) |
| `description` | string or null | (req) |
| `visibility` | `public` / `private` | (req) |
| `defaultBranch`, `language`, `homepage` | string or null | |
| `topics` | array of strings | |
| `stars`, `forks`, `openIssues` | integer | |
| `createdAt`, `updatedAt`, `pushedAt` | ISO 8601 UTC | `createdAt` (req) |

Issue / pull request:

| Field | Type | |
|---|---|---|
| `repository` | `owner/repo` | (req) |
| `number` | integer | (req) |
| `state` | `open` / `closed` / `merged` | (req) |
| `labels`, `assignees` | array of strings | (req) |
| `createdAt` | ISO 8601 UTC | (req) |
| `updatedAt`, `closedAt` | ISO 8601 UTC or null | |
| `commentCount` | integer | |

#### notion — `type: "page"`

| Field | Type | |
|---|---|---|
| `parent` | `{ "type": "workspace"\|"page"\|"database", "id": string\|null, "title": string\|null }` | (req) |
| `createdTime`, `lastEditedTime` | ISO 8601 UTC | (req) |
| `createdBy`, `lastEditedBy` | string (name or user ID) | |
| `properties` | object of property name → plain-text value | (req) — `{}` for plain pages |
| `archived` | boolean | |

#### slack — `type: "message"`

| Field | Type | |
|---|---|---|
| `channel` | `{ "id": string, "name": string }` | (req) |
| `user` | `{ "id": string, "name": string }` | (req) |
| `ts` | Slack message timestamp string, e.g. `"1792357424.000200"` | (req) |
| `threadTs` | string or null | (req) |
| `replyCount` | integer | (req) |
| `reactions` | array of `{ name, count }` | |
| `permalink` | string | |
| `edited` | boolean | |

### 3.3 Example (gmail)

```json
{
  "schemaVersion": 1,
  "service": "gmail",
  "type": "email",
  "sourceId": "19a0c2f7d3e4b5a6",
  "title": "Notes from Tuesday's study group",
  "author": "Joe Smith <joe@example.com>",
  "primaryTime": "2026-10-19T08:15:59Z",
  "url": "https://mail.google.com/mail/u/0/#inbox/19a0c2f7d3e4b5a6",
  "exportedAt": "2026-10-19T15:20:03Z",
  "exportedVia": {
    "mcpServer": "gmail",
    "tools": ["search_threads", "get_thread"],
    "request": "download emails received in the past 30 minutes"
  },
  "fields": {
    "from": { "name": "Joe Smith", "email": "joe@example.com" },
    "to": [{ "name": null, "email": "hw2.test.account@gmail.com" }],
    "cc": [],
    "receivedAt": "2026-10-19T08:15:59Z",
    "threadId": "19a0c2f7d3e4b5a6",
    "labels": ["INBOX", "UNREAD"],
    "snippet": "Attaching the notes we went over...",
    "attachments": [
      { "filename": "notes.pdf", "mimeType": "application/pdf", "sizeBytes": 48211 }
    ]
  }
}
```

---

## 4. `content.md`

UTF-8 Markdown. It holds the body of the item; metadata is **not** repeated here except for
a single heading line so the file is readable on its own.

| Service / type | Contents |
|---|---|
| gmail email | `# <subject>`, then the plain-text body. If only HTML was available, it is converted to plain text. |
| github repository | `# <owner/repo>`, then the README's text, or `_No README._` |
| github issue / PR | `# <title>`, the body, then a `## Comments` section with one `### <author> — <time>` sub-heading per comment. |
| notion page | `# <page title>`, then the page content as Markdown, as returned by the Notion MCP server. |
| slack message | `# #<channel> — <user>`, the message text, then a `## Thread replies` section (one `### <user> — <time>` per reply) if it has replies. |

---

## 5. `_export-log.jsonl` (one per service folder)

Each download run **appends one line** of JSON, so there is a history of what was downloaded,
when, and why:

```json
{"exportedAt":"2026-10-19T15:20:03Z","request":"download emails received in the past 30 minutes","itemCount":6,"created":["2026-10-19_08-15-59__joe-at-example-dot-com__5289bf79"],"updated":["..."]}
```

`created` lists item folders that did not exist before this run; `updated` lists ones that were
overwritten because the same item was downloaded again.

---

## 6. Rules

1. **Re-downloading overwrites, never duplicates.** The folder name is derived from the item
   itself, so the same item always lands in the same folder; `metadata.json`, `content.md`,
   and `exportedAt` are refreshed.
2. **No secrets in exports.** Never write OAuth tokens, API keys, passwords, or auth headers
   into any exported file.
3. **Times are UTC**, ISO 8601 with a trailing `Z` in JSON, `YYYY-MM-DD_HH-MM-SS` in folder
   names.
4. **Missing values are explicit**: required fields use `null` or `[]`, never omitted.
5. **Validate after every download**:
   `python3 .claude/skills/download-service-data/scripts/validate_exports.py`

---

## 7. Known limitations

These gaps come from what the official MCP servers expose. They are documented here rather than filled with guesses.

| Area | Limitation |
|---|---|
| Notion `author` | Always `"unknown"` (and `fields.createdBy` is `null`). The Notion MCP tools don't expose who created a page. |
| Notion `createdTime` | Exact for database pages, where it comes from a database query. For other pages it comes from the search result and is accurate only to the minute. It may also be the last-edited time, not the creation time. Because `primaryTime` is derived from it, it also sets the timestamp in those pages' folder names. |
| Notion completeness | Pages are found by keyword search, since there is no "list all pages" tool. A page that matches none of the searches could be missed. |
| Slack `url` | `null`. Per-message permalinks weren't fetched. |
| Slack messages | Automatic "has joined the channel" messages are excluded. |
| Gmail | Only the test emails were exported. Account and security notification emails were excluded because they contain IP and location details. |
