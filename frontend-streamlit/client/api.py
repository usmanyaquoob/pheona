from __future__ import annotations
import os
from typing import Any, Dict, Optional
import httpx

BACKEND_URL = os.getenv("PHEONA_BACKEND_URL", "").rstrip("/")
API_KEY = os.getenv("PHEONA_API_KEY", "")

def _headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    return headers

def is_backend_configured() -> bool:
    return bool(BACKEND_URL)

def preview_agent(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calls POST /v1/agent/preview on your backend.
    Returns: {"missing":[...], "previewPrompt":"..."} or a mock response if backend not set.
    """
    if not BACKEND_URL:
        # Demo-mode fallback so the UI still works without backend wired yet.
        return {
            "missing": [],
            "previewPrompt": f"[DEMO] Previewing prompt for agent '{payload.get('agent_name')}' at '{payload.get('business_name')}'."
        }

    url = f"{BACKEND_URL}/v1/agent/preview"
    with httpx.Client(timeout=30) as client:
        r = client.post(url, headers=_headers(), json=payload)
        r.raise_for_status()
        return r.json()

def create_agent(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calls POST /v1/agent/create on your backend.
    Returns: {"slug":"...", "editToken":"...", "assistantId":"...", "phoneNumber":"..."} or a mock.
    """
    if not BACKEND_URL:
        # Demo-mode fallback so you can click through end-to-end today.
        return {
            "slug": "demo-motor-trucking-inbound",
            "editToken": "demo-token",
            "assistantId": "asst_demo_123",
            "phoneNumber": "+1 (555) 010-2025"
        }

    url = f"{BACKEND_URL}/v1/agent/create"
    with httpx.Client(timeout=60) as client:
        r = client.post(url, headers=_headers(), json=payload)
        r.raise_for_status()
        return r.json()
