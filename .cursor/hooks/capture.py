#!/usr/bin/env python3
"""Agent capture hook for the 8x assignment.

Writes one markdown log per Cursor session into .agent-logs/, containing only
the verbatim prompt and the FINAL response for each turn.

Wired to three Cursor lifecycle events in .cursor/hooks.json:
  beforeSubmitPrompt -> "prompt"    append a PROMPT entry
  afterAgentResponse -> "response"  overwrite the pending-response buffer
  stop               -> "flush"     append the surviving buffer as a RESPONSE entry

The overwrite-then-flush split is what keeps intermediate responses out of the
log: only the buffer still standing at end-of-turn is ever written.

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
FALLBACK_MODEL = "claude-opus-5"

SESSION_KEYS = (
    "conversation_id", "conversationId", "session_id", "sessionId",
    "chat_id", "chatId", "thread_id", "threadId", "id",
)
PROMPT_KEYS = (
    "prompt", "user_prompt", "userPrompt", "prompt_text", "promptText",
    "text", "message", "content", "input",
)
RESPONSE_KEYS = (
    "response", "assistant_response", "assistantResponse", "agent_response",
    "agentResponse", "response_text", "responseText", "text", "message",
    "content", "output",
)
MODEL_KEYS = ("model", "model_name", "modelName", "model_id", "modelId")
TRANSCRIPT_KEYS = (
    "transcript_path", "transcriptPath", "transcript", "conversation_path",
    "conversationPath", "session_file", "sessionFile",
)


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def dig(payload, keys):
    """Breadth-first search for the first non-empty string under any of `keys`."""
    queue = [payload]
    while queue:
        node = queue.pop(0)
        if isinstance(node, dict):
            for key in keys:
                value = node.get(key)
                if isinstance(value, str) and value.strip():
                    return value
                if isinstance(value, (int, float)):
                    return str(value)
            queue.extend(node.values())
        elif isinstance(node, list):
            queue.extend(node)
    return None


def read_payload():
    raw = sys.stdin.read()
    try:
        return json.loads(raw) if raw.strip() else {}
    except (ValueError, TypeError):
        return {"_unparsed_stdin": raw}


def probe(event, payload):
    """Record raw payloads so the real field names can be pinned. Gitignored."""
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            {"event": event, "at": stamp(utc_now()), "payload": payload},
            ensure_ascii=False, default=str,
        )
        with (STATE / "raw-events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass


def session_id(payload):
    return dig(payload, SESSION_KEYS) or "unknown-session"


def state_path(sid):
    return STATE / f"{sid}.json"


def load_state(sid):
    try:
        return json.loads(state_path(sid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(sid, state):
    STATE.mkdir(parents=True, exist_ok=True)
    state_path(sid).write_text(json.dumps(state, indent=2), encoding="utf-8")


def log_path(sid, state):
    """One file per session, created on that session's first prompt."""
    if state.get("file"):
        return LOGS / state["file"]
    started = utc_now()
    name = f"{started.strftime('%Y-%m-%d_%H-%M-%S')}_{sid}.md"
    state["file"] = name
    state["first_prompt_time"] = stamp(started)
    return LOGS / name


def render_frontmatter(sid, state):
    return "\n".join([
        "---",
        f"session_id: {sid}",
        f"date: {state.get('first_prompt_time', '')[:10]}",
        f"author: {AUTHOR}",
        f"model: {state.get('model', FALLBACK_MODEL)}",
        f"tool: {TOOL}",
        f"project: {PROJECT}",
        f"total_exchanges: {state.get('exchanges', 0)}",
        f"first_prompt_time: {state.get('first_prompt_time', '')}",
        f"last_prompt_time: {state.get('last_prompt_time', '')}",
        "---",
        "",
        f"# Session Log - {state.get('first_prompt_time', '')[:10]}",
        "",
        f"Session: `{sid[:8]}` | Project: `{PROJECT}` | Author: `{AUTHOR}`",
        "",
        "---",
        "",
    ])


def rewrite_frontmatter(path, sid, state):
    """Refresh the header counters. Entry bodies are never touched."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    marker = "\n[LOG_ENTRY"
    index = text.find(marker)
    body = "\n" + text[index + 1:] if index != -1 else ""
    path.write_text(render_frontmatter(sid, state) + body, encoding="utf-8")


def append_entry(path, kind, num, sid, model, text):
    LOGS.mkdir(parents=True, exist_ok=True)
    block = (
        f"[LOG_ENTRY type={kind} num={num} session={sid[:8]}]\n"
        f"timestamp: {stamp(utc_now())}\n"
        f"model: {model}\n\n"
        f"{text.rstrip()}\n\n\n"
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(block)


def last_assistant_from_transcript(payload):
    """Fallback if afterAgentResponse never carried the response text."""
    location = dig(payload, TRANSCRIPT_KEYS)
    if not location:
        return None
    path = Path(location)
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    found = None
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        role = dig(record, ("role", "type", "sender"))
        if role and str(role).lower() in ("assistant", "agent", "ai"):
            text = dig(record, RESPONSE_KEYS)
            if text:
                found = text
    return found


def handle_prompt(payload):
    sid = session_id(payload)
    state = load_state(sid)
    path = log_path(sid, state)

    model = dig(payload, MODEL_KEYS) or state.get("model") or FALLBACK_MODEL
    text = dig(payload, PROMPT_KEYS) or "[hook could not read prompt text from payload]"

    num = state.get("exchanges", 0) + 1
    state["exchanges"] = num
    state["model"] = model
    state["last_prompt_time"] = stamp(utc_now())
    state["pending_num"] = num

    if not path.exists():
        LOGS.mkdir(parents=True, exist_ok=True)
        path.write_text(render_frontmatter(sid, state), encoding="utf-8")

    append_entry(path, "PROMPT", num, sid, model, text)
    save_state(sid, state)
    rewrite_frontmatter(path, sid, state)


def handle_response(payload):
    """Overwrite, never append. Intermediate responses erase themselves."""
    sid = session_id(payload)
    text = dig(payload, RESPONSE_KEYS)
    if not text:
        return
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / f"{sid}.pending.txt").write_text(text, encoding="utf-8")

    state = load_state(sid)
    model = dig(payload, MODEL_KEYS)
    if model:
        state["model"] = model
        save_state(sid, state)


def handle_flush(payload):
    sid = session_id(payload)
    state = load_state(sid)
    if not state.get("file"):
        return

    buffer = STATE / f"{sid}.pending.txt"
    text = None
    if buffer.exists():
        try:
            text = buffer.read_text(encoding="utf-8")
        except OSError:
            text = None
    if not text:
        text = last_assistant_from_transcript(payload)
    if not text:
        text = "[hook could not read response text for this turn]"

    num = state.get("pending_num", state.get("exchanges", 0))
    path = LOGS / state["file"]
    append_entry(path, "RESPONSE", num, sid, state.get("model", FALLBACK_MODEL), text)

    try:
        buffer.unlink(missing_ok=True)
    except OSError:
        pass
    state.pop("pending_num", None)
    save_state(sid, state)
    rewrite_frontmatter(path, sid, state)


def main():
    event = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    payload = read_payload()
    probe(event, payload)
    try:
        if event == "prompt":
            handle_prompt(payload)
        elif event == "response":
            handle_response(payload)
        elif event == "flush":
            handle_flush(payload)
    except Exception as error:  # never block the agent on a logging failure
        probe(f"{event}-error", {"error": repr(error)})
    print("{}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
