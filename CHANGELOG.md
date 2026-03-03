# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.4] - 2026-03-03

### Added
- **Streaming typing effect**: bridge sends a `💭` placeholder message as soon as a Telegram message is received, then progressively edits it token-by-token via a JSON IPC state file (`tg_stream_<chat_id>.json`).
- **Typing keepalive**: a background thread sends `sendChatAction typing` every 4 seconds while Agent Zero processes the request, giving real-time visual feedback.
- **Markdown → HTML rendering**: final Agent Zero response is converted from Markdown to Telegram HTML (`<b>`, `<i>`, `<code>`, `<pre>`, `<s>`, `<a>`) before being delivered via `editMessageText` with `parse_mode=HTML`.

### Changed
- `response_stream` extension now edits the Telegram placeholder incrementally (throttled to every 1.5 s and minimum 20 chars growth).
- Final stream edit uses `HTML` parse mode; intermediate edits use plain text to avoid partial-tag rendering errors.

---

## [0.2.3] - 2026-03-03

### Fixed
- **Root cause for missed inbound messages**: installer now launches the bridge as a **standalone background daemon** (`nohup python3 _60_telegram_bridge.py`) immediately after copying files, so the long-poll loop starts at boot without waiting for the `agent_init` hook.
- Added `__main__` block to `_60_telegram_bridge.py` for standalone daemon execution with `SIGTERM`/`SIGINT` handling.
- Added `TELEGRAM_LAUNCH_DAEMON` environment variable (default `true`) to opt out of the daemon launch.
- Added `TELEGRAM_BRIDGE_PID_FILE` and `TELEGRAM_BRIDGE_LOG_FILE` variables for PID/log file paths.

---

## [0.2.2] - 2026-03-03

### Added
- **Extension version diagnostics**: installer reads `VERSION` from the addon source and writes `/a0/TELEGRAM_EXT_VERSION` for runtime inspection.
- Bridge startup now logs the loaded version:
  - `[telegram-bridge] Module loaded (version=...)`
  - `[telegram-bridge] Standalone daemon running (version=...)  PID=<pid>`
  - `[telegram-bridge] Extension initialized (..., version=...)`
- Added `_resolve_extension_version()` helper with multiple candidate paths for version resolution.

---

## [0.2.1] - 2026-03-03

### Added
- **Multi-hook bootstrap fallback**: `response_stream` and `message_loop_end` extensions call `_bootstrap_inbound_worker()` on import (reasons: `response_stream_import`, `message_loop_end_import`) so the inbound worker can start even when `agent_init` is not invoked.
- **Module-import fallback bootstrap**: `_60_telegram_bridge.py` calls `_bootstrap_inbound_worker(reason="module_import")` at module level as a last-resort fallback.
- Added `channel_post` to the list of supported Telegram update types (for bots used in Telegram channels).
- Added improved diagnostics for unsupported/unrecognised update types.
- Added installer self-heal: automatically restores tracked files (default: `install_agent0_telegram_ext.sh`) before and after `git pull` via `A0_TELEGRAM_GIT_AUTO_RESTORE_TRACKED_FILES` and `A0_TELEGRAM_GIT_RESTORE_FILES`.
- Added auto-repair in installer for `git pull` conflicts: runs `git reset --hard` + `git clean -fd` then retries (`A0_TELEGRAM_GIT_AUTO_REPAIR_LOCAL_CHANGES`).
- Added documentation for bootstrap pull ordering limitation and manual recovery commands.

### Fixed
- **Root-agent detection**: all Telegram extensions now handle `agent.number` as both `int` and `str`, preventing silent hook skips.
- **Installer output**: fixed command-substitution side effect in final notes; normalised all log/message strings to English.
- **Inbound filter**: `CHAT_ID` is no longer an implicit inbound allowlist; opt-in via `TELEGRAM_USE_CHAT_ID_AS_ALLOWED=true`.
- Added detailed logging when an inbound chat is blocked.

### Changed
- Channel separation is now the default: `TELEGRAM_REPLY_VIA_BRIDGE=true`, `TELEGRAM_ENABLE_GLOBAL_NOTIFY=false`.

---

## [0.2.0] - 2026-03-03

### Added
- **Fail-safe for repeated HTTP 409**: after `TELEGRAM_CONFLICT_MAX_RETRIES` consecutive 409 responses the inbound poller stops and logs a clear message.
- **HTTP 409 handling**: `deleteWebhook` + configurable backoff + local lock file.
- Advanced diagnostic logging for `getWebhookInfo` on 409 conflicts.

### Fixed
- Telegram ↔ Agent0 bridge: automatic localhost port fallback (80 ↔ 8080).
- Aligned outbound secret resolution (env + `/a0/usr/secrets.env`) in both `telegram_notify` and `telegram_capture_response`.

---

## [0.1.0] - 2026-03-02

### Added
- Initial implementation of the inbound Telegram → Agent Zero bridge (`agent_init` extension).
- Initial implementation of the outbound notification pipeline (`response_stream` + `message_loop_end` extensions).
- Idempotent installer (`install_agent0_telegram_ext.sh`) safe for `/a0/usr`-only persistence, with:
  - `git pull --ff-only` auto-update before copying files.
  - Copy-only-when-changed behaviour.
  - Concurrency lock via `flock`.
  - `git pull` safe fallback (continues with local files on failure).
- Complete documentation (`README.md`), configuration template (`.env`), and task list (`TODO.md`).
- `/start`, `/help`, and `/reset` Telegram bot commands.
- `TELEGRAM_CONTEXTS_FILE` for persistent `chat_id → context_id` mapping across restarts.
- `TELEGRAM_DEBUG` flag for verbose diagnostic logging.
