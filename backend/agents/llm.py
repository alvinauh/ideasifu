"""LLM client wrapper for the IdeaSifu agents.

Uses OpenAI-compatible endpoints against Groq and Gemini. Every agent asks for
structured JSON and we parse it tolerantly.

Provider strategy
-----------------
* Non-web agents (Ideator, Cartographer, Director, refine): Groq (fast) →
  Gemini fallback.
* Web agents (Scout, Librarian): Groq → Gemini fallback. (No live web-search
  plugin available without OpenRouter; both providers use their training data.)
* Pro tier (Dojo): Gemini 2.5 Flash (primary, high quality) → Groq fallback.

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

GROQ_MODEL = os.environ.get("IDEASIFU_GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_FALLBACK_MODEL = os.environ.get("IDEASIFU_GROQ_FALLBACK_MODEL", "qwen/qwen3.6-27b")
# Gemini 2.0 Flash — used as pro-tier primary and general fallback.
GEMINI_MODEL = os.environ.get("IDEASIFU_GEMINI_MODEL", "gemini-2.0-flash")

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


def _gemini_client():
    key = os.environ.get("GEMINI_API_KEY")
    if OpenAI is None or not key:
        return None
    return OpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=key,
        timeout=120.0,
    )


_groq = _groq_client()
_gemini = _gemini_client()


def is_live() -> bool:
    return _groq is not None or _gemini is not None


def _providers(web: bool, pro: bool = False):
    """Ordered (client, model, label) chain to try for this call.

    Pro (Dojo) requests lead with Gemini 2.5 Flash then fall back to Groq.
    Web and non-web agents both lead with Groq then fall back to Gemini.
    """
    chain = []
    if pro:
        if _gemini is not None:
            chain.append((_gemini, GEMINI_MODEL, "gemini:pro"))
        if _groq is not None:
            chain.append((_groq, GROQ_MODEL, "groq"))
            chain.append((_groq, GROQ_FALLBACK_MODEL, "groq:fallback"))
    else:
        if _groq is not None:
            chain.append((_groq, GROQ_MODEL, "groq"))
            chain.append((_groq, GROQ_FALLBACK_MODEL, "groq:fallback"))
        if _gemini is not None:
            chain.append((_gemini, GEMINI_MODEL, "gemini"))
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
        raise LLMUnavailable("no GROQ_API_KEY or GEMINI_API_KEY configured")

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
