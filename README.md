# JARVIS — a voice HUD for Claude Code

Talk to your computer. It answers in a real voice, uses your own tools, and
shows you every step it takes.

This is a mission-control interface that **drives your own Claude Code**. It
isn't a separate AI — whatever connectors and skills you've already set up
(Gmail, Calendar, Drive, anything MCP) work here with no extra wiring, because
Claude Code is doing the work and this is a face on it.

```bash
git clone https://github.com/Itsme23476/jarvis-os.git
cd jarvis-os
cp .env.example .env      # add your ElevenLabs key
./start.sh
```

Opens on <http://localhost:8730>. Click **◉ VOICE**, allow the mic, and talk.

---

## What you need

| | |
|---|---|
| **Claude Code** | installed and logged in (`claude` → `/login`). This is the brain. |
| **Python 3** | standard library only — no `pip install`, no `npm`, no build step |
| **ElevenLabs** | free account, for the voice. Nothing else is paid. |

No API key for the model. It runs on your existing Claude Code login.

---

## How it works

```
you speak ─▶ ElevenLabs speech-to-text ─▶ text
                                            │
                                            ▼
  claude -p "<text>" --output-format stream-json --include-partial-messages
                     (your subscription · your connectors · your skills)
                                            │
             ┌──────────────────────────────┴──────────────────┐
             ▼                                                  ▼
   streamed telemetry                                     the answer
   (run id, tool calls, tokens, latency)                        │
             │                                                  ▼
             ▼                                     ElevenLabs text-to-speech
       the ACTION LOG                                           │
                                                                ▼
                                                        the RESPONSE panel
```

The server spawns `claude` and parses its `stream-json` output, forwarding
events to the browser over a streamed HTTP response. The Action Log isn't
decoration — it's Claude's real event stream.

---

## Talking to it

Press **◉ VOICE once**, then just talk. It listens, you stop, it answers and
speaks, then **listens again automatically** — no clicking between turns. Press
it again to end the conversation.

The mic goes deliberately deaf while it's speaking. Without that it transcribes
its own voice through your speakers and talks to itself forever.

You can also type in the uplink box (⌘↵ to send).

**Wrong microphone?** The browser's default mic is often not the one you talk
into. Open `http://localhost:8730/?mic=<part of the mic's name>` once (for
example `?mic=usb`); the choice is remembered. The Action Log shows which mic
is in use and lists the others.

---

## The command matrix

The six buttons are real. Press one, then say or type the rest.

| Button | What it does |
|---|---|
| **/new** | Fresh thread — clears the conversation |
| **/profile** | Remembers a fact about you, permanently |
| **/goal** | Sets your standing objective |
| **/personality** | Overlays a tone on the persona |
| **/kanban** | Say something to add it to your queue; press alone to hear it |
| **/background** | Runs a mission asynchronously and reports back when it lands |

Profile, goal, personality and the queue live in `state.json` and are injected
into **every** run, so they persist across restarts and genuinely change how it
behaves. Press a button with nothing after it to read the current value.

Try: `/personality` → *"dry, sardonic, fewer words"* → then ask it anything.

---

## Making it yours

**`persona.md` is the personality.** Brevity, tone, banned phrases, and the rule
that it must never narrate its own tooling. Edit it, restart, done — no code
change. Everything it says is spoken aloud, so it's written for the ear.

**Connectors** come from Claude Code. Add one with `claude mcp add …` and it
appears here on the next run. Check the STATUS line in the Action Log to see
which ones loaded.

---

## Lead tools (optional)

`tools/` holds two scripts the assistant knows about, so you can say "find me
200 dentist leads in the US and Canada and put them in a Google Sheet".

| Script | What it does |
|---|---|
| `leads.py dentist 100` | Real business listings from OpenStreetMap for US and Canadian cities, kept only if the website is live. Saves `leads.json` and `leads.xlsx`. |
| `competitor_pricing.py URL` | Plan names and prices on a page, as seen from the US, Germany, India and Brazil. |

```bash
pip install -r tools/requirements.txt
```

Sites decide what to show you from your IP address, so without a proxy every
"country" is just your own location. To see what a local visitor sees, copy
`tools/.env.local.example` to `tools/.env.local` and add residential proxy
credentials. The sheet records where each request really exited.

Know the limits: listings come from public map data, so there are no ratings
and coverage varies by city; the public map servers are often slow; and the
pricing script reads plain HTML, so prices drawn by JavaScript are missed.

---

## The permission trade-off — read this

By default this runs Claude with `--dangerously-skip-permissions`
(`JARVIS_PERMISSION=bypass`).

It has to. In a headless run there's nobody to click "allow", so without it
every tool call — including your connectors — stalls forever.

**That means the assistant can use tools, including ones that send email, without
asking you first.** On your own machine, driving your own assistant, that's the
point. But know what you're turning on. The guardrails then live in `persona.md`
and in whatever skills you install — not in a per-action prompt.

Set `JARVIS_PERMISSION=default` to require approval, and accept that tool calls
won't complete headlessly.

The server listens on `127.0.0.1` only and refuses requests that don't come
from its own page, so another website open in your browser can't send it
commands. Don't put it behind a tunnel or reverse proxy.

---

## Troubleshooting

Every run writes exactly what Claude said — stdout and stderr — to
`/tmp/jarvis-claude-raw.log`. If something misbehaves, read that first; it is
the ground truth.

**It transcribes me but never answers.** Check the raw log for
`authentication_failed`. A stale `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN`
in `~/.claude/settings.json` overrides your login and 401s on every request.
Remove them and Claude falls back to your subscription.

**A connector hangs the run.** Start with `JARVIS_MCP=none ./start.sh` to
confirm, then authorize the offending server with `claude` → `/mcp`.

**"core went quiet".** The watchdog stopped a run that produced nothing for
`JARVIS_TIMEOUT` seconds. The error includes Claude's stderr.

**"Port … is already in use".** Something else holds the port. Stop it, or
set `JARVIS_PORT` in `.env`.

**It says "nothing transcribed" while you talk.** It is probably listening on
the wrong microphone — see *Wrong microphone?* above. Start with
`JARVIS_DEBUG=1 ./start.sh` to keep the last clip at `/tmp/jarvis-last-audio`
and hear what it heard.

**The mic hears nothing.** The reactor shows a live `IN ▮▮▮▯▯` meter while
listening. If the bars don't move, it's mic permission, not the app.

---

## Files

```
jarvis-os/
├── server.py     HTTP + NDJSON run stream + voice proxy   (stdlib only)
├── runtime.py    spawns claude, parses stream-json
├── voice.py      ElevenLabs speech-to-text + text-to-speech
├── commands.py   the six command-matrix buttons + state
├── persona.md    how it talks — edit this
├── tools/        optional lead and pricing scripts
├── ui/           the HUD: index.html, styles.css, app.js
└── start.sh
```

There are no canned answers anywhere in this project. If Claude can't be
reached, it says so rather than faking a reply.

## License

MIT.
