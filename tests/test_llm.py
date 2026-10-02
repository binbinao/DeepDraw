"""Unit tests for the LLM profile resolver in :mod:`deepdraw.llm`.

We don't make any real network calls. The goal is to lock down:

- Built-in profile catalog (no surprise model swaps).
- Env-driven third-party provider routing (``OPENAI_COMPAT_*``).
- Per-agent vs global override precedence.
- Third-party path instantiates ``ChatOpenAI`` with ``openai_api_base``.
- Anthropic path instantiates ``ChatAnthropic`` (no missing import).
- Errors when an unknown profile/agent is requested.
"""

from __future__ import annotations

import os

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from deepdraw.llm import (
    _BUILTIN_PROFILES,
    _LLM_CONFIG,
    ModelProfile,
    _agent_profile_name,
    _parse_extra_headers,
    get_llm,
    get_profile,
    get_structured_llm,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch):
    """Strip every DeepDraw / OpenAI-Compatible env var before each test."""
    for key in list(os.environ):
        if (
            key.startswith("DEEPDRAW_LLM_")
            or key.startswith("OPENAI_COMPAT_")
            or key == "OPENAI_API_KEY"
            or key == "ANTHROPIC_API_KEY"
        ):
            monkeypatch.delenv(key, raising=False)
    # Provide a fake key so ChatOpenAI doesn't blow up at validation time
    # unless a test deliberately strips it.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fixture")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-fixture")


# ---------------------------------------------------------------------------
# Profile catalog
# ---------------------------------------------------------------------------


class TestBuiltinProfiles:
    def test_builtin_profile_set_is_stable(self):
        # Lock the public surface. If you intentionally change a built-in,
        # update this test AND the .env.example comments in the same change.
        names = sorted(_BUILTIN_PROFILES)
        assert names == [
            "claude_opus_46",
            "claude_sonnet_45",
            "deepseek_chat",
            "gpt4o",
            "gpt4o_mini",
            "openai_compat",
        ]

    def test_openai_profiles_have_openai_provider(self):
        for name in ("gpt4o", "gpt4o_mini", "deepseek_chat", "openai_compat"):
            assert _BUILTIN_PROFILES[name].provider == "openai", name

    def test_anthropic_profiles_have_anthropic_provider(self):
        for name in ("claude_opus_46", "claude_sonnet_45"):
            assert _BUILTIN_PROFILES[name].provider == "anthropic", name


# ---------------------------------------------------------------------------
# Header parser
# ---------------------------------------------------------------------------


class TestParseExtraHeaders:
    def test_empty_returns_empty_dict(self):
        assert _parse_extra_headers(None) == {}
        assert _parse_extra_headers("") == {}

    def test_parses_key_value_lines(self):
        text = "HTTP-Referer: https://example.com\nX-Title: DeepDraw\n"
        assert _parse_extra_headers(text) == {
            "HTTP-Referer": "https://example.com",
            "X-Title": "DeepDraw",
        }

    def test_ignores_comments_and_blanks_and_malformed(self):
        text = "# comment\n\nX-Auth: abc\nno-colon-here\n"
        assert _parse_extra_headers(text) == {"X-Auth": "abc"}


# ---------------------------------------------------------------------------
# Per-agent profile resolution
# ---------------------------------------------------------------------------


class TestAgentProfileName:
    def test_unknown_agent_raises(self):
        with pytest.raises(KeyError, match="Unknown agent"):
            _agent_profile_name("not_an_agent")

    def test_unknown_profile_raises(self, monkeypatch):
        monkeypatch.setenv("DEEPDRAW_LLM_SPEC_INTERPRETER", "made_up_profile")
        with pytest.raises(KeyError, match="is not a known profile"):
            _agent_profile_name("spec_interpreter")

    def test_builtin_profile_used_when_no_env(self):
        assert _agent_profile_name("spec_interpreter") == "gpt4o"
        assert _agent_profile_name("chief_verifier") == "claude_opus_46"

    def test_per_agent_env_overrides_builtin(self, monkeypatch):
        monkeypatch.setenv("DEEPDRAW_LLM_SPEC_INTERPRETER", "claude_sonnet_45")
        assert _agent_profile_name("spec_interpreter") == "claude_sonnet_45"

    def test_global_default_overrides_all_agents(self, monkeypatch):
        monkeypatch.setenv("DEEPDRAW_LLM_DEFAULT", "gpt4o_mini")
        assert _agent_profile_name("spec_interpreter") == "gpt4o_mini"
        assert _agent_profile_name("chief_verifier") == "gpt4o_mini"

    def test_per_agent_beats_global_default(self, monkeypatch):
        monkeypatch.setenv("DEEPDRAW_LLM_DEFAULT", "gpt4o_mini")
        monkeypatch.setenv("DEEPDRAW_LLM_CHIEF_VERIFIER", "claude_opus_46")
        assert _agent_profile_name("chief_verifier") == "claude_opus_46"
        assert _agent_profile_name("spec_interpreter") == "gpt4o_mini"

    def test_global_default_validates_against_catalog(self, monkeypatch):
        monkeypatch.setenv("DEEPDRAW_LLM_DEFAULT", "not_a_real_profile")
        with pytest.raises(KeyError, match="is not a known profile"):
            _agent_profile_name("spec_interpreter")


# ---------------------------------------------------------------------------
# Profile → chat model instantiation
# ---------------------------------------------------------------------------


