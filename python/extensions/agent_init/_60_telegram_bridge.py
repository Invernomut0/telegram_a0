"""Telegram inbound bridge for Agent Zero.

This extension starts a background polling loop that reads Telegram bot updates
and forwards incoming chat messages to Agent Zero via `/api_message`.

Required secrets/environment variables (typically in Agent Zero secrets):
- TELEGRAM_TOKEN
- AGENT_ZERO_API_KEY

Recommended:
- CHAT_ID (used as outbound target for global notify when enabled)
- AGENT_ZERO_URL (default: http://localhost:80)
- TELEGRAM_DEBUG=true (verbose diagnostics)
"""

from __future__ import annotations

import json
import os
import threading
import time
import errno
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib import error, parse, request

try:
    import fcntl
except Exception:  # pragma: no cover - non-posix fallback
    fcntl = None  # type: ignore[assignment]

try:
    from python.helpers.extension import Extension  # pyright: ignore[reportMissingImports]
except Exception:  # pragma: no cover - local fallback outside Agent Zero runtime
    class Extension:  # type: ignore[override]
        def __init__(self, agent=None, **kwargs):
            self.agent = agent


def _http_json(url: str, payload: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any]:
    data = None
    headers = {"Content-Type": "application/json"}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = request.Request(url=url, data=data, headers=headers, method="POST")

    with request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _safe_int(value: str, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _as_bool(value: str, default: bool = False) -> bool:
    raw = (value or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _mask(value: str, show_head: int = 4, show_tail: int = 3) -> str:
    if not value:
        return "<empty>"
    if len(value) <= show_head + show_tail:
        return "*" * len(value)
    return f"{value[:show_head]}...{value[-show_tail:]}"


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


class TelegramBridgeConfig:
    def __init__(
        self,
        token: str,
        api_url: str,
        api_key: str,
        allowed_chat_ids: set[str],
        poll_interval_sec: int,
        long_poll_timeout_sec: int,
        lifetime_hours: int,
        default_project: str | None,
        skip_old_updates_on_start: bool,
        offset_file: str,
        contexts_file: str,
        lock_file: str,
        auto_delete_webhook_on_conflict: bool,
        conflict_backoff_sec: int,
        conflict_max_retries: int,
        use_chat_id_as_allowed: bool,
        reply_via_bridge: bool,
        debug: bool,
        secrets_file: str,
    ):
        self.token = token
        self.api_url = api_url
        self.api_key = api_key
        self.allowed_chat_ids = allowed_chat_ids
        self.poll_interval_sec = poll_interval_sec
        self.long_poll_timeout_sec = long_poll_timeout_sec
        self.lifetime_hours = lifetime_hours
        self.default_project = default_project
        self.skip_old_updates_on_start = skip_old_updates_on_start
        self.offset_file = offset_file
        self.contexts_file = contexts_file
        self.lock_file = lock_file
        self.auto_delete_webhook_on_conflict = auto_delete_webhook_on_conflict
        self.conflict_backoff_sec = conflict_backoff_sec
        self.conflict_max_retries = conflict_max_retries
        self.use_chat_id_as_allowed = use_chat_id_as_allowed
        self.reply_via_bridge = reply_via_bridge
        self.debug = debug
        self.secrets_file = secrets_file

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.api_key)

    @staticmethod
    def from_env() -> "TelegramBridgeConfig":
        env_data = dict(os.environ)
        secrets_file = env_data.get("AGENT_ZERO_SECRETS_FILE", "/a0/usr/secrets.env").strip() or "/a0/usr/secrets.env"
        secrets_data = _parse_env_file(secrets_file)

        token = _resolve_secret(
            env_data,
            secrets_data,
            keys=("TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN"),
        )
        api_url = _resolve_secret(
            env_data,
            secrets_data,
            keys=("AGENT_ZERO_URL", "A0_URL"),
        ).rstrip("/") or "http://localhost:80"
        api_key = _resolve_secret(
            env_data,
            secrets_data,
            keys=("AGENT_ZERO_API_KEY", "API_KEY", "A0_API_KEY"),
        )
        debug = _as_bool(_resolve_secret(env_data, secrets_data, keys=("TELEGRAM_DEBUG",)) or "false", False)

        chat_id = _resolve_secret(env_data, secrets_data, keys=("CHAT_ID", "TELEGRAM_CHAT_ID"))
        raw_allowed = _resolve_secret(env_data, secrets_data, keys=("TELEGRAM_ALLOWED_CHAT_IDS",))
        allowed = {x.strip() for x in raw_allowed.split(",") if x.strip()}
        use_chat_id_as_allowed = _as_bool(
            _resolve_secret(env_data, secrets_data, keys=("TELEGRAM_USE_CHAT_ID_AS_ALLOWED", "TELEGRAM_STRICT_CHAT_FILTER"))
            or "false",
            False,
        )
        reply_via_bridge = _as_bool(
            _resolve_secret(env_data, secrets_data, keys=("TELEGRAM_REPLY_VIA_BRIDGE",)) or "true",
            True,
        )
        if chat_id and not allowed and use_chat_id_as_allowed:
            allowed = {chat_id}

        return TelegramBridgeConfig(
            token=token,
            api_url=api_url,
            api_key=api_key,
            allowed_chat_ids=allowed,
            poll_interval_sec=_safe_int(_resolve_secret(env_data, secrets_data, keys=("TELEGRAM_POLL_INTERVAL_SEC",)) or "2", 2),
            long_poll_timeout_sec=_safe_int(_resolve_secret(env_data, secrets_data, keys=("TELEGRAM_LONG_POLL_TIMEOUT_SEC",)) or "20", 20),
            lifetime_hours=_safe_int(_resolve_secret(env_data, secrets_data, keys=("TELEGRAM_CONTEXT_LIFETIME_HOURS",)) or "24", 24),
            default_project=_resolve_secret(env_data, secrets_data, keys=("TELEGRAM_DEFAULT_PROJECT",)) or None,
            skip_old_updates_on_start=_as_bool(_resolve_secret(env_data, secrets_data, keys=("TELEGRAM_SKIP_OLD_UPDATES",)) or "true", True),
            offset_file=_resolve_secret(env_data, secrets_data, keys=("TELEGRAM_OFFSET_FILE",)) or "/a0/tmp/telegram_offset.txt",
            contexts_file=_resolve_secret(env_data, secrets_data, keys=("TELEGRAM_CONTEXTS_FILE",)) or "/a0/tmp/telegram_contexts.json",
            lock_file=_resolve_secret(env_data, secrets_data, keys=("TELEGRAM_POLL_LOCK_FILE",)) or "/a0/tmp/telegram_poll.lock",
            auto_delete_webhook_on_conflict=_as_bool(
                _resolve_secret(env_data, secrets_data, keys=("TELEGRAM_AUTO_DELETE_WEBHOOK_ON_CONFLICT",)) or "true",
                True,
            ),
            conflict_backoff_sec=_safe_int(
                _resolve_secret(env_data, secrets_data, keys=("TELEGRAM_CONFLICT_BACKOFF_SEC",)) or "10",
                10,
            ),
            conflict_max_retries=_safe_int(
                _resolve_secret(env_data, secrets_data, keys=("TELEGRAM_CONFLICT_MAX_RETRIES",)) or "12",
                12,
            ),
            use_chat_id_as_allowed=use_chat_id_as_allowed,
            reply_via_bridge=reply_via_bridge,
            debug=debug,
            secrets_file=secrets_file,
        )


class TelegramInboundWorker:
    def __init__(self, config: TelegramBridgeConfig):
        self.cfg = config
        self._running = True
        self._lock = threading.Lock()
        self._contexts: dict[str, str] = self._load_contexts()
        self._poll_lock_handle: Any | None = None
        self._conflict_streak = 0
        self._blocked_chat_logged: set[str] = set()

    def _debug(self, message: str) -> None:
        if self.cfg.debug:
            print(f"[telegram-bridge][debug] {message}")

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        if not self.cfg.enabled:
            print("[telegram-bridge] Disabled: missing TELEGRAM_TOKEN or AGENT_ZERO_API_KEY")
            self._debug(
                "startup env status -> "
                f"TELEGRAM_TOKEN={'set' if bool(self.cfg.token) else 'missing'} "
                f"AGENT_ZERO_API_KEY={'set' if bool(self.cfg.api_key) else 'missing'} "
                f"AGENT_ZERO_URL={self.cfg.api_url}"
            )
            return

        if not self._try_acquire_poll_lock():
            print("[telegram-bridge] Poller not started: another local process already holds the poll lock")
            return

        offset = self._load_offset()

        if self.cfg.skip_old_updates_on_start and offset is None:
            offset = self._bootstrap_offset()
            self._save_offset(offset)

        print("[telegram-bridge] Inbound worker started")
        self._debug(
            "config -> "
            f"api_url={self.cfg.api_url} "
            f"secrets_file={self.cfg.secrets_file} "
            f"allowed_chat_ids={sorted(list(self.cfg.allowed_chat_ids)) if self.cfg.allowed_chat_ids else 'ALL'} "
            f"use_chat_id_as_allowed={self.cfg.use_chat_id_as_allowed} "
            f"reply_via_bridge={self.cfg.reply_via_bridge} "
            f"poll_interval={self.cfg.poll_interval_sec}s "
            f"long_poll_timeout={self.cfg.long_poll_timeout_sec}s "
            f"lifetime_hours={self.cfg.lifetime_hours} "
            f"default_project={self.cfg.default_project or '<none>'} "
            f"offset_file={self.cfg.offset_file} "
            f"contexts_file={self.cfg.contexts_file} "
            f"lock_file={self.cfg.lock_file} "
            f"auto_delete_webhook_on_conflict={self.cfg.auto_delete_webhook_on_conflict} "
            f"conflict_backoff_sec={self.cfg.conflict_backoff_sec} "
            f"conflict_max_retries={self.cfg.conflict_max_retries}"
        )

        try:
            while self._running:
                try:
                    updates = self._get_updates(offset)
                    self._conflict_streak = 0
                    self._debug(f"getUpdates returned {len(updates)} updates (offset={offset})")
                    for upd in updates:
                        upd_id = int(upd.get("update_id", 0))
                        if upd_id:
                            offset = upd_id + 1
                            self._save_offset(offset)
                        self._handle_update(upd)

                except error.HTTPError as exc:
                    if exc.code == 409:
                        self._handle_polling_conflict(exc)
                    else:
                        body = exc.read().decode("utf-8", errors="ignore")
                        print(f"[telegram-bridge] polling HTTP {exc.code}: {body[:500]}")
                        time.sleep(max(1, self.cfg.poll_interval_sec))
                except Exception as exc:
                    print(f"[telegram-bridge] polling error: {exc}")
                    time.sleep(max(1, self.cfg.poll_interval_sec))
        finally:
            self._release_poll_lock()

    def _handle_polling_conflict(self, exc: error.HTTPError) -> None:
        body = exc.read().decode("utf-8", errors="ignore")
        self._conflict_streak += 1
        print(f"[telegram-bridge] polling conflict (409): {body[:500]}")

        if self.cfg.debug:
            try:
                webhook_info = self._telegram_api("getWebhookInfo", {})
                result = webhook_info.get("result") if isinstance(webhook_info, dict) else None
                if isinstance(result, dict):
                    self._debug(
                        "webhook info on 409 -> "
                        f"url={result.get('url')!r} "
                        f"pending_update_count={result.get('pending_update_count')} "
                        f"last_error_message={result.get('last_error_message')!r}"
                    )
            except Exception as info_exc:
                self._debug(f"getWebhookInfo failed on 409: {info_exc}")

        if self.cfg.auto_delete_webhook_on_conflict:
            try:
                self._telegram_api("deleteWebhook", {"drop_pending_updates": False})
                self._debug("deleteWebhook executed after 409 conflict")
            except Exception as webhook_exc:
                self._debug(f"deleteWebhook failed after 409 conflict: {webhook_exc}")

        if self.cfg.conflict_max_retries > 0 and self._conflict_streak >= self.cfg.conflict_max_retries:
            print(
                "[telegram-bridge] stopping inbound polling after repeated 409 conflicts "
                f"(count={self._conflict_streak}). "
                "Another instance is likely polling with the same TELEGRAM_TOKEN."
            )
            self._running = False
            return

        time.sleep(max(1, self.cfg.conflict_backoff_sec))

    def _try_acquire_poll_lock(self) -> bool:
        if fcntl is None:
            self._debug("fcntl unavailable; poll lock disabled on this platform")
            return True

        path = Path(self.cfg.lock_file)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            handle = open(path, "a+", encoding="utf-8")
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as lock_exc:
                handle.close()
                if lock_exc.errno in {errno.EACCES, errno.EAGAIN}:
                    return False
                self._debug(f"unexpected poll lock error: {lock_exc}")
                return False

            handle.seek(0)
            handle.truncate(0)
            handle.write(str(os.getpid()))
            handle.flush()
            self._poll_lock_handle = handle
            return True
        except Exception as exc:
            self._debug(f"unable to create/acquire poll lock {path}: {exc}")
            return False

    def _release_poll_lock(self) -> None:
        handle = self._poll_lock_handle
        self._poll_lock_handle = None
        if not handle:
            return

        try:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass

        try:
            handle.close()
        except Exception:
            pass

    def _telegram_api(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"https://api.telegram.org/bot{self.cfg.token}/{method}"
        data = _http_json(url, payload=payload, timeout=self.cfg.long_poll_timeout_sec + 5)
        if not data.get("ok", False):
            raise RuntimeError(f"Telegram API error on {method}: {data}")
        return data

    def _get_updates(self, offset: int | None) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "timeout": self.cfg.long_poll_timeout_sec,
            "allowed_updates": ["message", "channel_post"],
        }
        if offset is not None:
            payload["offset"] = offset

        data = self._telegram_api("getUpdates", payload)
        result = data.get("result", [])
        return result if isinstance(result, list) else []

    def _bootstrap_offset(self) -> int:
        data = self._telegram_api("getUpdates", {"timeout": 0, "allowed_updates": ["message", "channel_post"]})
        result = data.get("result", [])
        if not isinstance(result, list) or not result:
            return 0

        max_id = max(int(x.get("update_id", 0)) for x in result)
        return max_id + 1

    def _handle_update(self, upd: dict[str, Any]) -> None:
        msg = upd.get("message") or upd.get("channel_post")
        if not isinstance(msg, dict):
            self._debug(f"unsupported update keys={list(upd.keys())[:6]}, skipping")
            return

        text = (msg.get("text") or "").strip()
        if not text:
            self._debug("received non-text or empty message, skipping")
            return

        chat = msg.get("chat") or {}
        chat_id = str(chat.get("id", "")).strip()
        if not chat_id:
            self._debug("message without chat_id, skipping")
            return

        if self.cfg.allowed_chat_ids and chat_id not in self.cfg.allowed_chat_ids:
            if chat_id not in self._blocked_chat_logged:
                print(
                    "[telegram-bridge] inbound skipped: unauthorized chat "
                    f"chat_id={chat_id}. "
                    "Set TELEGRAM_ALLOWED_CHAT_IDS to include this chat, "
                    "or leave it empty to accept all inbound chats."
                )
                self._blocked_chat_logged.add(chat_id)
            self._debug(f"chat_id={chat_id} not in allowed list, skipping")
            return

        sender = msg.get("from") or {}
        if bool(sender.get("is_bot")):
            self._debug("message from bot user, skipping")
            return

        self._debug(f"inbound message chat_id={chat_id} text={text[:120]!r}")

        if text in {"/start", "/help"}:
            self._send_telegram(chat_id, "✅ Telegram ↔ Agent0 bridge is active. Send a message and I will forward it to Agent0.")
            return

        if text.startswith("/reset"):
            self._contexts.pop(chat_id, None)
            self._save_contexts()
            self._send_telegram(chat_id, "♻️ Conversation context has been reset.")
            return

        self._forward_to_agent(chat_id, text)

    def _forward_to_agent(self, chat_id: str, text: str) -> None:
        context_id = self._contexts.get(chat_id)

        payload: dict[str, Any] = {
            "message": text,
            "lifetime_hours": self.cfg.lifetime_hours,
        }

        if context_id:
            payload["context_id"] = context_id
        elif self.cfg.default_project:
            payload["project"] = self.cfg.default_project

        target_urls = self._build_agent_message_urls()
        self._debug(
            "forwarding to Agent0 -> "
            f"target_urls={target_urls} "
            f"chat_id={chat_id} "
            f"has_context_id={bool(context_id)} "
            f"has_project={bool(payload.get('project'))} "
            f"text_len={len(text)}"
        )

        data = None
        last_connection_error: Exception | None = None

        for url in target_urls:
            try:
                req = request.Request(
                    url=url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "X-API-KEY": self.cfg.api_key,
                    },
                    method="POST",
                )

                with request.urlopen(req, timeout=180) as resp:
                    raw = resp.read().decode("utf-8")
                    data = json.loads(raw) if raw else {}

                self._debug(
                    f"Agent0 response status=ok url={url} "
                    f"context_id={data.get('context_id') if isinstance(data, dict) else None} "
                    f"has_response={bool(isinstance(data, dict) and data.get('response'))}"
                )

                new_context_id = data.get("context_id") if isinstance(data, dict) else None
                if isinstance(new_context_id, str) and new_context_id.strip():
                    self._contexts[chat_id] = new_context_id.strip()
                    self._save_contexts()

                if self.cfg.reply_via_bridge:
                    response_text = self._extract_response_text(data)
                    if response_text:
                        self._send_telegram(chat_id, response_text)
                        self._debug(
                            "inbound reply sent directly from bridge "
                            f"chat_id={chat_id} text_len={len(response_text)}"
                        )
                    else:
                        self._debug("no response text found in /api_message payload")
                return

            except error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="ignore")
                self._debug(f"Agent0 HTTPError url={url} code={exc.code} body={body[:500]!r}")
                self._send_telegram(chat_id, f"❌ Agent0 HTTP error {exc.code}: {body[:1200]}")
                return
            except error.URLError as exc:
                last_connection_error = exc
                self._debug(f"Agent0 URLError on {url}: {exc}")
                continue
            except Exception as exc:
                self._debug(f"Agent0 generic error on {url}: {exc}")
                self._send_telegram(chat_id, f"❌ Error forwarding to Agent0: {exc}")
                return

        details = str(last_connection_error) if last_connection_error else "endpoint unreachable"
        self._send_telegram(
            chat_id,
            "❌ Could not reach Agent0 on any configured endpoint. "
            f"Check AGENT_ZERO_URL. Details: {details}",
        )

    def _build_agent_message_urls(self) -> list[str]:
        base_url = self.cfg.api_url.rstrip("/")
        primary = f"{base_url}/api_message"
        urls: list[str] = [primary]

        try:
            parsed = parse.urlparse(base_url)
            host = (parsed.hostname or "").strip().lower()
            if host in {"localhost", "127.0.0.1"}:
                if parsed.port == 8080:
                    alt_netloc = f"{host}:80"
                elif parsed.port in {80, None}:
                    alt_netloc = f"{host}:8080"
                else:
                    alt_netloc = ""

                if alt_netloc:
                    alt_base = parse.urlunparse((parsed.scheme or "http", alt_netloc, parsed.path, "", "", "")).rstrip("/")
                    alt_url = f"{alt_base}/api_message"
                    if alt_url not in urls:
                        urls.append(alt_url)
        except Exception:
            pass

        return urls

    def _extract_response_text(self, data: dict[str, Any] | None) -> str:
        if not isinstance(data, dict):
            return ""

        direct = data.get("response")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()

        tool_args = data.get("tool_args")
        if isinstance(tool_args, dict):
            tool_text = tool_args.get("text") or tool_args.get("message")
            if isinstance(tool_text, str) and tool_text.strip():
                return tool_text.strip()

        payload = data.get("payload")
        if isinstance(payload, dict):
            payload_text = payload.get("text") or payload.get("message") or payload.get("response")
            if isinstance(payload_text, str) and payload_text.strip():
                return payload_text.strip()

        return ""

    def _send_telegram(self, chat_id: str, text: str) -> None:
        payload = {
            "chat_id": chat_id,
            "text": text[:4000],
            "disable_web_page_preview": True,
        }
        try:
            self._telegram_api("sendMessage", payload)
            self._debug(f"sendMessage ok chat_id={chat_id} text_len={len(payload['text'])}")
        except Exception as exc:
            print(f"[telegram-bridge] sendMessage error: {exc}")

    def _load_offset(self) -> int | None:
        path = Path(self.cfg.offset_file)
        try:
            if not path.exists():
                return None
            value = path.read_text(encoding="utf-8").strip()
            if not value:
                return None
            return int(value)
        except Exception:
            return None

    def _save_offset(self, offset: int) -> None:
        path = Path(self.cfg.offset_file)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(offset), encoding="utf-8")
        except Exception:
            pass

    def _load_contexts(self) -> dict[str, str]:
        path = Path(self.cfg.contexts_file)
        try:
            if not path.exists():
                return {}
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw) if raw else {}
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except Exception:
            pass
        return {}

    def _save_contexts(self) -> None:
        path = Path(self.cfg.contexts_file)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                path.write_text(json.dumps(self._contexts), encoding="utf-8")
        except Exception:
            pass


