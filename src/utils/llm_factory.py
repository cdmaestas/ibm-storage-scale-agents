"""LLM provider factory.

Builds a LangChain chat model from the ``[llm]`` config section, supporting
multiple backends behind a single ``provider`` key:

- ``ollama``    - local or remote Ollama (bundled, no extra required)
- ``openai``    - any OpenAI-compatible endpoint: OpenAI, vLLM, LM Studio,
                  llama.cpp server, Together, Groq, ...  (extra: ``openai``)
- ``anthropic`` - Anthropic Claude API                  (extra: ``anthropic``)
- ``azure``     - Azure OpenAI                          (extra: ``openai``)
- ``bedrock``   - AWS Bedrock                           (extra: ``aws``)

Configuration precedence for every setting is: environment variable > INI
value > built-in default. Environment variables use the ``SCALE_AGENTS_LLM_``
prefix (e.g. ``SCALE_AGENTS_LLM_BASE_URL``). API keys are read from the
environment only and are never taken from the INI file, so credentials do not
land in a committed config.
"""

from __future__ import annotations

import logging
import os
from configparser import SectionProxy

logger = logging.getLogger(__name__)

# Providers selectable via the `provider` key.
SUPPORTED_PROVIDERS = ("ollama", "openai", "anthropic", "azure", "bedrock")

# Legacy / LiteLLM-style "provider/model" prefixes we recognise on model_name.
# Kept so existing configs like "ollama_chat/qwen3:latest" keep working.
_MODEL_PREFIX_TO_PROVIDER = {
    "ollama_chat": "ollama",
    "ollama": "ollama",
    "openai": "openai",
    "anthropic": "anthropic",
    "azure": "azure",
    "bedrock": "bedrock",
}

_ENV_PREFIX = "SCALE_AGENTS_LLM_"


def _get(llm_config: SectionProxy, key: str, default: str | None = None) -> str | None:
    """Resolve a setting with precedence: env var > INI > default.

    The env var name is ``SCALE_AGENTS_LLM_<KEY>`` (upper-cased).
    Empty strings are treated as "not set" so a blank INI value falls through
    to the default rather than overriding it with "".
    """
    env_val = os.environ.get(_ENV_PREFIX + key.upper())
    if env_val is not None and env_val != "":
        return env_val
    ini_val = llm_config.get(key)
    if ini_val is not None and ini_val.strip() != "":
        return ini_val.strip()
    return default


def _split_model_prefix(model_name: str) -> tuple[str | None, str]:
    """Split a ``provider/model`` prefix off a model name.

    Returns ``(inferred_provider, bare_model)``. If there is no recognised
    prefix, ``inferred_provider`` is ``None`` and the model is returned as-is.
    """
    if "/" in model_name:
        prefix, rest = model_name.split("/", 1)
        provider = _MODEL_PREFIX_TO_PROVIDER.get(prefix.lower())
        if provider:
            return provider, rest
    return None, model_name


def _resolve_provider_and_model(llm_config: SectionProxy) -> tuple[str, str]:
    """Determine the provider and bare model name from config.

    An explicit ``provider`` key wins. Otherwise the provider is inferred from
    a legacy ``provider/model`` prefix on ``model_name`` (defaulting to
    ``ollama`` when there is no prefix, preserving prior behaviour).
    """
    # Accept the friendly SCALE_AGENTS_LLM_MODEL alias in addition to the
    # generic SCALE_AGENTS_LLM_MODEL_NAME / INI model_name.
    model_name = os.environ.get(_ENV_PREFIX + "MODEL") or _get(llm_config, "model_name")
    if not model_name:
        raise ValueError(
            "Missing model name: set 'model_name' in [llm], or SCALE_AGENTS_LLM_MODEL / SCALE_AGENTS_LLM_MODEL_NAME."
        )

    inferred_provider, bare_model = _split_model_prefix(model_name)

    explicit = _get(llm_config, "provider")
    if explicit:
        provider = explicit.lower()
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported LLM provider '{provider}'. Supported providers: {', '.join(SUPPORTED_PROVIDERS)}"
            )
        # When both are given, honour the explicit provider but still strip a
        # matching legacy prefix from the model id.
        return provider, bare_model

    # No explicit provider: fall back to the inferred one, else default ollama.
    return (inferred_provider or "ollama"), bare_model


