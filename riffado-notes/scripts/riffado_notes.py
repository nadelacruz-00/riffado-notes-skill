#!/usr/bin/env python3
"""Fetch Riffado recordings ("notes") for a time window and print them as markdown.

Config lookup order (first hit wins, per field):
  1. env vars RIFFADO_HOST, RIFFADO_API_KEY, RIFFADO_TZ
  2. --config PATH
  3. config.json in the skill root (one level above this script)

Usage examples:
  python3 riffado_notes.py --date today
  python3 riffado_notes.py --date 2026-11-10
  python3 riffado_notes.py --from "2026-11-11 08:00" --to "2026-11-11 12:00"
  python3 riffado_notes.py --since-hours 3
  python3 riffado_notes.py --last 1
  python3 riffado_notes.py --id <recording_id>
  python3 riffado_notes.py --check          # connectivity + auth self-test
"""
import argparse, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # Python < 3.9
    ZoneInfo, ZoneInfoNotFoundError = None, Exception

# Cloudflare in front of the host rejects Python's default "Python-urllib/x.y"
# User-Agent with error 1010 (browser_signature_banned). Any explicit UA passes.
USER_AGENT = "riffado-notes-skill/1.1"
SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = {}


def load_config(path=None):
    cfg = {}
    for p in [path, os.path.join(SKILL_ROOT, "config.json")]:
        if p and os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                cfg = json.load(f)
            break
    host = os.environ.get("RIFFADO_HOST") or cfg.get("host")
    key = os.environ.get("RIFFADO_API_KEY") or cfg.get("api_key")
    tz = os.environ.get("RIFFADO_TZ") or cfg.get("timezone") or "UTC"
    if not host or not key or "REPLACE" in key or "example.com" in host:
        sys.exit("CONFIG_MISSING: set host/api_key in config.json next to SKILL.md "
                 "(copy config.example.json) or export RIFFADO_HOST / RIFFADO_API_KEY.")
    return {"host": host.rstrip("/"), "key": key, "tz": tz}


def get_tz(name):
    if ZoneInfo:
        try:
            return ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError, KeyError):
            pass
    m = re.fullmatch(r"(?:UTC)?([+-])(\d{1,2}):?(\d{2})?", name.strip())
    if m:
        sign = 1 if m.group(1) == "+" else -1
        return timezone(sign * timedelta(hours=int(m.group(2)), minutes=int(m.group(3) or 0)), name)
    if name.upper() == "UTC":
        return timezone.utc
    sys.exit(f"TZ_ERROR: unknown timezone {name!r}; use an IANA name or an offset like +08:00")


def api(path, params=None):
    url = f"{CFG['host']}/api/v1{path}"
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {CFG['key']}",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    })
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            try:
                err = json.loads(body)
            except ValueError:
                err = {}
            code = err.get("code") if isinstance(err, dict) else None
            if e.code == 429 and attempt < 3:
                time.sleep(int(e.headers.get("Retry-After") or 2))
                continue
            if e.code == 404:
                return None
            if e.code == 401:
                sys.exit("AUTH_FAILED (401 UNAUTHORIZED): the API key is missing, revoked or expired.")
            if e.code == 403 and isinstance(err, dict) and err.get("cloudflare_error"):
                sys.exit(f"CLOUDFLARE_BLOCK ({err.get('error_name')}): the host's Cloudflare rules rejected "
                         f"this client. Adjust Security settings for /api/v1 on the Riffado zone.")
            if e.code == 403 and not code:
                sys.exit(f"NETWORK_BLOCKED: HTTP 403 not from Riffado (likely a sandbox egress proxy). "
                         f"Allow {urllib.parse.urlparse(CFG['host']).hostname} in the sandbox's network "
                         f"allowlist. Body: {body[:200]}")
            sys.exit(f"RIFFADO_API_ERROR HTTP {e.code} {code or ''} on {path}: {body[:400]}")
        except urllib.error.URLError as e:
            sys.exit(f"NETWORK_BLOCKED: cannot reach {CFG['host']} ({e.reason}). Allow "
                     f"{urllib.parse.urlparse(CFG['host']).hostname} in the sandbox's network allowlist.")


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def parse_local(s, tz):
    s = s.strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=tz)
        except ValueError:
            pass
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=tz)


def list_recordings(created_since=None, max_pages=50):
    out, cursor = [], None
    for _ in range(max_pages):
        page = api("/recordings", {"limit": 100, "cursor": cursor,
                                   "created_since": iso(created_since) if created_since else None})
        if not page:
            break
        out.extend(page.get("data", []))
        if not page.get("has_more"):
            break
        cursor = page.get("next_cursor")
    return out


def when(rec):
    return parse_ts(rec.get("recorded_at")) or parse_ts(rec.get("created_at"))


def text_of(x):
    """Extract text from transcript/summary objects (strings, {text: ...} dicts, lists)."""
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        for k in ("text", "markdown", "content", "summary", "body"):
            if isinstance(x.get(k), str) and x[k].strip():
                return x[k]
        return json.dumps(x, indent=2, ensure_ascii=False)
    if isinstance(x, list):
        return "\n".join(text_of(i) for i in x)
    return str(x)


def best_transcript(full):
    """Detail payload has `transcript` (primary) and `transcripts` (all sources); take the longest."""
    cands = [full.get("transcript")] + list(full.get("transcripts") or [])
    texts = [text_of(c).strip() for c in cands if c]
    return max(texts, key=len) if texts else ""


