"""Default model adapter manager implementation."""

from __future__ import annotations

from typing import Any

from dare_framework.config.types import Config, LLMConfig
from dare_framework.model.interfaces import IModelAdapterManager
from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.adapters.anthropic_adapter import AnthropicModelAdapter
from dare_framework.model.adapters.huawei_modelarts_adapter import HuaweiModelArtsModelAdapter
from dare_framework.model.adapters.openai_adapter import OpenAIModelAdapter
from dare_framework.model.adapters.openrouter_adapter import OpenRouterModelAdapter


class DefaultModelAdapterManager(IModelAdapterManager):
    """Resolve model adapters using Config.llm with a default OpenAI fallback."""

    def __init__(self, *, config: Config | None = None) -> None:
        self._config = config

    def load_model_adapter(self, *, config: Config | None = None) -> IModelAdapter | None:
        effective = config or self._config
        if effective is None:
            raise ValueError("DefaultModelAdapterManager requires a Config (in constructor or load_model_adapter).")
        llm = effective.llm
        adapter_name = _normalize_adapter_name(llm.adapter)
        if adapter_name == "openai":
            return _build_openai_adapter(llm)
        if adapter_name == "openrouter":
            return _build_openrouter_adapter(llm)
        if adapter_name == "anthropic":
            return _build_anthropic_adapter(llm)
        if adapter_name == "huawei-modelarts":
            return _build_huawei_modelarts_adapter(llm)
        raise ValueError(
            f"Unsupported model adapter '{adapter_name}'. Supported adapters: openai, openrouter, anthropic, huawei-modelarts."
        )



def _normalize_adapter_name(name: str | None) -> str:
    if not name:
        return "openai"
    return str(name).strip().lower()


def _build_openai_adapter(llm: LLMConfig) -> OpenAIModelAdapter:
    return OpenAIModelAdapter(
        name="openai",
        model=llm.model,
        api_key=llm.api_key,
        endpoint=llm.endpoint,
        http_client_options=_http_client_options_from_proxy(llm),
        extra=dict(llm.extra),
    )


def _build_openrouter_adapter(llm: LLMConfig) -> OpenRouterModelAdapter:
    return OpenRouterModelAdapter(
        name="openrouter",
        api_key=llm.api_key,
        model=llm.model,
        base_url=llm.endpoint,
        http_client_options=_http_client_options_from_proxy(llm),
        extra=dict(llm.extra),
    )


def _build_anthropic_adapter(llm: LLMConfig) -> AnthropicModelAdapter:
    return AnthropicModelAdapter(
        name="anthropic",
        api_key=llm.api_key,
        model=llm.model,
        base_url=llm.endpoint,
        http_client_options=_http_client_options_from_proxy(llm),
        extra=dict(llm.extra),
    )


def _build_huawei_modelarts_adapter(llm: LLMConfig) -> HuaweiModelArtsModelAdapter:
    return HuaweiModelArtsModelAdapter(
        name="huawei-modelarts",
        api_key=llm.api_key,
        model=llm.model,
        base_url=llm.endpoint,
        http_client_options=_http_client_options_from_proxy(llm),
        extra=dict(llm.extra),
    )


def _http_client_options_from_proxy(llm: LLMConfig) -> dict[str, Any]:
    proxy = llm.proxy
    options: dict[str, Any] = {}
    if proxy.disabled:
        options["trust_env"] = False
        options["proxy"] = None
        return options
    if proxy.use_system_proxy:
        options["trust_env"] = True
    if proxy.http or proxy.https:
        options["proxy"] = proxy.https or proxy.http
        options.setdefault("trust_env", False)
    return options


__all__ = ["DefaultModelAdapterManager"]
