---
name: download-service-data
description: Download data from Gmail, GitHub, Notion, or Slack through their official MCP servers and store it locally in dataExports/ using this project's documented format. Use whenever the user asks to download, export, fetch, pull, back up, or save emails, repos, issues, Notion pages, or Slack messages to disk.
---

# Download service data

Downloads items from a connected service and saves them under `dataExports/<service>/`
in the format specified by **`localStorageFormats.md`** (repo root). That file is the source
of truth. Read it before your first download in a conversation.

Never write files into `dataExports/` by hand. Always go through `scripts/save_items.py`,
which derives folder names, timestamps, and headings so every download is consistent.

## Steps

1. **Pin down the request.** Identify the service and the scope ("emails from the past
   30 minutes", "all repos", "Notion pages mentioning X", "messages in #general this week").
   If it's ambiguous, ask once. The assignment needs **at least 5 items per service**.

2. **Check the connection.** The servers are defined in `.mcp.json`: `gmail`, `github`,
   `notion`, `slack`. Their tools appear as `mcp__<server>__<tool>`. If a server's tools aren't
   available, stop and tell the user to run `/mcp` to authenticate it (see README.md). Do
   not fall back to a different, unofficial server.

3. **Fetch with the official server's tools.** Use its search/list tool to find matching
   items, then its read/get tool for each item's full content and metadata (see per-service
   notes below). Tool names differ between servers and versions; pick by what the tool does.

4. **Build a batch file** in the scratch/temp directory (not in the repo), shaped like:

   ```json
   {
     "service": "gmail",
     "request": "<the user's request, verbatim>",
     "tools": ["<MCP tool names you actually called>"],
     "items": [
       {
         "type": "email",
         "sourceId": "<the service's own ID>",
         "title": "<subject / repo full name / issue title / page title / first line of message>",
         "author": "<sender / owner / creator / poster>",
         "url": "<link to the item in the service, or null>",
         "fields": { "...service-specific, see localStorageFormats.md section 3.2..." },
         "content": "<body only; the script adds the '# heading' line>"
       }
     ]
   }
   ```

   - Fill **every required field** listed in `localStorageFormats.md` 3.2 for that service and
     type. Use `null` or `[]` when the service has no value. Never omit a required field.
   - Timestamps can be ISO strings or epoch seconds/milliseconds; the script normalizes them.
   - Copy values from the MCP responses. Never invent or guess data.
   - Never put tokens, API keys, or auth headers anywhere in the batch.

5. **Save:**
   ```bash
   python3 .claude/skills/download-service-data/scripts/save_items.py <batch.json>
   ```
   It prints each folder as `+` (new) or `~` (re-downloaded, overwritten) and appends a line
   to `dataExports/<service>/_export-log.jsonl`. If it prints `REJECTED`, fix that item's
   batch entry and re-run. Re-running is safe; nothing duplicates.

6. **Validate:**
   ```bash
   python3 .claude/skills/download-service-data/scripts/validate_exports.py
   ```
   Fix any `ERROR` lines before finishing.

7. **Report** to the user: how many items were created vs. updated per service, and the
   folder paths.

## Per-service notes

### gmail (`type: "email"`)
- Search with a Gmail query (e.g. `newer_than:30m`, `from:joe@example.com`), then read each
  message or thread. One item per **message**, not per thread.
- `sourceId` = the message ID. `title` = Subject. `author` = `Name <email>` from the From header.
- `fields.from` / `to` / `cc` are parsed into `{ "name", "email" }` objects.
- `fields.receivedAt` = the message's internal date (when Gmail received it).
- `fields.attachments` = filename / mimeType / size only. Don't download attachment bytes.
- `content` = the plain-text body. If only HTML exists, convert it to readable text.
- `url` = `https://mail.google.com/mail/u/0/#inbox/<messageId>`.

### github (`type: "repository" | "issue" | "pull_request"`)
- Repositories: list the authenticated user's repos. `sourceId` = `owner/repo`,
  `title` = `owner/repo`, `author` = owner. `content` = the README text (fetch the README
  file); empty if there is none.
- Issues/PRs: `sourceId` = `owner/repo#number`, `title` = issue title, `author` = opener.
  `content` = body, then `## Comments` with `### <author> — <time>` per comment.
- `fields.createdAt` must be the creation time (it decides the folder name).

### notion (`type: "page"`)
- Search the workspace (by text if the user gave one), then fetch each page's content.
- `sourceId` = page ID, `title` = page title, `author` = creator.
- `fields.parent` = `{ type, id, title }`. `fields.properties` = each property as plain text
  (`{}` for a plain page).
- `content` = the page body in Markdown, as returned by the server.

### slack (`type: "message"`)
- Search or read channel history, one item per **top-level message**. Its thread replies
  go inside that item's `content` under `## Thread replies`, not as separate items.
- `sourceId` = `<channelId>/<ts>`. `title` = the first line of the message (max ~80 chars).
  `author` = the poster's display name.
- `fields.channel` / `fields.user` need both `id` and `name`. Look up names if the server
  only returns IDs.
- `fields.ts` is the message timestamp string exactly as Slack returns it.
