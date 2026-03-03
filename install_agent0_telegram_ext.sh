#!/usr/bin/env bash
# Script di installazione estensione Telegram per Agent Zero
# Startup-safe: idempotente, con lock anti-esecuzione concorrente e copie solo-se-cambiano.
#
# Usage:
#   ./install_agent0_telegram_ext.sh [/percorso/alla/root/agentzero]
#
# Esempio tipico in container Agent Zero:
#   ./install_agent0_telegram_ext.sh /a0

set -Eeuo pipefail

log() {
  printf '[telegram-ext-installer] %s\n' "$*"
}

warn() {
  printf '[telegram-ext-installer][warn] %s\n' "$*" >&2
}

die() {
  printf '[telegram-ext-installer][error] %s\n' "$*" >&2
  exit 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT0_ROOT="${1:-${AGENT0_ROOT:-/a0}}"
SRC_DIR="${SOURCE_DIR:-$SCRIPT_DIR}"
EXT_DIR="$AGENT0_ROOT/python/extensions"
LOCK_FILE="${A0_TELEGRAM_INSTALL_LOCK_FILE:-/tmp/agent0_telegram_ext_install.lock}"
AUTO_UPDATE_REPO="${A0_TELEGRAM_AUTO_UPDATE_REPO:-true}"
AUTO_UPDATE_REMOTE="${A0_TELEGRAM_GIT_REMOTE:-origin}"
AUTO_UPDATE_BRANCH="${A0_TELEGRAM_GIT_BRANCH:-}"
AUTO_REPAIR_LOCAL_CHANGES="${A0_TELEGRAM_GIT_AUTO_REPAIR_LOCAL_CHANGES:-true}"
AUTO_RESTORE_TRACKED_FILES="${A0_TELEGRAM_GIT_AUTO_RESTORE_TRACKED_FILES:-true}"
RESTORE_FILE_LIST="${A0_TELEGRAM_GIT_RESTORE_FILES:-install_agent0_telegram_ext.sh}"

if command -v flock >/dev/null 2>&1; then
  exec 9>"$LOCK_FILE"
  if ! flock -n 9; then
    log "Un'altra installazione è in corso; skip sicuro."
    exit 0
  fi
else
  warn "'flock' non disponibile: continuo senza lock concorrente."
fi

[[ -d "$SRC_DIR" ]] || die "Directory sorgente non trovata: $SRC_DIR"

update_repo_if_possible() {
  local repo_dir="$1"

  _restore_tracked_files() {
    local _repo="$1"

    case "${AUTO_RESTORE_TRACKED_FILES,,}" in
      0|false|no|off)
        return 0
        ;;
    esac

    local file
    for file in $RESTORE_FILE_LIST; do
      if [[ -z "$file" ]]; then
        continue
      fi
      if git -C "$_repo" ls-files --error-unmatch "$file" >/dev/null 2>&1; then
        if ! git -C "$_repo" diff --quiet -- "$file"; then
          warn "Detected local changes in '$file' -> auto restoring to HEAD."
          if ! git -C "$_repo" checkout -- "$file"; then
            warn "Failed to auto-restore '$file'."
          fi
        fi
      fi
    done
  }

  _git_pull() {
    local _repo="$1"
    if [[ -n "$AUTO_UPDATE_BRANCH" ]]; then
      if ! git -C "$_repo" fetch --prune "$AUTO_UPDATE_REMOTE"; then
        warn "git fetch fallito, continuo con file locali già presenti."
        return 1
      fi
      git -C "$_repo" pull --ff-only "$AUTO_UPDATE_REMOTE" "$AUTO_UPDATE_BRANCH"
    else
      git -C "$_repo" pull --ff-only "$AUTO_UPDATE_REMOTE"
    fi
  }

  case "${AUTO_UPDATE_REPO,,}" in
    0|false|no|off)
      log "Auto-update repository disabilitato (A0_TELEGRAM_AUTO_UPDATE_REPO=$AUTO_UPDATE_REPO)."
      return 0
      ;;
  esac

  if [[ ! -d "$repo_dir/.git" ]]; then
    log "Sorgente non è un repository git locale: skip update ($repo_dir)"
    return 0
  fi

  if ! command -v git >/dev/null 2>&1; then
    warn "git non disponibile: skip update repository."
    return 0
  fi

  _restore_tracked_files "$repo_dir"

  log "Updating local repository from remote (remote=$AUTO_UPDATE_REMOTE)..."
  if _git_pull "$repo_dir"; then
    _restore_tracked_files "$repo_dir"
    log "Repository updated successfully."
    return 0
  fi

  case "${AUTO_REPAIR_LOCAL_CHANGES,,}" in
    0|false|no|off)
      warn "git pull failed and auto-repair is disabled: continuing with local files."
      return 0
      ;;
  esac

  warn "git pull failed: trying auto-repair (reset --hard + clean -fd) and retry."
  if ! git -C "$repo_dir" reset --hard; then
    warn "auto-repair failed on reset --hard, continuing with local files."
    return 0
  fi
  if ! git -C "$repo_dir" clean -fd; then
    warn "auto-repair failed on clean -fd, continuing with local files."
    return 0
  fi

  if ! _git_pull "$repo_dir"; then
    warn "retry git pull failed after auto-repair, continuing with local files."
    return 0
  fi

  _restore_tracked_files "$repo_dir"
  log "Repository updated successfully."
}

