# Agent Zero Telegram Extension

Estensione custom per Agent Zero che abilita integrazione Telegram bidirezionale:

- **Inbound**: messaggi ricevuti dal bot Telegram vengono inoltrati ad Agent Zero (`/api_message`).
- **Outbound**: risposte finali di Agent Zero vengono inviate su Telegram (`CHAT_ID`).
- **Notifiche**: qualsiasi risposta finale dell’agente (anche non originata da Telegram) può essere notificata sul canale/chat configurato.

## Struttura file

- `python/extensions/agent_init/_60_telegram_bridge.py`  
  Avvia un worker in background che usa long polling Telegram e inoltra i messaggi ad Agent Zero.
- `python/extensions/response_stream/_60_telegram_capture_response.py`  
  Intercetta i payload di risposta (tool call) e salva il testo finale da notificare.
- `python/extensions/message_loop_end/_60_telegram_notify.py`  
  Pubblica su Telegram la risposta finale catturata.
- `.env`  
  Esempio variabili ambiente/segreti.

## Prerequisiti

1. Istanza Agent Zero attiva.
2. Bot Telegram creato via `@BotFather`.
3. API key Agent Zero per endpoint esterni (`X-API-KEY`).

## Configurazione segreti

Nel tuo Agent Zero (Settings → Secrets) imposta almeno:

- `TELEGRAM_TOKEN`
- `CHAT_ID`
- `AGENT_ZERO_API_KEY`

L'estensione prova prima `os.environ`, poi fallback su file secrets Agent0:

- default: `/a0/usr/secrets.env`
- override: `AGENT_ZERO_SECRETS_FILE=/custom/path/secrets.env`

Alias supportati:

- `TELEGRAM_TOKEN` oppure `TELEGRAM_BOT_TOKEN`
- `AGENT_ZERO_API_KEY` oppure `API_KEY` oppure `A0_API_KEY`
- `CHAT_ID` oppure `TELEGRAM_CHAT_ID`

Opzionali:

- `AGENT_ZERO_URL` (default `http://localhost:80`)
- `TELEGRAM_ALLOWED_CHAT_IDS` (lista separata da virgole; se vuoto accetta tutte le chat inbound)
- `TELEGRAM_USE_CHAT_ID_AS_ALLOWED` (default `false`; se `true`, quando `TELEGRAM_ALLOWED_CHAT_IDS` è vuoto usa `CHAT_ID` come filtro inbound)
- `TELEGRAM_REPLY_VIA_BRIDGE` (default `true`; risponde in Telegram direttamente dal bridge inbound)
- `TELEGRAM_ENABLE_GLOBAL_NOTIFY` (default `false`; inoltra su `CHAT_ID` tutte le risposte Agent0, inclusa UI web)
- `TELEGRAM_DEFAULT_PROJECT`
- `TELEGRAM_POLL_INTERVAL_SEC`
- `TELEGRAM_LONG_POLL_TIMEOUT_SEC`
- `TELEGRAM_CONTEXT_LIFETIME_HOURS`
- `TELEGRAM_SKIP_OLD_UPDATES`
- `TELEGRAM_POLL_LOCK_FILE` (default `/a0/tmp/telegram_poll.lock`)
- `TELEGRAM_AUTO_DELETE_WEBHOOK_ON_CONFLICT` (default `true`)
- `TELEGRAM_CONFLICT_BACKOFF_SEC` (default `10`)
- `TELEGRAM_CONFLICT_MAX_RETRIES` (default `12`, `0` = infinito)
- `TELEGRAM_NOTIFY_PREFIX`
- `TELEGRAM_DEBUG` (`true/false`, default `false`)

> Nota: `CHAT_ID` per un canale Telegram in genere è numerico e inizia con `-100...`.

## Installazione

Copia i file in una root Agent Zero mantenendo i path, ad esempio:

