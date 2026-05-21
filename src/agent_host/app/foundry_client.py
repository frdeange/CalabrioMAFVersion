import json
import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential


logger = logging.getLogger("agent_host.foundry")


class FoundryClientManager:
    _instance: "FoundryClientManager | None" = None
    _instance_lock = threading.Lock()

    def __init__(self, project_endpoint: str, timeout_seconds: int = 30) -> None:
        self._project_endpoint = project_endpoint
        self._timeout_seconds = timeout_seconds
        self._credential: DefaultAzureCredential | None = None
        self._project_client: AIProjectClient | None = None
        self._openai_client: Any = None
        self._client_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="foundry")
        self._closed = False

    @classmethod
    def get_instance(
        cls, project_endpoint: str, timeout_seconds: int = 30
    ) -> "FoundryClientManager":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls(
                        project_endpoint=project_endpoint, timeout_seconds=timeout_seconds
                    )
        return cls._instance

    def _run_with_timeout(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        if self._closed:
            raise RuntimeError("Foundry client manager is closed")

        future: Future = self._executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=self._timeout_seconds)
        except FuturesTimeoutError as exc:
            cancelled = future.cancel()
            logger.error(
                "foundry_timeout",
                extra={
                    "event": "foundry_timeout",
                    "timeout_seconds": self._timeout_seconds,
                    "cancelled": cancelled,
                },
            )
            if not cancelled:
                logger.warning(
                    "foundry_timeout_cancellation_failed",
                    extra={
                        "event": "foundry_timeout_cancellation_failed",
                        "timeout_seconds": self._timeout_seconds,
                    },
                )
            raise TimeoutError(
                f"Foundry call timed out after {self._timeout_seconds}s"
            ) from exc

    def _ensure_clients(self) -> None:
        if self._project_client is not None and self._openai_client is not None:
            return

        if not self._project_endpoint.strip():
            raise ValueError("FOUNDRY_PROJECT_ENDPOINT is not configured")

        with self._client_lock:
            if self._project_client is None:
                self._credential = DefaultAzureCredential()
                self._project_client = AIProjectClient(
                    endpoint=self._project_endpoint,
                    credential=self._credential,
                )
                logger.info(
                    "foundry_project_client_initialized",
                    extra={"event": "foundry_project_client_initialized"},
                )
            if self._openai_client is None:
                self._openai_client = self._run_with_timeout(
                    self._project_client.get_openai_client
                )
                logger.info(
                    "foundry_openai_client_initialized",
                    extra={"event": "foundry_openai_client_initialized"},
                )

    def create_conversation(self) -> str:
        self._ensure_clients()
        try:
            conversation = self._run_with_timeout(self._openai_client.conversations.create)
            conversation_id = getattr(conversation, "id", "")
            if not conversation_id:
                raise RuntimeError("Foundry conversation id missing")
            return conversation_id
        except Exception:
            logger.exception(
                "foundry_create_conversation_failed",
                extra={"event": "foundry_create_conversation_failed"},
            )
            raise

    def _extract_response_text(self, response: Any) -> str:
        text = getattr(response, "output_text", None)
        if isinstance(text, str) and text.strip():
            return text

        chunks: list[str] = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                if getattr(content, "type", "") == "output_text":
                    value = getattr(content, "text", "")
                    if value:
                        chunks.append(value)
        return "".join(chunks).strip()

    def chat(self, agent_name: str, conversation_id: str, message: str) -> str:
        self._ensure_clients()
        try:
            response = self._run_with_timeout(
                self._openai_client.responses.create,
                conversation=conversation_id,
                extra_body={
                    "agent_reference": {"name": agent_name, "type": "agent_reference"}
                },
                input=message,
            )
            response_text = self._extract_response_text(response)
            if not response_text:
                raise RuntimeError("Foundry response text was empty")
            return response_text
        except Exception:
            logger.exception(
                "foundry_chat_failed",
                extra={
                    "event": "foundry_chat_failed",
                    "agent_name": agent_name,
                    "conversation_id": conversation_id,
                },
            )
            raise

    def chat_structured(
        self,
        agent_name: str,
        conversation_id: str,
        message: str,
        response_format: dict[str, Any],
    ) -> dict[str, Any]:
        self._ensure_clients()
        try:
            response = self._run_with_timeout(
                self._openai_client.responses.create,
                conversation=conversation_id,
                extra_body={
                    "agent_reference": {"name": agent_name, "type": "agent_reference"}
                },
                response_format=response_format,
                input=message,
            )
            response_text = self._extract_response_text(response)
            if not response_text:
                raise RuntimeError("Foundry structured response text was empty")
            return json.loads(response_text)
        except json.JSONDecodeError:
            logger.exception(
                "foundry_chat_structured_parse_failed",
                extra={
                    "event": "foundry_chat_structured_parse_failed",
                    "agent_name": agent_name,
                    "conversation_id": conversation_id,
                },
            )
            raise
        except Exception:
            logger.exception(
                "foundry_chat_structured_failed",
                extra={
                    "event": "foundry_chat_structured_failed",
                    "agent_name": agent_name,
                    "conversation_id": conversation_id,
                },
            )
            raise

    def health_check(self) -> bool:
        try:
            self.create_conversation()
            return True
        except Exception:
            logger.exception("foundry_health_check_failed", extra={"event": "foundry_health_check_failed"})
            return False

    def close(self) -> None:
        with self._client_lock:
            if self._closed:
                return

            for resource_name in ("_project_client", "_credential"):
                resource = getattr(self, resource_name, None)
                close = getattr(resource, "close", None)
                if callable(close):
                    try:
                        close()
                    except Exception:
                        logger.exception(
                            "foundry_resource_close_failed",
                            extra={
                                "event": "foundry_resource_close_failed",
                                "resource": resource_name,
                            },
                        )

            self._executor.shutdown(wait=False, cancel_futures=True)
            self._closed = True