def _require(provider: str, extra: str, import_error: ImportError) -> None:
    """Raise a clear, actionable error when a provider's extra is not installed."""
    raise RuntimeError(
        f"LLM provider '{provider}' requires the optional '{extra}' dependencies, "
        f"which are not installed. Install them with:\n"
        f"    uv sync --extra {extra}\n"
        f"or:\n"
        f"    pip install 'scale-agents[{extra}]'"
    ) from import_error


def build_llm(llm_config: SectionProxy):
    """Build a LangChain chat model from the ``[llm]`` config section.

    Args:
        llm_config: The ``[llm]`` section of the parsed configuration.

    Returns:
        A configured LangChain ``BaseChatModel`` instance.

    Raises:
        ValueError: If required settings are missing or the provider is unknown.
        RuntimeError: If the selected provider's optional dependency is missing.
    """
    provider, model = _resolve_provider_and_model(llm_config)

    timeout = float(_get(llm_config, "timeout", "60.0"))
    temperature = float(_get(llm_config, "temperature", "0"))
    base_url = _get(llm_config, "base_url")
    # API keys come from the environment only, never from the INI.
    api_key = os.environ.get(_ENV_PREFIX + "API_KEY") or None

    logger.info(f"Building LLM: provider={provider}, model={model}, base_url={base_url or 'default'}")

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=model,
            base_url=base_url or "http://localhost:11434",
            temperature=temperature,
            timeout=timeout,
        )

    if provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as e:
            _require(provider, "openai", e)
        # Local OpenAI-compatible servers (vLLM, LM Studio, llama.cpp) usually
        # ignore the key but the client still requires a non-empty value.
        if api_key is None and base_url:
            api_key = "EMPTY"
        return ChatOpenAI(
            model=model,
            base_url=base_url or None,
            api_key=api_key,
            temperature=temperature,
            timeout=timeout,
        )

    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as e:
            _require(provider, "anthropic", e)
        return ChatAnthropic(
            model=model,
            base_url=base_url or None,
            api_key=api_key,  # falls back to ANTHROPIC_API_KEY when None
            temperature=temperature,
            timeout=timeout,
        )

    if provider == "azure":
        try:
            from langchain_openai import AzureChatOpenAI
        except ImportError as e:
            _require(provider, "openai", e)
        api_version = _get(llm_config, "azure_api_version")
        if not base_url:
            raise ValueError(
                "Azure provider requires 'base_url' (the Azure OpenAI endpoint), "
                "set it in [llm] or via SCALE_AGENTS_LLM_BASE_URL."
            )
        if not api_version:
            raise ValueError(
                "Azure provider requires 'azure_api_version' in [llm] or SCALE_AGENTS_LLM_AZURE_API_VERSION."
            )
        return AzureChatOpenAI(
            azure_deployment=model,
            azure_endpoint=base_url,
            api_version=api_version,
            api_key=api_key,  # falls back to AZURE_OPENAI_API_KEY when None
            temperature=temperature,
            timeout=timeout,
        )

    if provider == "bedrock":
        try:
            from langchain_aws import ChatBedrockConverse
        except ImportError as e:
            _require(provider, "aws", e)
        # Credentials come from the standard AWS chain (env vars, shared config,
        # or instance/task role) via boto3.
        region = _get(llm_config, "aws_region") or os.environ.get("AWS_REGION")
        return ChatBedrockConverse(
            model=model,
            region_name=region,
            temperature=temperature,
        )

    # _resolve_provider_and_model already validates the provider, so this is
    # unreachable; assert loudly if that invariant is ever broken.
    raise AssertionError(f"Unhandled provider '{provider}'")
