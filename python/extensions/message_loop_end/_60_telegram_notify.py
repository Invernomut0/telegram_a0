"""Send Agent Zero notifications to Telegram at end of message-loop iteration."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib import request

try:
    from python.helpers.extension import Extension  # pyright: ignore[reportMissingImports]
except Exception:  # pragma: no cover - local fallback outside Agent Zero runtime
    class Extension:  # type: ignore[override]
        def __init__(self, agent=None, **kwargs):
            self.agent = agent


def _send_telegram_message(token: str, chat_id: str, text: str) -> None:
    payload = {
        "chat_id": chat_id,
        "text": text[:4000],
        "disable_web_page_preview": True,
    }
    req = request.Request(
        url=f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8")
        data = json.loads(raw) if raw else {}
    if not data.get("ok", False):
        raise RuntimeError(f"Telegram sendMessage failed: {data}")


def _parse_env_file(path: str) -> dict[str, str]:
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
        return {}

    return values


def _resolve_secret(
    env_data: dict[str, str],
    secrets_data: dict[str, str],
    keys: Iterable[str],
) -> str:
    for key in keys:
        val = env_data.get(key, "").strip()
        if val:
            return val
    for key in keys:
        val = secrets_data.get(key, "").strip()
        if val:
            return val
    return ""


def _as_bool(value: str, default: bool = False) -> bool:
    raw = (value or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


class TelegramNotifyExtension(Extension):
    _warned_missing_config = False

    @staticmethod
    def _is_root_agent(agent: Any) -> bool:
        raw_number = getattr(agent, "number", 0)
        try:
            return int(raw_number) == 0
        except Exception:
            return str(raw_number).strip() == "0"

    async def execute(self, loop_data=None, **kwargs) -> Any:
        if not self._is_root_agent(self.agent):
            return None

        env_data = dict(os.environ)
        secrets_file = env_data.get("AGENT_ZERO_SECRETS_FILE", "/a0/usr/secrets.env").strip() or "/a0/usr/secrets.env"
        secrets_data = _parse_env_file(secrets_file)

        global_notify_enabled = _as_bool(
            _resolve_secret(env_data, secrets_data, keys=("TELEGRAM_ENABLE_GLOBAL_NOTIFY",)) or "false",
            False,
        )
        if not global_notify_enabled:
            return None

        debug = _as_bool(_resolve_secret(env_data, secrets_data, keys=("TELEGRAM_DEBUG",)) or "false", False)

        def _debug(message: str) -> None:
            if debug:
                print(f"[telegram-notify][debug] {message}")

        token = _resolve_secret(env_data, secrets_data, keys=("TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN"))
        chat_id = _resolve_secret(env_data, secrets_data, keys=("CHAT_ID", "TELEGRAM_CHAT_ID"))
        if not token or not chat_id:
            if not TelegramNotifyExtension._warned_missing_config:
                print(
                    "[telegram-notify] skip notify: missing config -> "
                    f"TELEGRAM_TOKEN={'set' if bool(token) else 'missing'} "
                    f"CHAT_ID={'set' if bool(chat_id) else 'missing'} "
                    f"SECRETS_FILE={secrets_file}"
                )
                TelegramNotifyExtension._warned_missing_config = True
            _debug("notify disabled due to missing token/chat id")
            return None

        TelegramNotifyExtension._warned_missing_config = False

        pending = self.agent.get_data("_telegram_pending_response")
        if isinstance(pending, str) and pending.strip():
            text = pending.strip()
            self.agent.set_data("_telegram_pending_response", "")
        else:
            text = ""

        if not text:
            # Optional fallback for direct plain responses.
            fallback = getattr(loop_data, "last_response", "") if loop_data else ""
            if isinstance(fallback, str):
                maybe = fallback.strip()
                if maybe and not (maybe.startswith("{") and "tool_name" in maybe):
                    text = maybe
                    _debug("using fallback text from loop_data.last_response")

        if not text:
            _debug("skip notify: no pending/fallback text to send")
            return None

        prefix = _resolve_secret(env_data, secrets_data, keys=("TELEGRAM_NOTIFY_PREFIX",)) or "🤖 Agent0\n"
        body = f"{prefix}{text}" if prefix else text

        last_sent = self.agent.get_data("_telegram_last_sent")
        if isinstance(last_sent, str) and last_sent == body:
            _debug("skip notify: duplicate message prevented")
            return None

        try:
            _debug(f"sending message to chat_id={chat_id} text_len={len(body)}")
            _send_telegram_message(token, chat_id, body)
            self.agent.set_data("_telegram_last_sent", body)
            _debug("sendMessage success")
        except Exception as exc:
            print(f"[telegram-notify] send error: {exc}")

        return None
