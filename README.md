# Agent Zero Telegram Extension

Custom extension for Agent Zero enabling bidirectional Telegram integration:

- **Inbound**: messages received by the Telegram bot are forwarded to Agent Zero (`/api_message`).
- **Outbound**: Agent Zero's final responses are sent to Telegram (`CHAT_ID`).
- **Notifications**: any final agent response (including those not originating from Telegram) can be pushed to the configured channel/chat.

## File Structure

- `python/extensions/agent_init/_60_telegram_bridge.py`  
  Starts a background worker that long-polls Telegram and forwards messages to Agent Zero.
- `python/extensions/response_stream/_60_telegram_capture_response.py`  
  Intercepts streamed response payloads and progressively updates the Telegram placeholder message.
- `python/extensions/message_loop_end/_60_telegram_notify.py`  
  Publishes the captured final response to Telegram (opt-in via `TELEGRAM_ENABLE_GLOBAL_NOTIFY`).
- `.env`  
  Example environment variables / secrets template.

## Prerequisites

1. A running Agent Zero instance.
2. A Telegram bot created via `@BotFather`.
3. An Agent Zero API key for external endpoints (`X-API-KEY`).

## Secret Configuration

In your Agent Zero (Settings → Secrets) set at least:

- `TELEGRAM_TOKEN`
- `CHAT_ID`
- `AGENT_ZERO_API_KEY`

The extension first checks `os.environ`, then falls back to the Agent Zero secrets file:

- default: `/a0/usr/secrets.env`
- override: `AGENT_ZERO_SECRETS_FILE=/custom/path/secrets.env`

Supported aliases:

- `TELEGRAM_TOKEN` or `TELEGRAM_BOT_TOKEN`
- `AGENT_ZERO_API_KEY` or `API_KEY` or `A0_API_KEY`
- `CHAT_ID` or `TELEGRAM_CHAT_ID`

Optional variables:

- `AGENT_ZERO_URL` (default `http://localhost:80`)
- `TELEGRAM_ALLOWED_CHAT_IDS` (comma-separated list; if empty, all inbound chats are accepted)
- `TELEGRAM_USE_CHAT_ID_AS_ALLOWED` (default `false`; if `true`, uses `CHAT_ID` as inbound allowlist when `TELEGRAM_ALLOWED_CHAT_IDS` is empty)
- `TELEGRAM_REPLY_VIA_BRIDGE` (default `true`; reply to Telegram directly from the inbound bridge)
- `TELEGRAM_ENABLE_GLOBAL_NOTIFY` (default `false`; forward all Agent Zero responses — including web UI — to `CHAT_ID`)
- `TELEGRAM_DEFAULT_PROJECT`
- `TELEGRAM_POLL_INTERVAL_SEC`
- `TELEGRAM_LONG_POLL_TIMEOUT_SEC`
- `TELEGRAM_CONTEXT_LIFETIME_HOURS`
- `TELEGRAM_SKIP_OLD_UPDATES`
- `TELEGRAM_POLL_LOCK_FILE` (default `/a0/tmp/telegram_poll.lock`)
- `TELEGRAM_CONTEXTS_FILE` (default `/a0/usr/telegram_contexts.json` — persistent across restarts; maps each Telegram `chat_id` to its Agent Zero `context_id`)
- `TELEGRAM_AUTO_DELETE_WEBHOOK_ON_CONFLICT` (default `true`)
- `TELEGRAM_CONFLICT_BACKOFF_SEC` (default `10`)
- `TELEGRAM_CONFLICT_MAX_RETRIES` (default `12`, `0` = unlimited)
- `TELEGRAM_NOTIFY_PREFIX`
- `TELEGRAM_DEBUG` (`true/false`, default `false`)
- `TELEGRAM_LAUNCH_DAEMON` (default `true`; if `true` the installer starts the bridge as a daemon process at boot)
- `TELEGRAM_BRIDGE_PID_FILE` (default `/a0/tmp/telegram_bridge.pid`)
- `TELEGRAM_BRIDGE_LOG_FILE` (default `/a0/tmp/telegram_bridge.log`)

> Note: `CHAT_ID` for a Telegram channel is typically numeric and starts with `-100...`.

## Installation

Copy the files into an Agent Zero root, preserving the paths, for example:

- `/a0/python/extensions/agent_init/_60_telegram_bridge.py`
- `/a0/python/extensions/response_stream/_60_telegram_capture_response.py`
- `/a0/python/extensions/message_loop_end/_60_telegram_notify.py`

Then restart Agent Zero / the container.

## Startup-safe Installation with `/a0/usr` Persistence

