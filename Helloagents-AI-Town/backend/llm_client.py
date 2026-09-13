"""Project-side LLM compatibility wrapper for CyberTown."""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from config import load_runtime_env

from hello_agents import HelloAgentsException, HelloAgentsLLM
from openai import OpenAI


class CyberTownLLM(HelloAgentsLLM):
    """HelloAgents LLM with tolerant response extraction for gateway APIs."""

    def __init__(
        self,
        *args: Any,
        max_retries: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        self._max_retries = max_retries
        load_runtime_env()
        super().__init__(*args, **kwargs)

    def _create_client(self) -> OpenAI:
        return OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self._max_retries
            if self._max_retries is not None
            else self._env_int("LLM_MAX_RETRIES", 0),
        )

    def invoke(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Non-streaming LLM call that accepts common OpenAI-compatible shapes."""
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]},
            )
            return self._extract_text(response)
        except Exception as e:
            raise HelloAgentsException(f"LLM调用失败: {str(e)}")

    def _extract_text(self, response: Any) -> str:
        if isinstance(response, str):
            parsed = self._try_parse_json(response)
            if parsed is not None:
                return self._extract_text(parsed)
            return response

        if isinstance(response, bytes):
            return self._extract_text(response.decode("utf-8", errors="replace"))

        if isinstance(response, dict):
            error = response.get("error")
            if error:
                raise HelloAgentsException(f"LLM返回错误: {error}")

            choices = response.get("choices")
            if choices:
                return self._extract_choice_text(choices[0])

            for key in ("output_text", "content", "text"):
                content = response.get(key)
                if content:
                    return self._stringify_content(content)

            dumped = json.dumps(response, ensure_ascii=False)
            raise HelloAgentsException(f"无法解析LLM响应: {dumped[:300]}")

        choices = getattr(response, "choices", None)
        if choices:
            return self._extract_choice_text(choices[0])

        for key in ("output_text", "content", "text"):
            content = getattr(response, key, None)
            if content:
                return self._stringify_content(content)

        raise HelloAgentsException(f"无法解析LLM响应类型: {type(response).__name__}")

    def _extract_choice_text(self, choice: Any) -> str:
        if isinstance(choice, dict):
            message = choice.get("message") or choice.get("delta")
            if message is not None:
                return self._extract_message_text(message)
            for key in ("content", "text"):
                content = choice.get(key)
                if content:
                    return self._stringify_content(content)

        message = getattr(choice, "message", None) or getattr(choice, "delta", None)
        if message is not None:
            return self._extract_message_text(message)

        for key in ("content", "text"):
            content = getattr(choice, key, None)
            if content:
                return self._stringify_content(content)

        raise HelloAgentsException(f"无法解析LLM choice: {choice}")

    def _extract_message_text(self, message: Any) -> str:
        if isinstance(message, dict):
            content = message.get("content")
        else:
            content = getattr(message, "content", None)

        if content is None:
            raise HelloAgentsException(f"无法解析LLM message: {message}")
        return self._stringify_content(content)

    def _stringify_content(self, content: Any) -> str:
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text") or item.get("content")
                    if text:
                        parts.append(str(text))
                else:
                    text = getattr(item, "text", None) or getattr(item, "content", None)
                    if text:
                        parts.append(str(text))
            if parts:
                return "".join(parts)

        return str(content)

    def _try_parse_json(self, value: str) -> Optional[Any]:
        stripped = value.strip()
        if not stripped or stripped[0] not in "[{":
            return None
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return None

    def _env_int(self, name: str, default: int) -> int:
        value = os.getenv(name)
        if not value:
            return default
        try:
            return max(0, int(value))
        except ValueError:
            return default