- `/a0/python/extensions/agent_init/_60_telegram_bridge.py`
- `/a0/python/extensions/response_stream/_60_telegram_capture_response.py`
- `/a0/python/extensions/message_loop_end/_60_telegram_notify.py`

Poi riavvia Agent Zero/container.

## Installazione startup-safe con persistenza in `/a0/usr`

Se la tua installazione persiste solo `/a0/usr`, usa questo pattern:

1. Mantieni il repository addon in area persistente, ad esempio `/a0/usr/telegram_a0`.
2. Salva i secrets in `/a0/usr/secrets.env` (oppure nel sistema Secrets di Agent Zero).
3. Esegui ad ogni avvio container:
  - `/a0/usr/telegram_a0/install_agent0_telegram_ext.sh /a0`

Lo script è **idempotente** e quindi sicuro al bootstrap:

- prova ad aggiornare il repository locale con `git pull --ff-only` prima della copia file;
- se il pull fallisce per modifiche locali, prova automaticamente `git reset --hard` + `git clean -fd` e ritenta il pull;
- evita overwrite inutili (copia solo se i file cambiano)
- supporta lock anti-concorrenza (se `flock` è disponibile)
- non fallisce per file opzionali mancanti (`README.md`, `TODO.md`, `.env`)
- se `git pull` fallisce, continua usando i file locali già presenti (fail-safe)

Variabili utili per bootstrap avanzato:

- `AGENT0_ROOT` (default `/a0`)
- `SOURCE_DIR` (default directory dello script)
- `A0_TELEGRAM_INSTALL_LOCK_FILE` (default `/tmp/agent0_telegram_ext_install.lock`)
- `A0_TELEGRAM_AUTO_UPDATE_REPO` (default `true`)
- `A0_TELEGRAM_GIT_REMOTE` (default `origin`)
- `A0_TELEGRAM_GIT_BRANCH` (default branch tracciato localmente)
- `A0_TELEGRAM_GIT_AUTO_REPAIR_LOCAL_CHANGES` (default `true`, per disabilitare auto `reset/clean`)
- `A0_TELEGRAM_GIT_AUTO_RESTORE_TRACKED_FILES` (default `true`, restores changed tracked files before/after pull)
- `A0_TELEGRAM_GIT_RESTORE_FILES` (default `install_agent0_telegram_ext.sh`, space-separated tracked files)

Important bootstrap note:

- Agent Zero's extension bootstrap performs `git pull` **before** running this installer.
- If the repo is already dirty at bootstrap time, one manual cleanup may still be required once:
  - `git -C /a0/usr/extensions/repos/telegram_a0 reset --hard`
  - `git -C /a0/usr/extensions/repos/telegram_a0 clean -fd`
  - `git -C /a0/usr/extensions/repos/telegram_a0 pull --ff-only origin main`
- After that, this installer's auto-restore + auto-repair logic helps keep the repo clean across restarts.

## Flusso operativo

1. L’estensione `agent_init` avvia il loop Telegram long polling.
2. Ogni messaggio testuale ricevuto viene inoltrato a `/api_message`.
3. Agent Zero risponde normalmente.
4. Con default `TELEGRAM_REPLY_VIA_BRIDGE=true`, la risposta viene inviata alla stessa chat Telegram che ha scritto il messaggio.
5. `response_stream` + `message_loop_end` sono usati solo se abiliti `TELEGRAM_ENABLE_GLOBAL_NOTIFY=true`.

## Separazione canali (consigliata)

Per avere canali indipendenti:

- Messaggi da **web UI**: restano solo in web UI (non inoltrati a Telegram)
- Messaggi da **Telegram**: risposta solo su Telegram (stessa chat)

Configura:

- `TELEGRAM_REPLY_VIA_BRIDGE=true`
- `TELEGRAM_ENABLE_GLOBAL_NOTIFY=false`

## Comandi Telegram supportati

- `/start` o `/help`: conferma bridge attivo.
- `/reset`: resetta il context mapping Telegram→`context_id`.

## Sicurezza

