---
name: riffado-notes
description: Fetch the user's Riffado voice-recording notes (Plaud recorder transcripts served by their self-hosted Riffado public API) for a day, a time window, or the latest recording, and turn them into clean English notes. Each note has a short summary, topic sections with Mermaid diagrams, and action items for each speaker, written in plain ASD-STE100-style English. The note uses the recording's Highlight photos (participant lists, slides, whiteboards, prescriptions) for names, exact terms and values. Use it whenever the user says "grab my riffado notes", "latest riffado notes for today", "what did I record this morning", "notes from my 3pm call", "summarize yesterday's recordings", or asks about a recorded meeting, consult, call or voice memo by day or time, even if they do not say "Riffado".
---

# Riffado notes

Riffado is the user's self-hosted mirror of their Plaud recorder. Its read-only public API (`/api/v1`) exposes **recordings**. Each recording has a transcript, which is often Tagalog or Taglish, has speech-recognition errors, and has no speaker labels. The user wants these recordings as **clean English notes**: a summary, topic sections with diagrams, and action items for each speaker.

Credentials and settings are in `config.json`, next to this file: `host`, `api_key` and `timezone`. Read day and time phrases in that timezone unless the user names another one. The scripts read `config.json` automatically, so do not copy the key into commands or into chat.

All paths below are relative to this skill's directory (`<skill-dir>`).

## Step 1: Convert the request into a window

| User says | Args |
|---|---|
| "latest", "most recent", "last recording" | `--last 1` (or `--last N`) |
| "today", "yesterday", "Nov 10", "Monday" | `--date today` / `--date yesterday` / `--date YYYY-MM-DD` |
| "this morning" / "afternoon" / "evening" | `--from "<day> 05:00" --to "<day> 12:00"` / `12:00`–`18:00` / `18:00`–`<next day> 00:00` |
| "around 3pm", "my 3pm call" | ±90 min: `--from "<day> 13:30" --to "<day> 16:30"` |
| "last 2 hours", "since lunch" | `--since-hours 2` / `--from "<day> 12:00"` |
| a recording ID | `--id <id>` |

- If the request has two time phrases, the more specific phrase wins. For example, "this morning around 10am" means ±90 min around 10:00, not 05:00–12:00.
- If the user names a kind of recording ("meetings", "the consult", "my call with the bank"), keep only the recordings that match it by title and content. Then name the recordings you left out in one line, so the user can ask for them.

Resolve relative days against today's date in the configured timezone. If a narrow window comes back empty, rerun the request for the whole day with `--list-only`. Report the nearest recordings. Do not stop at "none".

## Step 2: Fetch the full transcripts

To write accurate notes, you need the whole transcript. An excerpt is not enough.

```bash
python3 <skill-dir>/scripts/riffado_notes.py <window args> --list-only            # see what is there
python3 <skill-dir>/scripts/riffado_notes.py <window args> --transcript none --out raw.md
python3 <skill-dir>/scripts/riffado_notes.py --id <id> --transcript full          # one recording at a time
```

- If there are 1–3 recordings, fetch all of them with `--transcript full --out raw.md`, then read `raw.md`.
- **Photos.** The script also downloads each recording's Highlight photos into `images/<recording-id>/`, downscaled for viewing. It lists them in a `### Photos` table, and marks their estimated positions in the transcript as `[[PHOTO n · ~mm:ss]]`. Open every listed photo before you write. Use `--no-images` only when the user asks for a text-only result. Section 1A of the system prompt explains how to use the photos.
- If there are more recordings, list them first. Then fetch and write notes for **one recording at a time** with `--id`. This keeps each transcript in focus.
- `--check` tests connectivity and the key. Run it first if anything fails.
- The environment variables `RIFFADO_HOST`, `RIFFADO_API_KEY` and `RIFFADO_TZ` override `config.json`.

### Failure codes (the script prints one and exits)

