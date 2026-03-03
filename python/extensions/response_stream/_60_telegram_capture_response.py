"""Capture final response text from streaming tool-call payloads.

This extension inspects parsed assistant output and stores the final response
text (from response tool args) so `message_loop_end` can publish it to Telegram.

As tokens stream in it also progressively edits the Telegram placeholder message
created by the bridge daemon, giving the user a live typing experience.
"""

from __future__ import annotations

import glob
import json
import os
import time as _time
from pathlib import Path
from typing import Any
from urllib import request

try:
    from python.extensions.agent_init._60_telegram_bridge import _bootstrap_inbound_worker  # pyright: ignore[reportMissingImports]

    _bootstrap_inbound_worker(reason="response_stream_import", agent=None)
except Exception as _bootstrap_exc:
    print(f"[telegram-capture] Bridge bootstrap fallback not available: {_bootstrap_exc}")

try:
    from python.helpers.extension import Extension  # pyright: ignore[reportMissingImports]
except Exception:  # pragma: no cover - local fallback outside Agent Zero runtime
    class Extension:  # type: ignore[override]
        def __init__(self, agent=None, **kwargs):
            self.agent = agent


_STREAM_TMP_DIR = "/a0/tmp"
_STREAM_EDIT_INTERVAL_SEC = 1.5
_STREAM_EDIT_MIN_CHARS_GROWTH = 20
_STREAM_FILE_MAX_AGE_SEC = 300


def _parse_env_file_capture(path: str) -> dict[str, str]:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return {}
    values: dict[str, str] = {}
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, val = raw.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key:
                values[key] = val
    except Exception:
        pass
    return values


def _resolve_telegram_token(env_data: dict[str, str], secrets_file: str) -> str:
    secrets = _parse_env_file_capture(secrets_file)
    for key in ("TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN"):
        val = env_data.get(key, "").strip() or secrets.get(key, "").strip()
        if val:
            return val
    return ""


def _try_stream_edit(token: str, text: str, debug_fn) -> None:
    """Scan active stream state files and edit the Telegram placeholder message as text grows."""
    if not token:
        return
    now = _time.time()
    try:
        files = glob.glob(f"{_STREAM_TMP_DIR}/tg_stream_*.json")
    except Exception:
        return
    for sf_path in files:
        try:
            sf = Path(sf_path)
            state = json.loads(sf.read_text(encoding="utf-8"))
            if state.get("done"):
                continue
            if now - float(state.get("created_ts", 0)) > _STREAM_FILE_MAX_AGE_SEC:
                continue
            last_edit_ts = float(state.get("last_edit_ts", 0))
            if now - last_edit_ts < _STREAM_EDIT_INTERVAL_SEC:
                continue
            last_text = str(state.get("last_text", ""))
            if len(text) - len(last_text) < _STREAM_EDIT_MIN_CHARS_GROWTH:
                continue
            chat_id = str(state["chat_id"])
            msg_id = int(state["message_id"])
            # Edit with plain text (no parse_mode) — final HTML edit is done by the daemon
            req = request.Request(
                url=f"https://api.telegram.org/bot{token}/editMessageText",
                data=json.dumps({
                    "chat_id": chat_id,
                    "message_id": msg_id,
                    "text": text[:4096],
                    "disable_web_page_preview": True,
                }).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with request.urlopen(req, timeout=8) as resp:
                result = json.loads(resp.read().decode("utf-8") or "{}")
            if result.get("ok"):
                state["last_text"] = text
                state["last_edit_ts"] = now
                sf.write_text(json.dumps(state), encoding="utf-8")
                debug_fn(f"stream edit ok chat_id={chat_id} msg_id={msg_id} text_len={len(text)}")
            else:
                debug_fn(f"stream edit not ok: {result.get('description', '?')}")
        except Exception as exc:
            debug_fn(f"stream edit error ({sf_path}): {exc}")
            continue


class TelegramCaptureResponseExtension(Extension):
    @staticmethod
    def _is_root_agent(agent: Any) -> bool:
        raw_number = getattr(agent, "number", 0)
        try:
            return int(raw_number) == 0
        except Exception:
            return str(raw_number).strip() == "0"

    async def execute(self, parsed: dict[str, Any] | None = None, **kwargs) -> Any:
        if not self._is_root_agent(self.agent):
            return None

        env_data = dict(os.environ)
        secrets_file = env_data.get("AGENT_ZERO_SECRETS_FILE", "/a0/usr/secrets.env").strip() or "/a0/usr/secrets.env"

        debug_raw = env_data.get("TELEGRAM_DEBUG", "").strip()
        if not debug_raw:
            p = Path(secrets_file)
            try:
                if p.exists() and p.is_file():
                    for line in p.read_text(encoding="utf-8").splitlines():
                        raw = line.strip()
                        if not raw or raw.startswith("#") or "=" not in raw:
                            continue
                        key, val = raw.split("=", 1)
                        if key.strip() == "TELEGRAM_DEBUG":
                            debug_raw = val.strip().strip('"').strip("'")
                            break
            except Exception:
                pass

        debug = debug_raw.strip().lower() in {"1", "true", "yes", "on"}

        def _debug(message: str) -> None:
            if debug:
                print(f"[telegram-capture][debug] {message}")

        if not isinstance(parsed, dict):
            _debug("parsed payload is not dict, skipping")
            return None

        tool_name = str(parsed.get("tool_name") or parsed.get("tool") or "").strip().lower()
        if tool_name not in {"response", "response_tool"}:
            if debug and tool_name:
                _debug(f"tool_name={tool_name} ignored")
            return None

        args = parsed.get("tool_args") or parsed.get("args") or {}
        if not isinstance(args, dict):
            _debug("response tool args missing or invalid")
            return None

        message = args.get("message") or args.get("text")
        if not isinstance(message, str):
            return None

        cleaned = message.strip()
        if cleaned:
            self.agent.set_data("_telegram_pending_response", cleaned)
            _debug(f"captured response text_len={len(cleaned)}")

            # Streaming edit: progressively update the Telegram placeholder message
            try:
                token = _resolve_telegram_token(env_data, secrets_file)
                _try_stream_edit(token, cleaned, _debug)
            except Exception as _stream_exc:
                _debug(f"stream update error: {_stream_exc}")
        else:
            _debug("response text empty after strip")

        return None
