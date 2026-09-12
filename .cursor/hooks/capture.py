#!/usr/bin/env python3
"""Agent capture hook for the 8x assignment.

Writes one markdown log per Cursor session into .agent-logs/, containing only
the verbatim prompt and the final response of each turn.

Wired to two Cursor lifecycle events in .cursor/hooks.json:
  beforeSubmitPrompt -> "prompt"  append the prompt verbatim
  stop               -> "flush"   append that turn's final response

Cursor's stop payload carries no response text, only a transcript path, so the
response is recovered from the session transcript. Within a turn the assistant
emits many entries; the last one holding text is the closing message, which is
text-only. Thinking and tool calls are therefore excluded by construction.

Every path fails open. A logging bug must never block the build.
"""

import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOGS = ROOT / ".agent-logs"
STATE = ROOT / ".cursor" / "hooks" / ".state"

AUTHOR = "Muzammal-Bilal"
PROJECT = "naano-rebuild"
TOOL = "cursor"


def stamp(moment=None):
    moment = moment or datetime.datetime.now(datetime.timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def read_event():
    """Cursor writes JSON with a UTF-8 BOM, so decode with utf-8-sig."""
    try:
        raw = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")
        return json.loads(raw) if raw.strip() else {}
    except (ValueError, OSError):
        return {}


def note(label, detail):
    """Scratch diagnostics. Gitignored, never part of the submission."""
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        with (STATE / "hook-debug.log").open("a", encoding="utf-8") as handle:
            handle.write(f"{stamp()} {label} {detail}\n")
    except OSError:
        pass


def load_state(session):
    try:
        return json.loads((STATE / f"{session}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(session, state):
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / f"{session}.json").write_text(json.dumps(state, indent=2), encoding="utf-8")


def header(session, state):
    date = state.get("first_prompt_time", "")[:10]
    return "\n".join([
        "---",
        f"session_id: {session}",
        f"date: {date}",
        f"author: {AUTHOR}",
        f"model: {state.get('model', '')}",
        f"tool: {TOOL}",
        f"project: {PROJECT}",
        f"total_exchanges: {state.get('exchanges', 0)}",
        f"first_prompt_time: {state.get('first_prompt_time', '')}",
        f"last_prompt_time: {state.get('last_prompt_time', '')}",
        "---",
        "",
        f"# Session Log - {date}",
        "",
        f"Session: `{session[:8]}` | Project: `{PROJECT}` | Author: `{AUTHOR}`",
        "",
        "---",
        "",
    ])


def write_entry(path, session, state, kind, text):
    """Append an entry, then refresh the header counters. Bodies are never touched."""
    LOGS.mkdir(parents=True, exist_ok=True)
    body = ""
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        cut = existing.find("\n[LOG_ENTRY")
        body = existing[cut + 1:] if cut != -1 else ""

    body += (
        f"[LOG_ENTRY type={kind} num={state.get('exchanges', 0)} session={session[:8]}]\n"
        f"timestamp: {stamp()}\n"
        f"model: {state.get('model', '')}\n\n"
        f"{text.rstrip()}\n\n\n"
    )
    path.write_text(header(session, state) + "\n" + body, encoding="utf-8")


def final_response(location):
    """Last assistant entry carrying text is that turn's closing message."""
    if not location:
        return None
    path = Path(location)
    if not path.is_file():
        return None
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None

    latest = None
    for line in lines:
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if record.get("role") != "assistant":
            continue
        blocks = record.get("message", {}).get("content", [])
        texts = [
            block.get("text", "") for block in blocks
            if isinstance(block, dict) and block.get("type") == "text"
            and block.get("text", "").strip()
        ]
        if texts:
            latest = "\n\n".join(texts)
    return latest


def on_prompt(event):
    session = event.get("conversation_id") or event.get("session_id") or "unknown-session"
    state = load_state(session)

    now = stamp()
    state["model"] = event.get("model") or state.get("model", "")
    state["exchanges"] = state.get("exchanges", 0) + 1
    state["last_prompt_time"] = now
    state.setdefault("first_prompt_time", now)
    state.setdefault(
        "file",
        f"{now[:10]}_{now[11:19].replace(':', '-')}_{session}.md",
    )

    text = event.get("prompt")
    if not text:
        note("prompt-missing", list(event.keys()))
        text = "[hook could not read prompt text]"

    write_entry(LOGS / state["file"], session, state, "PROMPT", text)
    save_state(session, state)


def on_flush(event):
    session = event.get("conversation_id") or event.get("session_id") or "unknown-session"
    state = load_state(session)
    if not state.get("file"):
        note("flush-no-session", session)
        return

    text = final_response(event.get("transcript_path"))
    if not text:
        note("flush-no-response", event.get("transcript_path"))
        text = "[hook could not recover the response for this turn]"

    write_entry(LOGS / state["file"], session, state, "RESPONSE", text)


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    event = read_event()
    try:
        if action == "prompt":
            on_prompt(event)
        elif action == "flush":
            on_flush(event)
    except Exception as error:  # never block the agent on a logging failure
        note(f"{action}-error", repr(error))
    print("{}")


if __name__ == "__main__":
    main()
