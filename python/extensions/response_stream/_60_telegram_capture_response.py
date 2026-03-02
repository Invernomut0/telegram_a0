"""Capture final response text from streaming tool-call payloads.

This extension inspects parsed assistant output and stores the final response
text (from response tool args) so `message_loop_end` can publish it to Telegram.
"""

from __future__ import annotations

import os
from typing import Any

try:
    from python.helpers.extension import Extension  # pyright: ignore[reportMissingImports]
except Exception:  # pragma: no cover - local fallback outside Agent Zero runtime
    class Extension:  # type: ignore[override]
        def __init__(self, agent=None, **kwargs):
            self.agent = agent


class TelegramCaptureResponseExtension(Extension):
    async def execute(self, parsed: dict[str, Any] | None = None, **kwargs) -> Any:
        if getattr(self.agent, "number", 0) != 0:
            return None

        debug = (os.getenv("TELEGRAM_DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"})

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
        else:
            _debug("response text empty after strip")

        return None