def render(full, tz, transcript_mode, excerpt_chars):
    t = when(full)
    mins = round((full.get("duration_ms") or 0) / 60000)
    lang = (full.get("transcript") or {}).get("language") if isinstance(full.get("transcript"), dict) else None
    lines = [f"## {full.get('title') or '(untitled)'}",
             f"- Recorded: {t.astimezone(tz).strftime('%a %Y-%m-%d %H:%M') if t else 'unknown'} "
             f"({CFG['tz']}) · {mins} min" + (f" · language: {lang}" if lang else ""),
             f"- ID: {full['id']}", ""]
    summary = text_of(full.get("summary")).strip()
    lines += ["### Summary", summary or "_No summary in Riffado; synthesize one from the transcript._", ""]
    if transcript_mode != "none":
        tr = best_transcript(full)
        if not tr and full.get("has_transcription"):
            tr = text_of(api(f"/recordings/{full['id']}/transcript")).strip()
        if tr and transcript_mode == "excerpt" and len(tr) > excerpt_chars:
            tr = tr[:excerpt_chars] + f"\n\n… [truncated; {len(tr)} chars total, rerun with --transcript full]"
        lines += ["### Transcript", tr or "_No transcript yet (still processing)._", ""]
    return "\n".join(lines)


def main():
    global CFG
    p = argparse.ArgumentParser()
    p.add_argument("--date", help="today | yesterday | YYYY-MM-DD (local day)")
    p.add_argument("--from", dest="frm", help="local start, 'YYYY-MM-DD HH:MM'")
    p.add_argument("--to", help="local end (exclusive), default now")
    p.add_argument("--since-hours", type=float)
    p.add_argument("--last", type=int, help="N most recent recordings")
    p.add_argument("--id")
    p.add_argument("--tz", help="override timezone (IANA name or +HH:MM)")
    p.add_argument("--config", help="path to config.json")
    p.add_argument("--transcript", choices=["none", "excerpt", "full"], default="excerpt")
    p.add_argument("--excerpt-chars", type=int, default=6000)
    p.add_argument("--out", help="also write full markdown (complete transcripts) to this file")
    p.add_argument("--list-only", action="store_true", help="titles/times only, no detail fetch")
    p.add_argument("--check", action="store_true", help="test connectivity and auth, then exit")
    a = p.parse_args()
    CFG = load_config(a.config)
    if a.tz:
        CFG["tz"] = a.tz
    tz = get_tz(CFG["tz"])
    now = datetime.now(tz)

    if a.check:
        page = api("/recordings", {"limit": 1})
        n = len((page or {}).get("data", []))
        print(f"OK: {urllib.parse.urlparse(CFG['host']).hostname} reachable, key accepted, "
              f"{n} recording(s) on first page, tz={CFG['tz']}, now={now.strftime('%Y-%m-%d %H:%M')}")
        return

    if a.id:
        if api(f"/recordings/{a.id}") is None:
            sys.exit(f"RECORDING_NOT_FOUND: {a.id}")
        recs, label = [{"id": a.id}], f"recording {a.id}"
    elif a.last:
        recs = list_recordings(now - timedelta(days=14))
        if len(recs) < a.last:
            recs = list_recordings(None, max_pages=10)
        recs = sorted(recs, key=lambda r: when(r) or datetime.min.replace(tzinfo=timezone.utc),
                      reverse=True)[:a.last]
        recs.reverse()  # chronological
        label = f"latest {a.last}"
    else:
        if a.date:
            d = {"today": now.date(), "yesterday": now.date() - timedelta(days=1)}.get(a.date.lower())
            start = datetime.combine(d, datetime.min.time(), tz) if d else parse_local(a.date, tz)
            end = start + timedelta(days=1)
        elif a.since_hours:
            start, end = now - timedelta(hours=a.since_hours), now
        elif a.frm:
            start = parse_local(a.frm, tz)
            end = parse_local(a.to, tz) if a.to else now
        else:
            p.error("give --date, --from/--to, --since-hours, --last, --id or --check")
        # created_at (ingest time) >= recorded_at, so created_since=start is a safe lower bound.
        # The API has no recorded_at filter and sorts by updated_at, so filter + sort locally.
        recs = [r for r in list_recordings(start) if (w := when(r)) and start <= w < end]
        recs.sort(key=when)
        label = f"{start.strftime('%Y-%m-%d %H:%M')} to {end.strftime('%Y-%m-%d %H:%M')} ({CFG['tz']})"

    header = f"# Riffado notes: {label}\n\n{len(recs)} recording(s).\n"
    print(header)
    if not recs:
        return
    if a.list_only:
        for r in recs:
            w = when(r)
            print(f"- {w.astimezone(tz).strftime('%Y-%m-%d %H:%M') if w else '?'} · {r.get('title')} · "
                  f"{round((r.get('duration_ms') or 0) / 60000)} min · id={r['id']} · "
                  f"transcript={r.get('has_transcription')} summary={r.get('has_summary')}")
        return
    fulls = [api(f"/recordings/{r['id']}") or r for r in recs]
    for full in fulls:
        print(render(full, tz, a.transcript, a.excerpt_chars))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(header + "\n" + "\n".join(render(x, tz, "full", 0) for x in fulls))
        print(f"[full markdown written to {a.out}]")


if __name__ == "__main__":
    main()
