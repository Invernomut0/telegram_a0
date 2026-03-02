"""Send Agent Zero notifications to Telegram at end of message-loop iteration."""

from __future__ import annotations

import json
import os
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


class TelegramNotifyExtension(Extension):
    async def execute(self, loop_data=None, **kwargs) -> Any:
        if getattr(self.agent, "number", 0) != 0:
            return None

        debug = (os.getenv("TELEGRAM_DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"})

        def _debug(message: str) -> None:
            if debug:
                print(f"[telegram-notify][debug] {message}")

        token = os.getenv("TELEGRAM_TOKEN", "").strip()
        chat_id = os.getenv("CHAT_ID", "").strip()
        if not token or not chat_id:
            _debug(
                "skip notify: missing env -> "
                f"TELEGRAM_TOKEN={'set' if bool(token) else 'missing'} "
                f"CHAT_ID={'set' if bool(chat_id) else 'missing'}"
            )
            return None

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

        prefix = os.getenv("TELEGRAM_NOTIFY_PREFIX", "🤖 Agent0\n")
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
