# frontend-streamlit/client/api.py
from __future__ import annotations
import os
import requests
import streamlit as st

# Streamlit Cloud → set in .streamlit/secrets.toml
BACKEND_BASE_URL = st.secrets.get("BACKEND_BASE_URL", os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000"))
BACKEND_API_KEY  = st.secrets.get("BACKEND_API_KEY",  os.getenv("BACKEND_API_KEY", ""))

def _headers() -> dict:
    hdrs = {"Content-Type": "application/json"}
    if BACKEND_API_KEY:
        hdrs["X-API-Key"] = BACKEND_API_KEY
    return hdrs

def is_backend_configured() -> bool:
    try:
        r = requests.get(f"{BACKEND_BASE_URL}/v1/health", timeout=6)
        return r.ok
    except Exception:
        return False

def preview_agent(payload: dict) -> dict:
    url = f"{BACKEND_BASE_URL}/v1/agent/preview"
    r = requests.post(url, json=payload, headers=_headers(), timeout=30)
    if not r.ok:
        raise RuntimeError(f"Server error '{r.status_code} {r.reason}' → {r.text}")
    return r.json()

def create_agent(payload: dict) -> dict:
    # default to provisioning a number in MVP
    body = dict(payload)
    body.setdefault("template_key", "insurance/motor_trucking/inbound")
    body.setdefault("provision_phone_number", True)

    url = f"{BACKEND_BASE_URL}/v1/agent/create"
    r = requests.post(url, json=body, headers=_headers(), timeout=60)
    if not r.ok:
        raise RuntimeError(f"Server error '{r.status_code} {r.reason}' → {r.text}")
    return r.json()