- `NETWORK_BLOCKED`: the sandbox cannot reach the host. On Claude web (claude.ai), the user must add the host to the code-execution allowed domains in Settings. Tell the user that, and name the hostname from `config.json`. Do not retry with curl or other shell tools. They hit the same block.
- `CLOUDFLARE_BLOCK`: Cloudflare on the host rejected the client. The script already sends a custom User-Agent, because Cloudflare blocks Python's default User-Agent with error 1010. If this code still appears, the user must relax the Cloudflare security rule for `/api/v1`.
- `AUTH_FAILED`: the key is wrong or was revoked. Ask the user for a new read-only key, and tell them to update `config.json`.
- `CONFIG_MISSING`: there is no `config.json`. Tell the user to copy `config.example.json` to `config.json` and fill it in.

## Step 3: Write the notes

**Read `references/notes-system-prompt.md` first, and follow it.** It is the default output format. It covers these steps:

1. Translate to English and clean speech-recognition errors. Read the photos and use them as a source for names, terms, values and diagrams. High-stakes terms (doses, money, names, dates) are never changed silently.
2. Infer the speakers from context.
3. Split the note into topic sections.
4. Give each section one or more accurate Mermaid diagrams.
5. Put the action items for each speaker at the end.
6. Write all prose in plain English, using `references/ste100-rules.md` (ASD-STE100).

Write the note to `notes.md`.

Use another format only when the user asks for one. Examples: "just the transcript", "one line", or "only the action items". Even then, keep the translation and accuracy rules.

## Step 4: Check and render

```bash
python3 <skill-dir>/scripts/ste-lint.py notes.md                           # plain-English check
python3 <skill-dir>/scripts/render_notes_html.py notes.md notes.html       # standalone page with rendered diagrams
```

- Fix each hard linter violation in your own prose: semicolons, phrasal verbs, nominalizations, and over-long sentences. This includes the template's header lines. Ignore findings inside recording titles, system names and quoted speech.
- Read each Mermaid block again against the syntax rules in the system prompt. A broken diagram shows as an error box in the HTML.

## Step 5: Deliver

- Show the full note in chat as Markdown, with the Mermaid blocks included. This keeps it readable on any device.
- Save `notes.md` and `notes.html` as files the user can download. `notes.html` embeds the photos that the note uses, so it is the one file to share. `notes.md` needs the `images/` folder next to it. On Claude web, write them to `/mnt/user-data/outputs/` if that directory exists. If a file-sharing tool is available, send both files. `notes.html` renders the diagrams in any browser. If the user wants a visual page, you can also put `notes.html` into an HTML artifact.
- Fill in the template's `Window:` line, for example "Wed 11 Nov, 12:00–14:00 (Europe/Berlin)" or "latest recording". This makes a misread request obvious.
- If a recording has `has_transcription: false`, tell the user it is still processing.

## API facts that shape the approach

- `GET /api/v1/recordings` takes `limit` (1–100), `cursor`, `created_since`, `updated_since` and `has_transcription`. Results are sorted by `updated_at` descending. The API has no `recorded_at` filter and no sort parameter. So the script uses `created_since` set to the window start as a lower bound, because ingest time is always ≥ recording time. Then it filters and sorts by `recorded_at` locally.
- `GET /api/v1/recordings/{id}` also returns `images` (id, mime_type, size_bytes, captured_at, offset_ms, url), sorted by `offset_ms`. `GET /api/v1/recordings/{id}/images/{imageId}` returns the bytes, or a 302 redirect to a pre-signed S3 URL. The script fetches that URL without the API key. The list endpoint has no photo count.
- It also returns `transcript` (`{source, language, text}`), `transcripts` (a list of these) and `summary`. `summary` is usually `null`, so the transcript and the photos are the sources for the notes.
- Errors use the format `{error, code, details}`: 401 `UNAUTHORIZED`, 404 `RECORDING_NOT_FOUND`, and 429 `RATE_LIMITED`. The script honors the `Retry-After` header.