_BOOTSTRAP_LOCK = threading.Lock()
_BOOTSTRAP_STARTED = False


def _is_root_agent_number(agent: Any) -> bool:
    raw_number = getattr(agent, "number", 0)
    try:
        return int(raw_number) == 0
    except Exception:
        return str(raw_number).strip() == "0"


def _bootstrap_inbound_worker(reason: str, agent: Any | None = None) -> bool:
    global _BOOTSTRAP_STARTED

    with _BOOTSTRAP_LOCK:
        if _BOOTSTRAP_STARTED:
            return False

        cfg = TelegramBridgeConfig.from_env()
        if not cfg.enabled:
            # Keep this log visible even when debug is off: missing secrets is a common root cause.
            print("[telegram-bridge] Bootstrap skipped: missing TELEGRAM_TOKEN or AGENT_ZERO_API_KEY")
            if cfg.debug:
                print(
                    "[telegram-bridge][debug] bootstrap env -> "
                    f"reason={reason} "
                    f"TELEGRAM_TOKEN={_mask(cfg.token)} "
                    f"AGENT_ZERO_API_KEY={_mask(cfg.api_key)} "
                    f"AGENT_ZERO_URL={cfg.api_url} "
                    f"SECRETS_FILE={cfg.secrets_file}"
                )
            _BOOTSTRAP_STARTED = True
            return False

        worker = TelegramInboundWorker(cfg)
        thread = threading.Thread(
            target=worker.run,
            daemon=True,
            name="telegram-inbound-bridge",
        )
        thread.start()

        if agent is not None:
            try:
                agent.set_data("_telegram_inbound_worker", worker)
            except Exception:
                pass

        _BOOTSTRAP_STARTED = True
        print(f"[telegram-bridge] Extension initialized (reason={reason})")
        return True


class TelegramBridgeExtension(Extension):
    _started = False
    _start_lock = threading.Lock()

    @staticmethod
    def _is_root_agent(agent: Any) -> bool:
        return _is_root_agent_number(agent)

    async def execute(self, **kwargs) -> Any:
        # Start only once, on top-level agent.
        if not self._is_root_agent(self.agent):
            return None

        with TelegramBridgeExtension._start_lock:
            if TelegramBridgeExtension._started:
                return None

            _bootstrap_inbound_worker(reason="agent_init", agent=self.agent)
            TelegramBridgeExtension._started = True

        return None


# Fallback bootstrap: in some Agent Zero runtimes the agent_init hook may not be invoked.
# Starting here ensures inbound polling can still run as soon as this module is imported.
try:
    _bootstrap_inbound_worker(reason="module_import", agent=None)
except Exception as _bootstrap_exc:
    print(f"[telegram-bridge] Bootstrap error on module import: {_bootstrap_exc}")
