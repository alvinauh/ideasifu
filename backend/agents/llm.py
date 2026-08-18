"""LLM client wrapper for the IdeaSifu agents.

Uses OpenAI-compatible endpoints against Groq and OpenRouter (keys shared from
the kuasaprestij stack). Every agent asks for structured JSON and we parse it
tolerantly.

Provider strategy
-----------------
* Non-web agents (Ideator, Cartographer, Director, refine): Groq
  `llama-3.3-70b-versatile` (fast) → OpenRouter free Llama fallback.
* Web agents (Scout, Librarian): OpenRouter `:online` — the model gets live web
  search via OpenRouter's Exa-backed plugin. Groq's chat API can't search, so it
  is only a last-ditch no-web fallback. `:online` is billed to the OpenRouter
  account, so it is used ONLY for the two agents that genuinely need fresh sources.
* Pro tier (Dojo): DeepSeek V3 direct API (primary, no watermarking) →
  Gemini 2.5 Flash via OpenRouter (fallback) → free chain as last resort.

If no API keys are set (or the SDK isn't installed), `is_live()` returns False
and the orchestrator serves deterministic mock data instead — so the whole app
runs end-to-end with zero credentials.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Type, TypeVar

from pydantic import BaseModel

log = logging.getLogger("ideasifu.llm")

# Mirror kuasaprestij's proven free Llama-3.3-70B chain.
GROQ_MODEL = os.environ.get("IDEASIFU_GROQ_MODEL", "llama-3.3-70b-versatile")
# Free Groq fallback on a separate daily token quota — used when the 70B model
# hits its per-day token limit (429), so we stay live instead of dropping to mock.
GROQ_FALLBACK_MODEL = os.environ.get(
    "IDEASIFU_GROQ_FALLBACK_MODEL", "llama-3.1-8b-instant"
)
OPENROUTER_MODEL = os.environ.get(
    "IDEASIFU_OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"
)
# `:online` gives the model OpenRouter's web-search plugin (used by Scout/Librarian).
OPENROUTER_ONLINE_MODEL = os.environ.get(
    "IDEASIFU_OPENROUTER_ONLINE_MODEL", "meta-llama/llama-3.3-70b-instruct:online"
)
# Pro tier: DeepSeek V3 primary (no watermarking, ~$0.02/full generation),
# Gemini 2.5 Flash via OpenRouter as fallback if DeepSeek fails.
DEEPSEEK_PRO_MODEL = os.environ.get("IDEASIFU_PRO_MODEL", "deepseek-chat")
OPENROUTER_PRO_FALLBACK_MODEL = os.environ.get(
    "IDEASIFU_PRO_FALLBACK_MODEL", "google/gemini-2.5-flash"
)

T = TypeVar("T", bound=BaseModel)

try:
    from openai import OpenAI
except ImportError:  # SDK optional for mock-only runs
    OpenAI = None


class LLMUnavailable(RuntimeError):
    """Raised when no live LLM client is configured or every provider failed."""


def _groq_client():
    key = os.environ.get("GROQ_API_KEY")
    if OpenAI is None or not key:
        return None
    return OpenAI(base_url="https://api.groq.com/openai/v1", api_key=key, timeout=60.0)


def _openrouter_client():
    key = os.environ.get("OPENROUTER_API_KEY")
    if OpenAI is None or not key:
        return None
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=key,
        timeout=90.0,
        default_headers={"X-Title": "IdeaSifu"},
    )


def _deepseek_client():
    key = os.environ.get("DEEPSEEK_API_KEY")
    if OpenAI is None or not key:
        return None
    return OpenAI(
        base_url="https://api.deepseek.com/v1",
        api_key=key,
        timeout=120.0,
    )


_groq = _groq_client()
_openrouter = _openrouter_client()
_deepseek = _deepseek_client()


def is_live() -> bool:
    return _groq is not None or _openrouter is not None or _deepseek is not None


def _providers(web: bool, pro: bool = False):
    """Ordered (client, model, label) chain to try for this call.

    Pro requests lead with the paid model (OPENROUTER_PRO_MODEL) and fall
    through to the free chain if that fails. Web agents lead with OpenRouter
    `:online`; non-web agents lead with fast Groq.
    """
    chain = []
    if pro:
        if _deepseek is not None:
            chain.append((_deepseek, DEEPSEEK_PRO_MODEL, "deepseek:pro"))
        if _openrouter is not None:
            chain.append((_openrouter, OPENROUTER_PRO_FALLBACK_MODEL, "openrouter:pro-fallback"))
    if web:
        if _openrouter is not None:
            chain.append((_openrouter, OPENROUTER_ONLINE_MODEL, "openrouter:online"))
        if _groq is not None:  # no web search, but better than mock
            chain.append((_groq, GROQ_MODEL, "groq"))
            chain.append((_groq, GROQ_FALLBACK_MODEL, "groq:8b"))
        if _openrouter is not None:
            chain.append((_openrouter, OPENROUTER_MODEL, "openrouter"))
    else:
        if _groq is not None:
            chain.append((_groq, GROQ_MODEL, "groq"))
            chain.append((_groq, GROQ_FALLBACK_MODEL, "groq:8b"))
        if _openrouter is not None:
            chain.append((_openrouter, OPENROUTER_MODEL, "openrouter"))
    return chain


def _looks_like_schema(obj) -> bool:
    """True if a parsed object is a JSON *schema* rather than a data payload.

    Weaker models (e.g. Groq's 8B) sometimes echo the schema we hand them before
    the actual answer; grabbing that would fail validation on every required
    field. Skip it and take the next object instead."""
    return isinstance(obj, dict) and any(
        k in obj for k in ("$schema", "$defs", "properties")
    )


def _iter_json(text: str):
    """Yield each top-level JSON object/array found in `text`, left to right."""
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch not in "{[":
            i += 1
            continue
        close_ch = "}" if ch == "{" else "]"
        depth = 0
        in_str = False
        esc = False
        for j in range(i, n):
            c = text[j]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c == ch:
                    depth += 1
                elif c == close_ch:
                    depth -= 1
                    if depth == 0:
                        # strict=False tolerates raw control characters (literal
                        # newlines) inside string values — common when a model
                        # returns long multi-paragraph markdown in a JSON string.
                        try:
                            yield json.loads(text[i : j + 1], strict=False)
                        except json.JSONDecodeError:
                            pass
                        i = j + 1
                        break
        else:  # no matching close bracket — nothing more to find
            return


def _extract_json(text: str):
    """Pull the intended JSON object/array out of a model response, tolerating
    markdown fences, leading prose, and a leading schema echo."""
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)

    first = None
    for obj in _iter_json(text):
        if first is None:
            first = obj
        if not _looks_like_schema(obj):
            return obj  # the real payload
    if first is not None:
        return first  # only a schema-shaped object was found — let validation judge
    raise ValueError(f"No JSON found in model output: {text[:200]!r}")


def generate(
    system: str,
    user: str,
    model_cls: Type[T],
    *,
    web: bool = False,
    pro: bool = False,
    max_tokens: int = 8000,
) -> T:
    """Ask an LLM for a JSON object validated against `model_cls`.

    Tries each provider in the chain in turn; the first that returns parseable,
    schema-valid JSON wins. Raises LLMUnavailable if none succeed (the
    orchestrator then falls back to mock data).
    """
    chain = _providers(web, pro)
    if not chain:
        raise LLMUnavailable("no GROQ_API_KEY or OPENROUTER_API_KEY configured")

    schema = model_cls.model_json_schema()
    prompt = (
        f"{user}\n\n"
        "Respond with ONLY a single valid JSON object matching this JSON schema. "
        "No prose, no markdown code fences, no commentary.\n\n"
        f"JSON schema:\n{json.dumps(schema)}"
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    last_err: Exception | None = None
    for client, model, label in chain:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
            )
            text = resp.choices[0].message.content or ""
            return model_cls.model_validate(_extract_json(text))
        except Exception as exc:  # noqa: BLE001 — try the next provider
            last_err = exc
            log.warning("[llm] provider %s (%s) failed: %s", label, model, exc)
            continue

    raise LLMUnavailable(f"all providers failed; last error: {last_err}")