update_repo_if_possible "$SRC_DIR"

installed_count=0
updated_count=0
unchanged_count=0
skipped_count=0

copy_if_changed() {
  local src="$1"
  local dst="$2"

  [[ -f "$src" ]] || die "File sorgente mancante: $src"
  mkdir -p "$(dirname "$dst")"

  if [[ -f "$dst" ]]; then
    if cmp -s "$src" "$dst"; then
      unchanged_count=$((unchanged_count + 1))
      log "unchanged: $dst"
      return 0
    fi
    cp -f "$src" "$dst"
    updated_count=$((updated_count + 1))
    log "updated:   $dst"
    return 0
  fi

  cp -f "$src" "$dst"
  installed_count=$((installed_count + 1))
  log "installed: $dst"
}

copy_optional_if_present() {
  local src="$1"
  local dst="$2"

  if [[ ! -f "$src" ]]; then
    skipped_count=$((skipped_count + 1))
    log "optional missing, skip: $src"
    return 0
  fi

  copy_if_changed "$src" "$dst"
}

mkdir -p "$EXT_DIR/agent_init" "$EXT_DIR/response_stream" "$EXT_DIR/message_loop_end"

# Copia estensioni core (obbligatorie)
copy_if_changed \
  "$SRC_DIR/python/extensions/agent_init/_60_telegram_bridge.py" \
  "$EXT_DIR/agent_init/_60_telegram_bridge.py"

copy_if_changed \
  "$SRC_DIR/python/extensions/response_stream/_60_telegram_capture_response.py" \
  "$EXT_DIR/response_stream/_60_telegram_capture_response.py"

copy_if_changed \
  "$SRC_DIR/python/extensions/message_loop_end/_60_telegram_notify.py" \
  "$EXT_DIR/message_loop_end/_60_telegram_notify.py"

# File di riferimento (opzionali)
copy_optional_if_present "$SRC_DIR/README.md" "$AGENT0_ROOT/README_TELEGRAM_EXT.md"
copy_optional_if_present "$SRC_DIR/TODO.md" "$AGENT0_ROOT/TODO_TELEGRAM_EXT.md"
copy_optional_if_present "$SRC_DIR/.env" "$AGENT0_ROOT/.env.telegram_example"

cat <<EOF
✅ Estensione Telegram installata (startup-safe)

Root Agent0:     $AGENT0_ROOT
Sorgente addon:  $SRC_DIR

Riepilogo:
- installed: $installed_count
- updated:   $updated_count
- unchanged: $unchanged_count
- skipped:   $skipped_count

Note:
- Script idempotente: puoi lanciarlo ad ogni startup container.
- All'avvio prova ad aggiornare il repository locale (`git pull --ff-only`) prima della copia file.
- Se `git pull` fallisce per modifiche locali, per default prova auto-repair (`git reset --hard && git clean -fd`) e ritenta.
- Configura i secrets richiesti (TELEGRAM_TOKEN, CHAT_ID, AGENT_ZERO_API_KEY) in Agent Zero.
- Per dettagli e troubleshooting consulta: $AGENT0_ROOT/README_TELEGRAM_EXT.md
EOF
