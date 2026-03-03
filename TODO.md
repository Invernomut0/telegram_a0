# TODO

## To Do

- [ ] **Owner:** Lorenzo — **Task:** Add end-to-end integration tests on a real Agent Zero environment — **Deadline:** 2026-03-10
- [ ] **Owner:** Lorenzo — **Task:** Add outbound rate-limiting and exponential retry — **Deadline:** 2026-03-12

## Doing

- [ ] *(no tasks in progress)*

## Review

- [ ] *(no tasks in review)*

## Done

- [x] **Owner:** Copilot — **Task:** Streaming typing effect + HTML formatting (v0.2.4): daemon sends ⏳ placeholder + typing keepalive, response_stream edits it token-by-token via file IPC, daemon final-edits with Markdown→HTML. — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Root cause fix: installer now launches bridge as standalone daemon (`TELEGRAM_LAUNCH_DAEMON=true`) so inbound polling starts immediately at boot without waiting for `agent_init` hook. Added `__main__` block to bridge for standalone mode. Bumped to `0.2.3`. — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Added extension version diagnostics (installer + bridge logs) and bumped build to `0.2.2` — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Added multi-hook bootstrap fallback triggers (`response_stream_import`, `message_loop_end_import`) plus bridge module-load diagnostic log — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Added module-import fallback bootstrap for inbound worker to handle runtimes where `agent_init` hook is not triggered — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Fixed root-agent detection across all Telegram extensions to handle `agent.number` as int or string (prevents silent hook skip) — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Fixed installer output command-substitution side effect in final notes and normalized key installer logs/messages to English — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Added inbound support for Telegram `channel_post` updates and improved unsupported-update diagnostics — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Added installer self-heal to auto-restore tracked files (default: `install_agent0_telegram_ext.sh`) before/after pull + documented bootstrap pull ordering limitation — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Added auto-fix in installer for `git pull` conflicts (auto-repair `reset --hard` + `clean -fd` + retry) — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Documented troubleshooting for bootstrap error `git pull failed ... local changes would be overwritten` with recovery commands — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Updated installer: automatic `git pull --ff-only` at every startup before copying files (with safe fallback) — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Channel separation completed: direct Telegram reply from bridge + global notify opt-in (`TELEGRAM_ENABLE_GLOBAL_NOTIFY=false` default) — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Fixed inbound filter: `CHAT_ID` is no longer an implicit allowlist (opt-in via `TELEGRAM_USE_CHAT_ID_AS_ALLOWED`) + blocked-chat logging — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Fixed Telegram↔Agent0 bridge: automatic localhost port fallback (80/8080) and advanced diagnostic logging — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Aligned outbound secret resolution (env + `/a0/usr/secrets.env`) in `telegram_notify`/`telegram_capture_response` — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Added fail-safe for repeated `HTTP 409` with inbound stop and webhook diagnostics (`getWebhookInfo`) — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Hardened Telegram polling with `HTTP 409` handling (deleteWebhook + backoff + local lock file) — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Implemented inbound Telegram → Agent Zero bridge (`agent_init`) — **Date:** 2026-03-02
- [x] **Owner:** Copilot — **Task:** Implemented outbound notification pipeline (`response_stream` + `message_loop_end`) — **Date:** 2026-03-02
- [x] **Owner:** Copilot — **Task:** Added complete documentation (`README.md`) and configuration template (`.env`) — **Date:** 2026-03-02
- [x] **Owner:** Copilot — **Task:** Made installer idempotent and startup-safe for `/a0/usr`-only persistence — **Date:** 2026-03-02