- Usa sempre i **Secrets** di Agent Zero per token e chiavi.
- Limita gli ingressi con `TELEGRAM_ALLOWED_CHAT_IDS` se vuoi accettare solo chat specifiche.

## Debug rapido

- Se non arrivano messaggi inbound, verifica `TELEGRAM_TOKEN`.
- Se inbound arriva ma Agent Zero non risponde, verifica `AGENT_ZERO_API_KEY` e `AGENT_ZERO_URL`.
- Se Agent Zero risponde ma Telegram non riceve, verifica `CHAT_ID` e permessi del bot nel canale/chat.

Importante: `CHAT_ID` è usato per l'**outbound** (dove inviare notifiche). Non filtra l'inbound a meno che non abiliti esplicitamente `TELEGRAM_USE_CHAT_ID_AS_ALLOWED=true`.

### Debug verboso consigliato

Imposta in Secrets:

- `TELEGRAM_DEBUG=true`

Con questo flag vedrai nei log:

- stato variabili all'avvio (`TELEGRAM_TOKEN`, `AGENT_ZERO_API_KEY`, `AGENT_ZERO_URL`)
- numero update ricevuti da `getUpdates`
- motivi di skip (chat non ammessa, payload vuoto, ecc.)
- esito inoltro a `/api_message`
- esito invio `sendMessage`

Con le ultime patch, anche le estensioni outbound (`response_stream` e `message_loop_end`) leggono i secrets sia da `os.environ` sia da file (`/a0/usr/secrets.env`), allineandosi al bridge inbound.

### Log utili da cercare

- `[telegram-bridge] Inbound worker started`
- `[telegram-bridge][debug] forwarding to Agent0 -> target_urls=[...]`
- `[telegram-bridge][debug] Agent0 response status=ok ...`
- `[telegram-notify] skip notify: missing config -> ...`
- `[telegram-notify][debug] sendMessage success`

Se trovi il log:

- `[telegram-bridge] Skipping startup: missing TELEGRAM_TOKEN or AGENT_ZERO_API_KEY`

significa che **il bridge inbound è disabilitato**. In quel caso non leggerà Telegram finché non imposti entrambe le variabili.

### Errore polling `HTTP 409: Conflict`

Il bridge ora gestisce automaticamente i conflitti più comuni su `getUpdates`:

- prova a rimuovere un eventuale webhook attivo (`deleteWebhook`), perché Telegram non permette webhook e polling insieme;
- applica un backoff configurabile prima di riprovare;
- usa un lock file locale per evitare doppio poller nello stesso host/container.
- può fermare il polling inbound dopo N conflitti consecutivi (`TELEGRAM_CONFLICT_MAX_RETRIES`) per evitare loop rumorosi.

Se il `409` continua, in genere c’è **un altro processo esterno** che usa lo stesso bot token in polling. In tal caso lascia attivo un solo consumer `getUpdates` per quel token.

### Errore bootstrap: `git pull failed ... local changes would be overwritten`

Se nei log vedi un errore simile:

- `git pull failed ... Your local changes to the following files would be overwritten by merge`

allora l'estensione **non viene aggiornata/installa** al riavvio, e potresti continuare a eseguire codice vecchio.

Risoluzione (una tantum) nel container Agent Zero, sul repo persistente:

- `git -C /a0/usr/extensions/repos/telegram_a0 reset --hard`
- `git -C /a0/usr/extensions/repos/telegram_a0 clean -fd`
- `git -C /a0/usr/extensions/repos/telegram_a0 pull --ff-only origin main`

Poi riavvia Agent Zero/container.

Nota: con la configurazione consigliata per canali separati,

- `TELEGRAM_ENABLE_GLOBAL_NOTIFY=false` (default)
- `TELEGRAM_REPLY_VIA_BRIDGE=true` (default)

i messaggi della web UI non vengono inoltrati su Telegram, mentre i messaggi Telegram ricevono risposta direttamente sulla stessa chat Telegram.
