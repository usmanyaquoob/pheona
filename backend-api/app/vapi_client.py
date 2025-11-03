# backend-api/app/vapi_client.py
from __future__ import annotations

import logging
from typing import Optional, Dict, Any

import httpx
from .config import settings

log = logging.getLogger("pheona.vapi")

# Vapi curated voice IDs are case-sensitive. Use one of:
# Elliot, Kylie, Rohan, Lily, Savannah, Hana, Neha, Cole, Harry, Paige, Spencer
# (See error enum you received.)
def _pick_vapi_voice(voice_gender: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Map 'male'/'female'/'auto' to Vapi voices.
    If 'auto' or None: omit voice (Platform default will be used).
    """
    if not voice_gender:
        return None
    g = voice_gender.lower()
    if g == "female":
        return {"provider": "vapi", "voiceId": "Hana"}
    if g == "male":
        return {"provider": "vapi", "voiceId": "Harry"}
    return None  # auto

def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.VAPI_API_KEY}",
        "Content-Type": "application/json",
    }

async def create_assistant(
    *,
    name: str,
    system_prompt: str,
    first_message: str,
    voice_gender: Optional[str] = None,
    business_name: Optional[str] = None,
    model_provider: Optional[str] = None,
    model_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a Vapi Assistant.

    Minimal shape (stable as of Nov 2025):
      - name: string
      - firstMessage: string
      - model: { provider, model, messages: [{role:'system', content: ...}] }
      - voice (optional): { provider:'vapi', voiceId:'Hana'|'Harry'|... }
    """
    provider = (model_provider or "openai").strip()
    model = (model_name or "gpt-4o-mini").strip()

    payload: Dict[str, Any] = {
        "name": name,
        "firstMessage": first_message,
        "model": {
            "provider": provider,
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt}
            ],
        },
    }
    voice = _pick_vapi_voice(voice_gender)
    if voice:
        payload["voice"] = voice

    async with httpx.AsyncClient(base_url=settings.VAPI_BASE_URL, timeout=30.0) as client:
        res = await client.post("/assistant", headers=_headers(), json=payload)
        if res.is_error:
            log.error("Vapi /assistant error %s: %s", res.status_code, res.text)
            res.raise_for_status()
        return res.json()

async def create_phone_number(
    *,
    assistant_id: str,
    label: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Provision a *Vapi-provided* phone number and attach to assistant.
    IMPORTANT: Endpoint is /phone-number (singular). Do NOT send areaCode —
    it's not supported for Vapi-provided numbers and will 400.
    """
    body: Dict[str, Any] = {
        "provider": "vapi",
        "assistantId": assistant_id,
    }
    if label:
        body["name"] = label

    async with httpx.AsyncClient(base_url=settings.VAPI_BASE_URL, timeout=30.0) as client:
        res = await client.post("/phone-number", headers=_headers(), json=body)
        if res.is_error:
            log.error("Vapi phone number create error %s: %s", res.status_code, res.text)
            res.raise_for_status()
        return res.json()
