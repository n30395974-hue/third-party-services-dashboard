# Third-Party Services Dashboard

This project connects **Claude Code** (Anthropic's AI coding assistant) to four online
services — **Gmail, GitHub, Notion, and Slack** — using each vendor's **official MCP server**.
Claude Code downloads data from those services into local files with a documented format,
and a small **local dashboard website** lets you search all of that data at once, e.g. find
every email, repo, Notion page, and Slack message that mentions "Joe Smith".

Built by Noah Beitler (solo) for *AI Assisted Development of Products and Services*, HW2.
Gmail, GitHub, and Notion are required by the assignment; **Slack** is the additional service.

> All accounts used here are **test accounts created for this assignment**. No personal,
> school, or work data is in this repository.

---

## How it works

```
 Gmail ─┐                                      ┌─────────────────────────┐
 GitHub ─┤  official    ┌───────────────┐  save │ dataExports/            │  read  ┌───────────┐
 Notion ─┤  MCP server ─▶│  Claude Code  │──────▶│   gmail/ github/        │───────▶│ Dashboard │
 Slack  ─┘  (.mcp.json)  │ + skill       │       │   notion/ slack/        │        │ (local    │
                         └───────────────┘       │ (localStorageFormats.md)│        │  website) │
                                                 └─────────────────────────┘        └───────────┘
```

1. **MCP servers** (Model Context Protocol) are how Claude Code talks to outside services. The
   four official servers are configured in [`.mcp.json`](.mcp.json).
2. A **project skill**, [`.claude/skills/download-service-data/`](.claude/skills/download-service-data/SKILL.md),
   tells Claude Code exactly how to download items and save them, so every download follows
   the same format.
3. Downloads land in [`dataExports/`](dataExports/), one sub-folder per service and one folder
   per item. The format is specified in [`localStorageFormats.md`](localStorageFormats.md).
4. The **dashboard** in [`dashboard/`](dashboard/) reads those files and lets you search them.

## What's in this repo

| Path | What it is |
|---|---|
| [`dataExports/`](dataExports/) | The downloaded data, one sub-folder per service. |
| [`localStorageFormats.md`](localStorageFormats.md) | Specification of the local storage format. |
| [`.claude/skills/download-service-data/`](.claude/skills/download-service-data/) | The Claude Code skill for downloading, plus `save_items.py` (writes files in the right format) and `validate_exports.py` (checks them). |
| [`.mcp.json`](.mcp.json) | MCP server configuration. Contains **no secrets**. |
| [`dashboard/`](dashboard/) | The dashboard web app (Python server + HTML/CSS/JS) and its tests. |
| [`presentation/`](presentation/) | PowerPoint presentation and demo video. |

---

## Running the dashboard

Requirements: **Python 3.8 or newer**. Nothing to install; it uses only the standard library.
Check with `python3 --version`.

```bash
python3 dashboard/server.py
```

Open **http://localhost:8000** in your browser.

- **Search across all services:** type in the search box, e.g. `Joe Smith`. Every word must
  match. Use quotes for an exact phrase: `"study group"`.
- **Pick services:** click a service chip (Gmail, GitHub, Notion, Slack) to show only that
  service; click several to combine them; click **All services** to reset. Each chip shows how
  many results that service has for the current search.
- Every result is labelled and colour-coded with the service it came from. Expand
  **Full content & metadata** to see the whole item, all its metadata, and the local folder it
  was read from.
- After downloading new data, just refresh the page.

Options: `--port 8080` to use a different port, `--data /path/to/dataExports` to read another
folder. Stop the server with `Ctrl+C`.

The server only listens on `127.0.0.1`, so the data is never reachable from other computers.

---

## Connecting the services (to reproduce the downloads)

You need [Claude Code](https://code.claude.com) installed, and a **test account** for each
service. Don't use real accounts.

Start Claude Code from this folder (`claude`). It reads `.mcp.json` and asks you to approve
the project's MCP servers. Then authenticate each one:

### Notion and Slack
Run `/mcp` inside Claude Code, choose the server, and sign in with your test account in the
browser window that opens (OAuth). For Slack, use a test workspace you created (you're its
admin, so you can approve the connection).

### GitHub
The official GitHub server authenticates with a personal access token (PAT) for your **test**
GitHub account:
1. On the test account: *Settings → Developer settings → Personal access tokens → Fine-grained
   tokens*. Grant read-only access to repositories, issues, and pull requests.
2. Put the token in your shell environment, never in a file in this repo:
   ```bash
   export GITHUB_PAT=github_pat_xxxxxxxx   # add to ~/.zshrc or ~/.bashrc to keep it
   ```
   `.mcp.json` reads it via `${GITHUB_PAT}`.

### Gmail
Google's official Gmail MCP server needs an OAuth client from a Google Cloud project owned by
your **test** Google account:
1. In the [Google Cloud console](https://console.cloud.google.com) create a project, then enable
   the **Gmail API** and the **Gmail MCP API** (`gcloud services enable gmailmcp.googleapis.com`).
2. Configure the OAuth consent screen (External, add your test account as a test user, add the
   `gmail.readonly` scope).
3. Create an OAuth client ID of type **Web application** with the authorized redirect URI
   `http://localhost:8765/callback`.
4. Register it with Claude Code. The client secret goes into your system keychain, not into
   `.mcp.json`:
   ```bash
   claude mcp remove gmail --scope project
   claude mcp add-json --scope project gmail \
     '{"type":"http","url":"https://gmailmcp.googleapis.com/mcp/v1","oauth":{"clientId":"YOUR_CLIENT_ID.apps.googleusercontent.com","callbackPort":8765}}' \
     --client-secret
   ```
5. Run `/mcp`, choose `gmail`, and sign in with the test account.

Run `claude mcp list` to check that all four servers show as connected.

## Downloading data

In Claude Code, ask in plain English. The `download-service-data` skill handles the rest:

- `download the emails I received in the past day`
- `download all my GitHub repositories and their open issues`
- `download every Notion page that mentions Joe Smith`
- `download this week's messages from #general in Slack`

Re-downloading an item overwrites its folder; it never creates duplicates. To check that
everything matches the documented format:

```bash
python3 .claude/skills/download-service-data/scripts/validate_exports.py
```

## Tests

```bash
python3 -m unittest discover -s dashboard/tests -v
```

The tests use **fake** sample data from `dashboard/tests/fixture_batches/` (marked
`TEST FIXTURE`) and write only to temporary folders, never to `dataExports/`.

## Security

- **No credentials in the repo.** `.mcp.json` uses OAuth (tokens kept by Claude Code / your
  keychain) or `${GITHUB_PAT}` from your environment. `.gitignore` excludes `.env` files and
  credential files. `save_items.py` and `validate_exports.py` refuse anything that looks like a
  token.
- **Test accounts only.** Everything in `dataExports/` is from throwaway accounts.
- **Local only.** The dashboard binds to `127.0.0.1` and serves only its own four files.
- **Untrusted content is never rendered as HTML.** Emails and messages are displayed as plain
  text, so a malicious email can't run scripts in the dashboard.
