from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional, Dict, Any, List

import httpx
from .config import settings

log = logging.getLogger("pheona.vapi")


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.VAPI_API_KEY}",
        "Content-Type": "application/json",
    }


# ---------------- Assistants ----------------

async def create_assistant(
    *,
    name: str,
    system_prompt: str,
    first_message: str,
    voice_gender: Optional[str] = None,   # unused: Vapi defaults are fine
    business_name: Optional[str] = None,  # only for specialization; not sent
    model_provider: Optional[str] = None, # leave None to use Vapi default
    model_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    POST /assistant
    Body includes name, firstMessage and model (provider/model/messages).
    """
    provider = (model_provider or "openai").strip()
    model = (model_name or "gpt-4o-mini").strip()

    payload: Dict[str, Any] = {
        "name": name,
        "firstMessage": first_message,
        "model": {
            "provider": provider,
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}],
        },
    }

    async with httpx.AsyncClient(base_url=settings.VAPI_BASE_URL, timeout=30.0) as client:
        res = await client.post("/assistant", headers=_headers(), json=payload)
        if res.is_error:
            log.error("Vapi /assistant error %s: %s", res.status_code, res.text)
            res.raise_for_status()
        return res.json()


# ---------------- Phone Numbers ----------------
# API ref:
#   POST  /phone-number    → create (free Vapi number supported)  :contentReference[oaicite:0]{index=0}
#   GET   /phone-number/:id → fetch details incl. E.164 "number"  :contentReference[oaicite:1]{index=1}
#   DEL   /phone-number/:id → delete (cleanup on timeout)          :contentReference[oaicite:2]{index=2}

_HINT_CODE_RE = re.compile(r"\b(\d{3})\b")


def _parse_suggested_area_codes(msg: str) -> List[str]:
    """Extracts 3-digit codes from messages like: 'Hint: Try one of 518, 510, 904.'"""
    return list(dict.fromkeys(_HINT_CODE_RE.findall(msg or "")))  # preserve order & de-dupe


async def _post_create_number(payload: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient(base_url=settings.VAPI_BASE_URL, timeout=30.0) as client:
        res = await client.post("/phone-number", headers=_headers(), json=payload)
        if res.is_error:
            log.error("Vapi phone number create error %s: %s", res.status_code, res.text)
            res.raise_for_status()
        return res.json()


async def _get_phone_number(phone_number_id: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(base_url=settings.VAPI_BASE_URL, timeout=30.0) as client:
        res = await client.get(f"/phone-number/{phone_number_id}", headers=_headers())
        if res.is_error:
            log.error("Vapi GET /phone-number/%s error %s: %s", phone_number_id, res.status_code, res.text)
            res.raise_for_status()
        return res.json()


async def _delete_phone_number(phone_number_id: str) -> None:
    async with httpx.AsyncClient(base_url=settings.VAPI_BASE_URL, timeout=30.0) as client:
        res = await client.delete(f"/phone-number/{phone_number_id}", headers=_headers())
        if res.is_error:
            log.error("Vapi DELETE /phone-number/%s error %s: %s", phone_number_id, res.status_code, res.text)
            res.raise_for_status()


async def create_phone_number(
    assistant_id: str,
    label: Optional[str] = None,
    *,
    # start with a few good bets; we’ll append hints from API responses dynamically
    seed_area_codes: Optional[List[str]] = None,
    poll_interval: float = 10.0,   # Vapi can take up to ~2 minutes to be routable
    poll_timeout: float = 180.0    # poll up to 3 minutes for E.164 assignment
) -> Dict[str, Any]:
    """
    Provision a *free* Vapi-managed number and attach it to the assistant.

    Body (Vapi provider):
      {
        "provider": "vapi",
        "assistantId": "<uuid>",
        "name": "...",                       # optional
        "numberDesiredAreaCode": "510"       # optional, but we’ll use + retry with hints
      }

    Strategy:
      1) Try a list of area codes (includes hinted codes from API errors).
      2) As soon as creation returns an `id`, poll GET /phone-number/{id}
         until the E.164 number appears (or timeout).
      3) If we time out without ever getting a number, delete the stub entry.
    """
    base: Dict[str, Any] = {
        "provider": "vapi",
        "assistantId": assistant_id,
    }
    if label:
        base["name"] = label

    # Build retry list: seed → (later) hints from API responses
    attempts: List[str] = list(seed_area_codes or ["510", "518", "904", "509", "415", "407"])
    created: Optional[Dict[str, Any]] = None
    last_exc: Optional[httpx.HTTPStatusError] = None

    # Try each area code (Vapi sometimes rejects particular codes; it responds with suggested ones)
    for code in attempts:
        try:
            payload = {**base, "numberDesiredAreaCode": code}
            created = await _post_create_number(payload)
            log.info("Vapi number created with area code %s; id=%s", code, created.get("id"))
            break
        except httpx.HTTPStatusError as e:
            body = e.response.text if e.response is not None else ""
            # If API hints new codes, append them to the attempts list
            for hint in _parse_suggested_area_codes(body):
                if hint not in attempts:
                    attempts.append(hint)
            last_exc = e
            continue

    if not created:
        # Exhausted all attempts
        raise last_exc or RuntimeError("Unable to create a Vapi number")

    phone_id = created.get("id")
    if not phone_id:
        # Defensive: return whatever we got; caller may re-fetch via the list endpoint
        return created

    # Poll for the E.164 number to show up
    start = asyncio.get_event_loop().time()
    while (asyncio.get_event_loop().time() - start) < poll_timeout:
        pn = await _get_phone_number(phone_id)
        e164 = pn.get("number") or pn.get("e164") or pn.get("phone")
        if isinstance(e164, str) and e164.strip():
            return pn
        await asyncio.sleep(poll_interval)

    # If we never saw a number, delete the dangling record to keep the org clean
    try:
        await _delete_phone_number(phone_id)
        log.warning("Deleted unprovisioned Vapi number id=%s after timeout", phone_id)
    except Exception as e:
        log.error("Failed to delete unprovisioned number id=%s: %s", phone_id, e)
    return created  # best-effort: return what we have