If your setup only persists `/a0/usr`, use this pattern:

1. Keep the addon repository in a persistent area, e.g. `/a0/usr/telegram_a0`.
2. Store secrets in `/a0/usr/secrets.env` (or in Agent Zero's Secrets system).
3. Run at every container startup:
  - `/a0/usr/telegram_a0/install_agent0_telegram_ext.sh /a0`

The script is **idempotent** and therefore safe at bootstrap:

- tries to update the local repository with `git pull --ff-only` before copying files;
- if the pull fails due to local changes, automatically runs `git reset --hard` + `git clean -fd` and retries;
- skips unnecessary overwrites (copies only when files change);
- supports concurrency lock (when `flock` is available);
- does not fail for missing optional files (`README.md`, `TODO.md`, `.env`);
- if `git pull` fails, continues with locally available files (fail-safe).

Advanced bootstrap variables:

- `AGENT0_ROOT` (default `/a0`)
- `SOURCE_DIR` (default: script directory)
- `A0_TELEGRAM_INSTALL_LOCK_FILE` (default `/tmp/agent0_telegram_ext_install.lock`)
- `A0_TELEGRAM_AUTO_UPDATE_REPO` (default `true`)
- `A0_TELEGRAM_GIT_REMOTE` (default `origin`)
- `A0_TELEGRAM_GIT_BRANCH` (default: locally tracked branch)
- `A0_TELEGRAM_GIT_AUTO_REPAIR_LOCAL_CHANGES` (default `true`; set to `false` to disable auto `reset/clean`)
- `A0_TELEGRAM_GIT_AUTO_RESTORE_TRACKED_FILES` (default `true`, restores changed tracked files before/after pull)
- `A0_TELEGRAM_GIT_RESTORE_FILES` (default `install_agent0_telegram_ext.sh`, space-separated tracked files)

Version diagnostics:

- The installer reads `VERSION` from the addon source and writes `/a0/TELEGRAM_EXT_VERSION`.
- Bridge startup logs include the loaded version, e.g.:
  - `[telegram-bridge] Module loaded (version=...)`
  - `[telegram-bridge] Standalone daemon running (version=...)  PID=<pid>`
  - `[telegram-bridge] Extension initialized (..., version=...)`

Daemon launch note:

- By default (`TELEGRAM_LAUNCH_DAEMON=true`) the installer starts the bridge as a **standalone background process** immediately after copying files.
- This means the bridge is active **from the very first boot**, without waiting for a web UI message to trigger `agent_init`.
- The daemon's stdout/stderr is written to `TELEGRAM_BRIDGE_LOG_FILE` (default `/a0/tmp/telegram_bridge.log`).
- The daemon's PID is saved to `TELEGRAM_BRIDGE_PID_FILE` (default `/a0/tmp/telegram_bridge.pid`).
- On every reinstall, any existing daemon is stopped and a fresh one is started.

Important bootstrap note:

- Agent Zero's extension bootstrap performs `git pull` **before** running this installer.
- If the repo is already dirty at bootstrap time, one manual cleanup may still be required once:
  - `git -C /a0/usr/extensions/repos/telegram_a0 reset --hard`
  - `git -C /a0/usr/extensions/repos/telegram_a0 clean -fd`
  - `git -C /a0/usr/extensions/repos/telegram_a0 pull --ff-only origin main`
- After that, this installer's auto-restore + auto-repair logic helps keep the repo clean across restarts.

Inbound update types:

- The bridge listens to both `message` and `channel_post` Telegram updates.
- This helps when the bot is used in channels where updates arrive as `channel_post` instead of `message`.
- The bridge also includes a module-import fallback bootstrap, so inbound polling can start even if `agent_init` is not invoked in a specific runtime.

## How It Works

1. The installer starts the bridge as a **standalone daemon** (`nohup python3 _60_telegram_bridge.py`) immediately after copying files.
2. The daemon starts the Telegram long-polling loop **without waiting** for a web UI message.
3. Every received text message is forwarded to `/api_message`.
4. Agent Zero responds normally.
5. With the default `TELEGRAM_REPLY_VIA_BRIDGE=true`, the response is sent back to the same Telegram chat that sent the message.
6. `response_stream` + `message_loop_end` are used only when `TELEGRAM_ENABLE_GLOBAL_NOTIFY=true` is set.

## Channel Separation (Recommended)

For independent channels:

- Messages from the **web UI**: stay in the web UI only (not forwarded to Telegram).
- Messages from **Telegram**: reply goes only to Telegram (same chat).

Set:

- `TELEGRAM_REPLY_VIA_BRIDGE=true`
- `TELEGRAM_ENABLE_GLOBAL_NOTIFY=false`

## Supported Telegram Commands

- `/start` or `/help`: confirms the bridge is active.
- `/reset`: resets the Telegram → `context_id` mapping for the current chat, starting a fresh Agent Zero session. The session is otherwise **always preserved** across messages and container restarts (stored in `TELEGRAM_CONTEXTS_FILE`).

## Security

- Always use Agent Zero **Secrets** for tokens and keys.
- Restrict inbound access with `TELEGRAM_ALLOWED_CHAT_IDS` if you want to accept only specific chats.

## Quick Debug

- If inbound messages are not arriving, check `TELEGRAM_TOKEN`.
- If inbound arrives but Agent Zero does not respond, check `AGENT_ZERO_API_KEY` and `AGENT_ZERO_URL`.
- If Agent Zero responds but Telegram does not receive the reply, check `CHAT_ID` and bot permissions in the channel/chat.

Note: `CHAT_ID` is used for **outbound** delivery (where to send notifications). It does not filter inbound unless you explicitly set `TELEGRAM_USE_CHAT_ID_AS_ALLOWED=true`.

### Verbose Debug

Set in Secrets:

- `TELEGRAM_DEBUG=true`

With this flag the logs will show:

- variable state at startup (`TELEGRAM_TOKEN`, `AGENT_ZERO_API_KEY`, `AGENT_ZERO_URL`)
- number of updates returned by `getUpdates`
- skip reasons (unauthorized chat, empty payload, etc.)
- result of forwarding to `/api_message`
- result of `sendMessage`

The outbound extensions (`response_stream` and `message_loop_end`) also read secrets from both `os.environ` and the file (`/a0/usr/secrets.env`), consistent with the inbound bridge.

### Useful Log Lines

- `[telegram-bridge] Inbound worker started`
- `[telegram-bridge][debug] forwarding to Agent0 -> target_urls=[...]`
- `[telegram-bridge][debug] Agent0 response status=ok ...`
- `[telegram-notify] skip notify: missing config -> ...`
- `[telegram-notify][debug] sendMessage success`

Accepted initialization logs include:

- `[telegram-bridge] Standalone daemon running (version=X.Y.Z)  PID=<pid>` ← daemon mode (new)
- `[telegram-bridge] Extension initialized (reason=agent_init)`
- `[telegram-bridge] Extension initialized (reason=module_import)`
- `[telegram-bridge] Extension initialized (reason=response_stream_import)`
- `[telegram-bridge] Extension initialized (reason=message_loop_end_import)`

With `TELEGRAM_LAUNCH_DAEMON=true` (default), the installer summary shows `Bridge daemon: running (PID=..., log=...)`.  
If the daemon fails to start, check `/a0/tmp/telegram_bridge.log`.

If you do **not** see any bridge init log, check the daemon log file directly: `cat /a0/tmp/telegram_bridge.log`

If you see the log line:

- `[telegram-bridge] Skipping startup: missing TELEGRAM_TOKEN or AGENT_ZERO_API_KEY`

it means the **inbound bridge is disabled**. It will not poll Telegram until both variables are set.

### Polling Error `HTTP 409: Conflict`

The bridge automatically handles the most common `getUpdates` conflicts:

- tries to remove any active webhook (`deleteWebhook`), because Telegram does not allow webhook and polling simultaneously;
- applies a configurable backoff before retrying;
- uses a local lock file to prevent a double poller on the same host/container;
- can stop inbound polling after N consecutive conflicts (`TELEGRAM_CONFLICT_MAX_RETRIES`) to avoid noisy loops.

If the `409` persists, there is typically **another external process** using the same bot token in polling mode. In that case, keep only one active `getUpdates` consumer per token.

### Bootstrap Error: `git pull failed ... local changes would be overwritten`

If you see a log line like:

- `git pull failed ... Your local changes to the following files would be overwritten by merge`

the extension is **not being updated** at restart and you may be running stale code.

One-time fix inside the Agent Zero container, on the persistent repo:

- `git -C /a0/usr/extensions/repos/telegram_a0 reset --hard`
- `git -C /a0/usr/extensions/repos/telegram_a0 clean -fd`
- `git -C /a0/usr/extensions/repos/telegram_a0 pull --ff-only origin main`

Then restart Agent Zero / the container.

Note: with the recommended channel-separation configuration,

- `TELEGRAM_ENABLE_GLOBAL_NOTIFY=false` (default)
- `TELEGRAM_REPLY_VIA_BRIDGE=true` (default)

web UI messages are not forwarded to Telegram, while Telegram messages receive a reply directly on the same Telegram chat.