class TestGetLlM:
    def test_openai_profile_returns_chat_openai(self):
        # No env tweaks → uses builtin gpt4o. The OpenAI client will try to
        # authenticate, but we assert the class + model_name only.
        m = get_llm("spec_interpreter")
        assert isinstance(m, ChatOpenAI)
        assert m.model_name == "gpt-4o"

    def test_anthropic_profile_returns_chat_anthropic(self):
        m = get_llm("chief_verifier")
        assert isinstance(m, ChatAnthropic)
        # Don't pin the exact model id — providers rename.

    def test_third_party_profile_uses_base_url(self, monkeypatch):
        monkeypatch.setenv("OPENAI_COMPAT_BASE_URL", "https://api.deepseek.com")
        monkeypatch.setenv("OPENAI_COMPAT_API_KEY", "sk-fake")
        monkeypatch.setenv("DEEPDRAW_LLM_PROCESS_RECOMMENDER", "deepseek_chat")

        m = get_llm("process_recommender")
        assert isinstance(m, ChatOpenAI)
        assert m.openai_api_base == "https://api.deepseek.com"
        assert m.model_name == "deepseek-chat"

    def test_third_party_profile_picks_up_extra_headers(self, monkeypatch):
        monkeypatch.setenv("OPENAI_COMPAT_BASE_URL", "https://api.deepseek.com")
        monkeypatch.setenv("OPENAI_COMPAT_API_KEY", "sk-fake")
        monkeypatch.setenv(
            "OPENAI_COMPAT_HEADERS", "HTTP-Referer: https://example.com\nX-Title: DD"
        )
        monkeypatch.setenv("DEEPDRAW_LLM_PROCESS_RECOMMENDER", "deepseek_chat")

        m = get_llm("process_recommender")
        assert m.default_headers == {
            "HTTP-Referer": "https://example.com",
            "X-Title": "DD",
        }

    def test_openai_compat_profile_honors_model_override(self, monkeypatch):
        monkeypatch.setenv("OPENAI_COMPAT_BASE_URL", "https://api.example.com")
        monkeypatch.setenv("OPENAI_COMPAT_API_KEY", "sk-x")
        monkeypatch.setenv("OPENAI_COMPAT_MODEL", "custom-model-7")
        monkeypatch.setenv("DEEPDRAW_LLM_DEFAULT", "openai_compat")

        m = get_llm("bom_generator")
        assert m.model_name == "custom-model-7"
        assert m.openai_api_base == "https://api.example.com"

    def test_third_party_falls_back_to_openai_key(self, monkeypatch):
        monkeypatch.setenv("OPENAI_COMPAT_BASE_URL", "https://api.deepseek.com")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-shared")
        # no OPENAI_COMPAT_API_KEY → falls back to OPENAI_API_KEY
        monkeypatch.delenv("OPENAI_COMPAT_API_KEY", raising=False)
        monkeypatch.setenv("DEEPDRAW_LLM_DEFAULT", "openai_compat")

        m = get_llm("spec_interpreter")
        # ChatOpenAI wraps the key as SecretStr.
        assert m.openai_api_key.get_secret_value() == "sk-shared"

    def test_per_agent_temperature_overrides_builtin(self):
        p = get_profile("process_recommender")
        assert p.temperature == 0.3  # _LLM_CONFIG override, not 0.0 builtin

    def test_unknown_agent_raises(self):
        with pytest.raises(KeyError, match="Unknown agent"):
            get_llm("not_a_real_agent")

    def test_missing_integration_package_raises_runtimeerror(
        self, monkeypatch
    ):
        # Pretend the openai package isn't importable.
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "langchain_openai":
                raise ImportError("simulated missing package")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        monkeypatch.setenv("OPENAI_COMPAT_BASE_URL", "https://api.deepseek.com")
        monkeypatch.setenv("DEEPDRAW_LLM_DEFAULT", "openai_compat")
        with pytest.raises(RuntimeError, match="langchain-openai"):
            get_llm("spec_interpreter")


# ---------------------------------------------------------------------------
# Structured-output wrapper
# ---------------------------------------------------------------------------


class TestGetStructuredLlm:
    def test_returns_structured_openai_wrapper(self):
        from pydantic import BaseModel

        class S(BaseModel):
            x: int

        s = get_structured_llm("spec_interpreter", S)
        # with_structured_output returns RunnableSequence-like; just assert
        # it's wrapped (not a bare ChatModel).
        assert not isinstance(s, type(get_llm("spec_interpreter")))


# ---------------------------------------------------------------------------
# Backward compatibility shim
# ---------------------------------------------------------------------------


class TestLegacyConfig:
    def test_llm_config_uses_profile_key(self):
        # Make sure no agent still references the old ``model`` key — agents
        # that import ``_LLM_CONFIG`` would break otherwise.
        for agent, cfg in _LLM_CONFIG.items():
            assert "profile" in cfg, agent
            assert cfg["profile"] in _BUILTIN_PROFILES, agent
            assert "temperature" in cfg, agent


# ---------------------------------------------------------------------------
# ModelProfile value object
# ---------------------------------------------------------------------------


class TestModelProfile:
    def test_init_kwargs_compose_correctly(self):
        p = ModelProfile(
            name="x",
            provider="openai",
            model_id="foo",
            temperature=0.5,
            extra={"base_url": "https://x", "api_key": "k"},
        )
        kw = p.init_kwargs()
        assert kw == {
            "model": "openai:foo",
            "temperature": 0.5,
            "base_url": "https://x",
            "api_key": "k",
        }
