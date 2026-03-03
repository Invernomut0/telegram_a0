# TODO

## To Do

- [ ] **Owner:** Lorenzo — **Task:** Aggiungere test d’integrazione end-to-end su ambiente Agent Zero reale — **Deadline:** 2026-03-10
- [ ] **Owner:** Lorenzo — **Task:** Aggiungere rate-limiting outbound e retry esponenziale — **Deadline:** 2026-03-12

## Doing

- [ ] *(nessuna attività in corso)*

## Review

- [ ] *(nessuna attività in review)*

## Done

- [x] **Owner:** Copilot — **Task:** Added extension version diagnostics (installer + bridge logs) and bumped build to `0.2.2` — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Added multi-hook bootstrap fallback triggers (`response_stream_import`, `message_loop_end_import`) plus bridge module-load diagnostic log — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Added module-import fallback bootstrap for inbound worker to handle runtimes where `agent_init` hook is not triggered — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Fixed root-agent detection across all Telegram extensions to handle `agent.number` as int or string (prevents silent hook skip) — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Fixed installer output command-substitution side effect in final notes and normalized key installer logs/messages to English — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Added inbound support for Telegram `channel_post` updates and improved unsupported-update diagnostics — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Added installer self-heal to auto-restore tracked files (default: `install_agent0_telegram_ext.sh`) before/after pull + documented bootstrap pull ordering limitation — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Inserita auto-fix in installer per conflitti `git pull` (auto-repair `reset --hard` + `clean -fd` + retry) — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Documentato troubleshooting per errore bootstrap `git pull failed ... local changes would be overwritten` con recovery commands — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Installer aggiornato: `git pull --ff-only` automatico ad ogni avvio prima della copia file (con fallback safe) — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Separazione canali completata: reply Telegram diretto dal bridge + global notify opt-in (`TELEGRAM_ENABLE_GLOBAL_NOTIFY=false` default) — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Corretto filtro inbound: `CHAT_ID` non è più allowlist implicita (opt-in con `TELEGRAM_USE_CHAT_ID_AS_ALLOWED`) + log chat bloccate — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Fix bridge Telegram↔Agent0: fallback automatico porta localhost (80/8080) e logging diagnostico avanzato — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Allineata risoluzione secrets outbound (env + `/a0/usr/secrets.env`) in `telegram_notify`/`telegram_capture_response` — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Aggiunto fail-safe su `HTTP 409` ripetuti con stop inbound e diagnostica webhook (`getWebhookInfo`) — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Hardened polling Telegram con gestione `HTTP 409` (deleteWebhook + backoff + lock file locale) — **Date:** 2026-03-03
- [x] **Owner:** Copilot — **Task:** Implementato bridge inbound Telegram → Agent Zero (`agent_init`) — **Date:** 2026-03-02
- [x] **Owner:** Copilot — **Task:** Implementata pipeline notifiche outbound (`response_stream` + `message_loop_end`) — **Date:** 2026-03-02
- [x] **Owner:** Copilot — **Task:** Aggiunta documentazione completa (`README.md`) e template configurazione (`.env`) — **Date:** 2026-03-02
- [x] **Owner:** Copilot — **Task:** Reso installer idempotente e startup-safe per persistenza solo `/a0/usr` — **Date:** 2026-03-02
