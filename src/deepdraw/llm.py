"""LLM factory for DeepDraw agents.

Supports two providers out of the box:
- ``openai``    — official OpenAI API **and** any third-party vendor that
  follows the OpenAI Chat Completions protocol (DeepSeek, Moonshot,
  Volcengine Ark, SiliconFlow, OpenRouter, Azure OpenAI, self-hosted
  vLLM/Ollama in OpenAI mode, ...). Differentiation happens via
  ``base_url`` (``openai_api_base`` on the underlying ``ChatOpenAI``).
- ``anthropic`` — official Anthropic API.

Configuration is env-driven. Each agent declares a *profile* name in
``_LLM_CONFIG``; the profile resolves to a concrete chat model with the
right ``base_url``, ``api_key``, and ``model`` id.

Built-in profile names (overridable via env):

    gpt4o               openai:gpt-4o
    gpt4o_mini          openai:gpt-4o-mini
    claude_opus_46      anthropic:claude-opus-4-6
    claude_sonnet_45    anthropic:claude-sonnet-4-5
    deepseek_chat       DeepSeek official (uses OPENAI_COMPAT_* if set)
    openai_compat       whatever OPENAI_COMPAT_* env says

Env variables (read on each call so tests can mutate them):

    DEEPDRAW_LLM_DEFAULT         default profile name; default ``gpt4o``
    OPENAI_API_KEY               OpenAI official
    ANTHROPIC_API_KEY            Anthropic official
    OPENAI_COMPAT_BASE_URL       required for ``openai_compat`` / ``deepseek_chat``
    OPENAI_COMPAT_API_KEY        defaults to ``OPENAI_API_KEY`` if unset
    OPENAI_COMPAT_MODEL          default model id for ``openai_compat`` profile
    OPENAI_COMPAT_HEADERS        optional ``Key: Val`` pairs, one per line

Per-agent overrides: set ``DEEPDRAW_LLM_<AGENT>`` to a profile name, e.g.
``DEEPDRAW_LLM_CHIEF_VERIFIER=claude_opus_46``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

try:
    from langchain.chat_models import init_chat_model  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    from langchain_core.chat_models import init_chat_model  # type: ignore[no-redef]


# ---------------------------------------------------------------------------
# Profile model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelProfile:
    """Resolved chat-model profile: provider + kwargs for init_chat_model."""

    name: str
    provider: str
    model_id: str
    temperature: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    def init_kwargs(self) -> dict[str, Any]:
        """Materialize kwargs for ``init_chat_model``."""
        kw: dict[str, Any] = {
            "model": f"{self.provider}:{self.model_id}",
            "temperature": self.temperature,
        }
        kw.update(self.extra)
        return kw


# ---------------------------------------------------------------------------
# Built-in profile catalog
# ---------------------------------------------------------------------------


_BUILTIN_PROFILES: dict[str, ModelProfile] = {
    "gpt4o": ModelProfile(
        name="gpt4o", provider="openai", model_id="gpt-4o", temperature=0.0
    ),
    "gpt4o_mini": ModelProfile(
        name="gpt4o_mini", provider="openai", model_id="gpt-4o-mini", temperature=0.0
    ),
    "claude_opus_46": ModelProfile(
        name="claude_opus_46",
        provider="anthropic",
        model_id="claude-opus-4-6",
        temperature=0.0,
    ),
    "claude_sonnet_45": ModelProfile(
        name="claude_sonnet_45",
        provider="anthropic",
        model_id="claude-sonnet-4-5",
        temperature=0.0,
    ),
    "deepseek_chat": ModelProfile(
        name="deepseek_chat",
        provider="openai",  # langchain 1.x has no openai-compatible key;
        # base_url flips the request to a third-party endpoint.
        model_id="deepseek-chat",
        temperature=0.3,
    ),
    "openai_compat": ModelProfile(
        name="openai_compat",
        provider="openai",
        model_id=os.environ.get("OPENAI_COMPAT_MODEL", "gpt-4o-mini"),
        temperature=0.0,
    ),
}


# ---------------------------------------------------------------------------
# Env helpers
# ---------------------------------------------------------------------------


def _parse_extra_headers(text: str | None) -> dict[str, str]:
    """Parse ``Key: Value`` lines into a header dict. Empty/None → ``{}``."""
    if not text:
        return {}
    headers: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        headers[k.strip()] = v.strip()
    return headers


def _openai_compat_extra() -> dict[str, Any]:
    """Build kwargs for any ``openai-compatible`` profile from env."""
    base_url = os.environ.get("OPENAI_COMPAT_BASE_URL")
    api_key = os.environ.get("OPENAI_COMPAT_API_KEY") or os.environ.get(
        "OPENAI_API_KEY"
    )
    extra: dict[str, Any] = {}
    if base_url:
        extra["base_url"] = base_url
    if api_key:
        extra["api_key"] = api_key
    headers = _parse_extra_headers(os.environ.get("OPENAI_COMPAT_HEADERS"))
    if headers:
        extra["default_headers"] = headers
    return extra


def _build_profile_from_env(name: str) -> ModelProfile:
    """Materialize an openai-compatible profile from env, with name fallback."""
    base = _BUILTIN_PROFILES.get(name) or _BUILTIN_PROFILES["openai_compat"]
    if base.provider != "openai":
        return base
    # If the builtin profile itself uses openai, AND it carries the
    # openai-compatible tag, treat it as third-party. We tag by name.
    if name not in {"deepseek_chat", "openai_compat"}:
        return base
    extra = _openai_compat_extra()
    model_id = (
        os.environ.get("OPENAI_COMPAT_MODEL") if name == "openai_compat" else base.model_id
    )
    return ModelProfile(
        name=name,
        provider=base.provider,
        model_id=model_id or base.model_id,
        temperature=base.temperature,
        extra=extra,
    )


def _resolve_profile(profile_name: str) -> ModelProfile:
    """Resolve a profile name to a concrete ``ModelProfile``.

    Resolution order:
    1. If the name is registered in ``_BUILTIN_PROFILES`` AND env has
       ``OPENAI_COMPAT_BASE_URL`` set, build a fresh profile from env
       (only meaningful for ``openai-compatible`` builtins).
    2. Otherwise return the registered builtin as-is.
    """
    if profile_name not in _BUILTIN_PROFILES:
        raise KeyError(
            f"Unknown LLM profile: {profile_name!r}. "
            f"Known: {sorted(_BUILTIN_PROFILES)}"
        )
    base = _BUILTIN_PROFILES[profile_name]
    # Third-party profiles: openai provider key + OPENAI_COMPAT_BASE_URL set.
    if (
        base.provider == "openai"
        and profile_name in {"deepseek_chat", "openai_compat"}
        and os.environ.get("OPENAI_COMPAT_BASE_URL")
    ):
        return _build_profile_from_env(profile_name)
    return base


# ---------------------------------------------------------------------------
# Agent → profile mapping (Phase 3+)
# ---------------------------------------------------------------------------


# Per-agent LLM profile. Edit a profile name (or override via env
# ``DEEPDRAW_LLM_<AGENT>``) to switch providers without touching agent code.
_LLM_CONFIG: dict[str, dict[str, Any]] = {
    "spec_interpreter": {"profile": "gpt4o", "temperature": 0.0},
    "drawing_auditor": {"profile": "gpt4o", "temperature": 0.0},
    "bom_generator": {"profile": "gpt4o", "temperature": 0.0},
    "process_recommender": {"profile": "gpt4o", "temperature": 0.3},
    "chief_verifier": {"profile": "claude_opus_46", "temperature": 0.0},
}


def _agent_profile_name(agent_name: str) -> str:
    """Return effective profile name for ``agent_name``.

    Resolution order:
    1. ``DEEPDRAW_LLM_<AGENT>`` per-agent override
    2. ``DEEPDRAW_LLM_DEFAULT`` global override
    3. ``_LLM_CONFIG[agent_name]["profile"]`` builtin
    """
    if agent_name not in _LLM_CONFIG:
        raise KeyError(
            f"Unknown agent: {agent_name}. Known: {sorted(_LLM_CONFIG)}"
        )
    env_key = f"DEEPDRAW_LLM_{agent_name.upper()}"
    override = os.environ.get(env_key)
    if override:
        if override not in _BUILTIN_PROFILES:
            raise KeyError(
                f"{env_key}={override!r} is not a known profile. "
                f"Known: {sorted(_BUILTIN_PROFILES)}"
            )
        return override
    default = os.environ.get("DEEPDRAW_LLM_DEFAULT")
    if default:
        if default not in _BUILTIN_PROFILES:
            raise KeyError(
                f"DEEPDRAW_LLM_DEFAULT={default!r} is not a known profile. "
                f"Known: {sorted(_BUILTIN_PROFILES)}"
            )
        return default
    return _LLM_CONFIG[agent_name]["profile"]


def get_profile(agent_name: str) -> ModelProfile:
    """Return the resolved ``ModelProfile`` for an agent."""
    profile_name = _agent_profile_name(agent_name)
    profile = _resolve_profile(profile_name)
    cfg = _LLM_CONFIG[agent_name]
    if profile.temperature != cfg["temperature"]:
        # per-agent temperature overrides the builtin default
        profile = ModelProfile(
            name=profile.name,
            provider=profile.provider,
            model_id=profile.model_id,
            temperature=cfg["temperature"],
            extra=profile.extra,
        )
    return profile


# ---------------------------------------------------------------------------
# Public factory API
# ---------------------------------------------------------------------------


def get_llm(agent_name: str):
    """Return a configured chat model for ``agent_name``.

    Reads API keys/base_url from environment. For third-party OpenAI-compatible
    endpoints we bypass ``init_chat_model`` (which strips ``base_url`` in 1.x)
    and call ``ChatOpenAI`` directly with ``openai_api_base``.
    """
    profile = get_profile(agent_name)
    kwargs = profile.init_kwargs()
    extra = profile.extra

    if extra.get("base_url") and profile.provider == "openai":
        # Third-party OpenAI-compatible endpoint.
        try:
            from langchain_openai import ChatOpenAI  # type: ignore[import-not-found]
        except ImportError as e:
            raise RuntimeError(
                "Third-party OpenAI-compatible provider requires langchain-openai. "
                "Install with `uv pip install langchain-openai`."
            ) from e
        chat_kwargs: dict[str, Any] = {
            "model": profile.model_id,
            "temperature": profile.temperature,
            "openai_api_base": extra["base_url"],
        }
        if extra.get("api_key"):
            chat_kwargs["openai_api_key"] = extra["api_key"]
        if extra.get("default_headers"):
            chat_kwargs["default_headers"] = extra["default_headers"]
        return ChatOpenAI(**chat_kwargs)

    try:
        return init_chat_model(**kwargs)
    except ImportError as e:
        raise RuntimeError(
            f"Missing integration package for provider {profile.provider!r}: {e}. "
            f"Install with `uv pip install langchain-{profile.provider}` "
            f"(or 'langchain-openai' for openai-compatible)."
        ) from e


def get_structured_llm(agent_name: str, schema: type[BaseModel]):
    """Return a chat model with structured output bound to a Pydantic schema.

    Uses the agent's configured model + temperature; wraps with
    ``with_structured_output()``. Cannot be combined with ``bind_tools()``
    on the same model.
    """
    llm = get_llm(agent_name)
    return llm.with_structured_output(schema)


__all__ = [
    "ModelProfile",
    "_BUILTIN_PROFILES",
    "_LLM_CONFIG",
    "get_llm",
    "get_profile",
    "get_structured_llm",
]
