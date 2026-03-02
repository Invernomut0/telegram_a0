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

- `AGENT_ZERO_URL` (default `http://localhost:8080`)
- `TELEGRAM_ALLOWED_CHAT_IDS` (lista separata da virgole)
- `TELEGRAM_DEFAULT_PROJECT`
- `TELEGRAM_POLL_INTERVAL_SEC`
- `TELEGRAM_LONG_POLL_TIMEOUT_SEC`
- `TELEGRAM_CONTEXT_LIFETIME_HOURS`
- `TELEGRAM_SKIP_OLD_UPDATES`
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

- evita overwrite inutili (copia solo se i file cambiano)
- supporta lock anti-concorrenza (se `flock` è disponibile)
- non fallisce per file opzionali mancanti (`README.md`, `TODO.md`, `.env`)

Variabili utili per bootstrap avanzato:

- `AGENT0_ROOT` (default `/a0`)
- `SOURCE_DIR` (default directory dello script)
- `A0_TELEGRAM_INSTALL_LOCK_FILE` (default `/tmp/agent0_telegram_ext_install.lock`)

## Flusso operativo

1. L’estensione `agent_init` avvia il loop Telegram long polling.
2. Ogni messaggio testuale ricevuto viene inoltrato a `/api_message`.
3. Agent Zero risponde normalmente.
4. Le estensioni `response_stream` + `message_loop_end` pubblicano la risposta su Telegram.

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

### Debug verboso consigliato

Imposta in Secrets:

- `TELEGRAM_DEBUG=true`

Con questo flag vedrai nei log:

- stato variabili all'avvio (`TELEGRAM_TOKEN`, `AGENT_ZERO_API_KEY`, `AGENT_ZERO_URL`)
- numero update ricevuti da `getUpdates`
- motivi di skip (chat non ammessa, payload vuoto, ecc.)
- esito inoltro a `/api_message`
- esito invio `sendMessage`

Se trovi il log:

- `[telegram-bridge] Skipping startup: missing TELEGRAM_TOKEN or AGENT_ZERO_API_KEY`

significa che **il bridge inbound è disabilitato**. In quel caso non leggerà Telegram finché non imposti entrambe le variabili.
