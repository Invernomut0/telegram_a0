# TODO

## To Do

- [ ] **Owner:** Lorenzo — **Task:** Aggiungere test d’integrazione end-to-end su ambiente Agent Zero reale — **Deadline:** 2026-03-10
- [ ] **Owner:** Lorenzo — **Task:** Aggiungere rate-limiting outbound e retry esponenziale — **Deadline:** 2026-03-12

## Doing

- [ ] *(nessuna attività in corso)*

## Review

- [ ] *(nessuna attività in review)*

## Done

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
