# Capture test

Evidence that agent capture is installed at the project level and fires on its
own, in every session, without anyone remembering to run it.

## Setup

| | |
| --- | --- |
| Tool | Cursor 3.20.10 |
| Models seen | `claude-opus-5-thinking-high` (main session), `auto-smart` (second session) |
| Mechanism | Cursor lifecycle hooks |
| Config file changed | `.cursor/hooks.json` |
| Hook script | `.cursor/hooks/capture.py` |
| Output | `.agent-logs/YYYY-MM-DD_HH-MM-SS_<session-id>.md`, one file per session |

Two events are wired. `beforeSubmitPrompt` fires the instant Enter is pressed
and appends the prompt. `stop` fires when the turn ends and appends that turn's
final response. Nothing in between is recorded: no thinking, no tool calls.

```json
{
  "version": 1,
  "hooks": {
    "beforeSubmitPrompt": [
      { "command": "python .cursor/hooks/capture.py prompt", "timeout": 15 }
    ],
    "stop": [
      { "command": "python .cursor/hooks/capture.py flush", "timeout": 15 }
    ]
  }
}
```

Because the config lives in the repo rather than in user settings, it applies to
every chat opened in this workspace. That is the property the second canary
below is there to prove.

## Canary 1 — the session that created the hook

**File:** `.agent-logs/2026-09-12_18-44-33_d6ecbfc0-b9df-48f7-b3e9-a5634cac9f3d.md`

```
[LOG_ENTRY type=PROMPT num=33 session=d6ecbfc0]
timestamp: 2026-09-12T22:18:50.960Z
model: claude-opus-5-thinking-high

CAPTURE TEST â€” 8x assignment, Muzammal Bilal
```

```
[LOG_ENTRY type=RESPONSE num=33 session=d6ecbfc0]
timestamp: 2026-09-12T22:19:03.222Z
model: claude-opus-5-thinking-high

Capture test acknowledged — this exchange is now being written to `.agent-logs/` as PROMPT 31 and RESPONSE 31 for session `d6ecbfc0`.

Your prompt was captured by the `beforeSubmitPrompt` hook the moment you pressed Enter. This reply will be captured by the `stop` hook when I finish writing it. Both land in `.agent-logs/2026-09-12_18-44-33_d6ecbfc0-b9df-48f7-b3e9-a5634cac9f3d.md`, verbatim, with a UTC timestamp and the model name.
```

## Canary 2 — a brand-new chat, opened after the hook was installed

Different session id, different file, different model. Nothing was run by hand.

**File:** `.agent-logs/2026-09-12_22-19-40_e20a0b31-c90f-4fa1-ab27-24d0578dde6a.md`

```
[LOG_ENTRY type=PROMPT num=1 session=e20a0b31]
timestamp: 2026-09-12T22:19:40.721Z
model: auto-smart

CAPTURE TEST â€” 8x assignment, Muzammal Bilal
```

```
[LOG_ENTRY type=RESPONSE num=1 session=e20a0b31]
timestamp: 2026-09-12T22:20:12.670Z
model: auto-smart

Canary received.

`CAPTURE TEST — 8x assignment, Muzammal Bilal` is logged for this session. The Cursor hook should write the prompt and this reply into `.agent-logs/` when the turn ends.
```

## The canary caught a bug, and the fix

Both prompts above landed as `CAPTURE TEST â€” 8x assignment`. The em dash is
wrong. Reading the raw bytes rather than trusting the terminal:

```
on disk:                  b'\xc3\xa2\xe2\x82\xac\xe2\x80\x9d'
"\u2014".encode("utf-8"):  b'\xe2\x80\x94'
that, decoded cp1252, re-encoded utf-8:
                          b'\xc3\xa2\xe2\x82\xac\xe2\x80\x9d'
```

Cursor hands the hook UTF-8 that has already been decoded once through cp1252.
The responses were unaffected because those are read from the session
transcript file, which does not have the fault. It only ever hit prompts, and it
only surfaced here because this was the first prompt containing a non-ASCII
character.

The brief asks for prompts captured verbatim, and `â€”` is not verbatim, so
`undo_double_encoding()` in `capture.py` now reverses it. It is guarded twice:
the mojibake markers must be present, and the cp1252 round trip must succeed.
Text that merely contains an accented character — `château`, `café naïve über` —
fails the decode and passes through untouched.

Re-sending the same canary after the fix, in both sessions:

```
[LOG_ENTRY type=PROMPT num=35 session=d6ecbfc0]
timestamp: 2026-09-12T22:24:21.268Z
model: claude-opus-5-thinking-high

CAPTURE TEST — 8x assignment, Muzammal Bilal
```

```
[LOG_ENTRY type=PROMPT num=2 session=e20a0b31]
timestamp: 2026-09-12T22:24:29.310Z
model: auto-smart

CAPTURE TEST — 8x assignment, Muzammal Bilal
```

The four entries above the fix are left exactly as they were recorded. The brief
says not to edit an entry after the fact, and that applies to entries that
embarrass the tooling as much as to the rest.

## Other things that did not work first

**`afterAgentResponse` does not fire in Cursor 3.20.10.** It was the obvious
event for capturing a reply and it never ran once. `stop` fires reliably, so the
response is captured there instead.

**The `stop` payload carries no response text.** It gives a `transcript_path`
and nothing else, so the reply has to be recovered from the session transcript.
Within one turn the assistant emits many JSONL entries; the last one containing
`type: "text"` blocks is the closing message. That entry is text-only by
construction, which is what keeps thinking and tool calls out of the log without
having to filter them.

**The hook payload arrives with a UTF-8 BOM.** A plain `utf-8` decode left a
`\ufeff` on the front of the JSON and `json.loads` refused it. Reading with
`utf-8-sig` fixed that. Separate issue from the cp1252 fault above.

**An image-only message really does send an empty prompt.** That is not the same
as the payload being unreadable, and the first version of the hook reported both
as `[hook could not read prompt text]`, which was misleading. PROMPT 7 in the
main log still carries that older wording, and is left alone for the same reason
as above. The hook now distinguishes the two cases and records the attachment
count.

## Verifying independently

```bash
ls .agent-logs/
grep -c "LOG_ENTRY type=PROMPT" .agent-logs/*.md
grep -n "CAPTURE TEST" .agent-logs/*.md
```

Two files, two different session ids, the canary present in both. Nothing in
`.agent-logs/` is gitignored; it ships with the repo.
