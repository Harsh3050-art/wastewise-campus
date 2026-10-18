"""One place that talks to the LLM provider. Change providers here only."""
import base64
import os

import streamlit as st


class AIUnavailable(Exception):
    """Raised when the AI cannot be used (no key, network error, bad reply...)."""


def _secret(name, default=None):
    try:
        value = st.secrets.get(name)
    except Exception:
        value = None
    return value or os.environ.get(name) or default


def provider():
    p = _secret("AI_PROVIDER")
    if p:
        return str(p).lower()
    if _secret("ANTHROPIC_API_KEY"):
        return "anthropic"
    if _secret("GEMINI_API_KEY"):
        return "gemini"
    return "none"


def ai_configured():
    p = provider()
    if p == "anthropic":
        return bool(_secret("ANTHROPIC_API_KEY"))
    if p == "gemini":
        return bool(_secret("GEMINI_API_KEY"))
    return False


def generate(system, user_text, image_bytes=None, image_mime="image/jpeg", max_tokens=1200):
    """Return the model's text reply. Raises AIUnavailable on any problem."""
    p = provider()
    try:
        if p == "anthropic":
            return _anthropic(system, user_text, image_bytes, image_mime, max_tokens)
        if p == "gemini":
            return _gemini(system, user_text, image_bytes, image_mime, max_tokens)
    except AIUnavailable:
        raise
    except Exception as e:
        raise AIUnavailable(f"{type(e).__name__}: {e}") from e
    raise AIUnavailable("No AI key is configured" if p == "none" else f"Unknown AI_PROVIDER '{p}'")


def _anthropic(system, user_text, image_bytes, image_mime, max_tokens):
    key = _secret("ANTHROPIC_API_KEY")
    if not key:
        raise AIUnavailable("ANTHROPIC_API_KEY is missing")
    import anthropic

    client = anthropic.Anthropic(api_key=key, timeout=30.0)
    content = []
    if image_bytes:  # images work best before the text
        content.append({"type": "image", "source": {
            "type": "base64", "media_type": image_mime,
            "data": base64.b64encode(image_bytes).decode("ascii")}})
    content.append({"type": "text", "text": user_text})
    msg = client.messages.create(
        model=_secret("ANTHROPIC_MODEL", "claude-haiku-5-5"),
        max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": content}])
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


GEMINI_DEFAULT_MODELS = ["gemini-3.5-flash", "gemini-3-flash-preview", "gemini-2.5-flash"]
_gemini_state = {"model": None}  # remembers the first model that worked


def _gemini(system, user_text, image_bytes, image_mime, max_tokens):
    key = _secret("GEMINI_API_KEY")
    if not key:
        raise AIUnavailable("GEMINI_API_KEY is missing")
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key)
    parts = []
    if image_bytes:
        parts.append(types.Part.from_bytes(data=image_bytes, mime_type=image_mime))
    parts.append(user_text)
    config = types.GenerateContentConfig(system_instruction=system,
                                         response_mime_type="application/json")

    chosen = _secret("GEMINI_MODEL")
    models = [chosen] if chosen else ([_gemini_state["model"]] if _gemini_state["model"]
                                      else GEMINI_DEFAULT_MODELS)
    last = None
    for model in models:
        try:
            resp = client.models.generate_content(model=model, contents=parts, config=config)
            _gemini_state["model"] = model
            return resp.text or ""
        except Exception as e:
            last = e
            msg = str(e).lower()
            if "not_found" in msg or "not found" in msg or "404" in msg:
                continue  # try the next model name
            raise
    raise AIUnavailable(f"No Gemini model worked. Set GEMINI_MODEL in secrets.toml. Last error: {last}")