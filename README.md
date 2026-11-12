# riffado-notes skill

A Claude skill that fetches your [Riffado](https://riffado.com) recordings (Plaud recorder transcripts) for a day, a time window, or the latest recording. It turns each recording into clean English notes. You trigger it with requests like *"grab my latest riffado notes for today"* or *"notes from my 3pm call"*.

Each note contains:

- a short **summary** at the start
- the transcript **translated to English** (Tagalog/Taglish is supported), with speech-recognition errors cleaned up. Changes to doses, amounts, names and dates are logged and never made silently.
- **photo-enriched context**: the recording's Plaud Highlight photos (participant lists, slides, whiteboards, prescriptions) are downloaded, viewed by Claude, and used for real names, exact spellings, values and diagrams. Useful photos are embedded in the note.
- **topic sections**, each with one or more accurate **Mermaid diagrams**
- **action items for each speaker** (speakers are inferred from context, because the transcripts have no labels)
- plain-English prose following [ASD-STE100](https://github.com/danyuchn/asd-ste100-skill), checked by the bundled linter
- a standalone **HTML page** that renders the diagrams in any browser

The skill uses the read-only Riffado public API (`/api/v1/recordings`). It needs only Python 3 standard-library modules.

## Layout

```
riffado-notes/
├── SKILL.md                          # workflow Claude follows
├── config.example.json               # copy to config.json and fill in
├── references/
│   ├── notes-system-prompt.md        # default note format: translation, sections, diagrams, action items
│   └── ste100-rules.md               # plain-English rules (adapted from asd-ste100-skill, MIT)
├── scripts/
│   ├── riffado_notes.py              # fetches recordings, transcripts and photos
│   ├── render_notes_html.py          # converts notes.md to notes.html: renders diagrams, embeds photos
│   └── ste-lint.py                   # STE100 linter (from asd-ste100-skill, MIT)
└── THIRD_PARTY_NOTICES.md
```

`config.json` holds your host and API key. It is gitignored and never committed.

## Setup

1. Copy `riffado-notes/config.example.json` to `riffado-notes/config.json` and set:
   - `host`: your Riffado URL, e.g. `https://riffado.example.com`
   - `api_key`: a personal read-only key (`op_...`), created in Riffado's Automation API settings
   - `timezone`: an IANA name such as `Europe/Berlin`, or an offset such as `+08:00`
2. Zip the `riffado-notes/` folder, with `config.json` inside it.
3. **Claude web (claude.ai):** go to Settings → Capabilities, upload the zip as a skill, and make sure code execution is on.
4. **Allow the host in Claude web.** By default, the claude.ai code-execution sandbox blocks outbound requests to unknown domains. In Settings → Capabilities → code execution, turn on network egress and add your Riffado hostname to the allowed domains. If the domain is not allowed, the script exits with `NETWORK_BLOCKED`. On Team or Enterprise plans, an admin may have to allow the domain.
5. Test it in a chat with: *"run the riffado-notes check"*. Claude runs `scripts/riffado_notes.py --check`.

## Script usage

```bash
python3 riffado-notes/scripts/riffado_notes.py --check
python3 riffado-notes/scripts/riffado_notes.py --date today --list-only
python3 riffado-notes/scripts/riffado_notes.py --last 1
python3 riffado-notes/scripts/riffado_notes.py --from "2026-11-11 13:30" --to "2026-11-11 16:30" --transcript full --out raw.md
python3 riffado-notes/scripts/ste-lint.py notes.md
python3 riffado-notes/scripts/render_notes_html.py notes.md notes.html
```

Environment variables `RIFFADO_HOST`, `RIFFADO_API_KEY` and `RIFFADO_TZ` override `config.json`.

## Known issues fixed

- **Cloudflare error 1010 (`browser_signature_banned`).** Cloudflare's Browser Integrity Check rejects Python's default `Python-urllib/3.x` User-Agent. The script sends an explicit `User-Agent` header.
- **Sandbox egress blocks** show up as `NETWORK_BLOCKED` with the hostname to allow, instead of a raw traceback.
- **`summary` is usually null** on recordings. The skill tells Claude to write the notes from the transcript.
- **Photos on S3 storage** come back as a 302 redirect to a pre-signed URL. The script fetches that URL without the `Authorization` header, because S3 rejects a request that uses two auth mechanisms.
- **Mermaid `timeline` breaks when a time contains a colon** (`10:15 : event`). The note format tells Claude to write `10.15 AM : event` instead.

## Photos

Photos sync only for Plaud 4.0 accounts that have "Import Plaud transcripts, summaries and photos" turned on, and only Highlight photos sync. `GET /api/v1/recordings/{id}` returns them in an `images` array, sorted by `offset_ms`. The script:

1. saves each photo to `images/<recording-id>/NN-MMmSSs.jpg`. If Pillow is installed, it fixes the rotation and downscales the photo to a 1568 px long edge. HEIC photos also need `pillow-heif`.
2. lists the photos in a `### Photos` table in its output.
3. inserts `[[PHOTO n · ~mm:ss]]` markers into the transcript. Transcripts have no timestamps, so each position is an estimate: the photo time divided by the recording length.

Pass `--no-images` to skip photos.
