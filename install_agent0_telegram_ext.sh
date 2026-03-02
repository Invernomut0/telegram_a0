#!/bin/bash
# Script di installazione estensione Telegram per Agent Zero
# Copia i file nelle cartelle corrette e crea le directory se mancanti
# Usage: ./install_agent0_telegram_ext.sh /percorso/alla/root/agentzero

set -e

if [ -z "$1" ]; then
  echo "Usage: $0 /percorso/alla/root/agentzero"
  exit 1
fi

AGENT0_ROOT="$1"

# Percorsi sorgente (dove si trova questo script)
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

# Percorsi destinazione
EXT_DIR="$AGENT0_ROOT/python/extensions"

# Crea le cartelle se non esistono
mkdir -p "$EXT_DIR/agent_init"
mkdir -p "$EXT_DIR/response_stream"
mkdir -p "$EXT_DIR/message_loop_end"

# Copia i file Python
cp "$SRC_DIR/python/extensions/agent_init/_60_telegram_bridge.py" "$EXT_DIR/agent_init/"
cp "$SRC_DIR/python/extensions/response_stream/_60_telegram_capture_response.py" "$EXT_DIR/response_stream/"
cp "$SRC_DIR/python/extensions/message_loop_end/_60_telegram_notify.py" "$EXT_DIR/message_loop_end/"

# Copia README, TODO e .env come riferimento (opzionale)
cp "$SRC_DIR/README.md" "$AGENT0_ROOT/README_TELEGRAM_EXT.md" || true
cp "$SRC_DIR/TODO.md" "$AGENT0_ROOT/TODO_TELEGRAM_EXT.md" || true
cp "$SRC_DIR/.env" "$AGENT0_ROOT/.env.telegram_example" || true

cat <<EOF
✅ Estensione Telegram installata!

- Riavvia Agent Zero/container per attivare le nuove estensioni.
- Ricordati di configurare i secrets richiesti (TELEGRAM_TOKEN, CHAT_ID, AGENT_ZERO_API_KEY) nelle impostazioni di Agent Zero.
- Consulta README_TELEGRAM_EXT.md per dettagli e troubleshooting.
EOF
