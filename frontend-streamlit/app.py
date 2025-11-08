from __future__ import annotations
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd
import streamlit as st
from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv

from client.api import preview_agent, create_agent, is_backend_configured, load_agent
from components.collect_list import collect_list

load_dotenv()

st.set_page_config(page_title="Pheona – Build your Voice Agent", page_icon="🎙️", layout="centered")

TEMPLATES_DIR = Path(os.getenv("PHEONA_TEMPLATES_DIR", Path(__file__).resolve().parents[1] / "templates"))
MOTOR_TRUCKING_TEMPLATE = TEMPLATES_DIR / "insurance/motor_trucking/inbound.json"

class AgentBuilderPayload(BaseModel):
    industry: str = "insurance"
    subcategory: str = "motor_trucking"
    use_case: str = "inbound_lead_capture"
    agent_name: str
    business_name: str
    website: str | None = None
    voice_gender: str = Field(pattern="^(male|female)$")
    languages: List[str] = ["English"]
    timezone: str | None = None
    transfer_number: str | None = None
    free_instructions: str = ""
    info_to_collect: List[Dict[str, Any]]
    template_key: str = "insurance/motor_trucking/inbound"

def load_template() -> Dict[str, Any]:
    with open(MOTOR_TRUCKING_TEMPLATE, "r", encoding="utf-8") as f:
        return json.load(f)

def section_header(title: str, caption: str | None = None):
    st.subheader(title)
    if caption:
        st.caption(caption)

# ---------- Sidebar: Build status & Load saved agent ----------
with st.sidebar:
    st.markdown("#### Build status")
    st.write("Backend configured:", "✅" if is_backend_configured() else "❌")
    st.write("Template:", f"`{MOTOR_TRUCKING_TEMPLATE.name}`")
    st.divider()
    st.markdown("**Load saved agent**")
    default_edit = st.text_input("Paste edit link (or leave blank)", placeholder="/edit/<slug>?token=<token>")
    colL, colR = st.columns(2)
    slug_in = colL.text_input("Slug", placeholder="alex-xyz12")
    token_in = colR.text_input("Token", type="password", placeholder="edit token")
    if st.button("Load", use_container_width=True):
        try:
            if default_edit and "?token=" in default_edit:
                path, query = default_edit.split("?token=", 1)
                slug_in = path.rstrip("/").split("/")[-1]
                token_in = query
            if not (slug_in and token_in):
                st.error("Provide either the edit link or slug + token.")
            else:
                data = load_agent(slug_in, token_in)
                saved = data.get("payload", {})
                st.session_state["agent_name"] = saved.get("agent_name", "")
                st.session_state["business_name"] = saved.get("business_name", "")
                st.session_state["website"] = saved.get("website", "")
                st.session_state["voice_gender"] = saved.get("voice_gender", "female")
                st.session_state["languages"] = saved.get("languages", ["English"])
                st.session_state["timezone"] = saved.get("timezone", "US/Eastern")
                st.session_state["transfer_number"] = saved.get("transfer_number", "")
                st.session_state["free_instructions"] = saved.get("free_instructions", "")
                if saved.get("info_to_collect"):
                    st.session_state["collect_df"] = pd.DataFrame(saved["info_to_collect"])
                st.session_state["last_slug"] = data.get("slug")
                st.session_state["last_token"] = data.get("editToken")
                st.session_state["last_phone"] = data.get("phoneNumber")
                st.success("Loaded. Prefilled the builder.")
                st.rerun()
        except Exception as e:
            st.error(f"Load failed: {e}")

tpl = load_template()

# ---------- Controlled defaults ----------
st.session_state.setdefault("agent_name", "")
st.session_state.setdefault("business_name", "")
st.session_state.setdefault("website", "")
st.session_state.setdefault("voice_gender", "female")
st.session_state.setdefault("languages", ["English"])
st.session_state.setdefault("timezone", "US/Eastern")
st.session_state.setdefault("transfer_number", "")
st.session_state.setdefault("free_instructions", "")
st.session_state.setdefault("last_slug", "")
st.session_state.setdefault("last_token", "")
st.session_state.setdefault("last_phone", "")

# ---------- UI ----------
st.title("Pheona")
st.write("Spin up a production-grade **inbound** voice agent for **Motor Trucking Insurance** in minutes.")

section_header("1) Identity")
col1, col2 = st.columns(2)
col1.text_input("Agent name", max_chars=40, key="agent_name", placeholder="e.g., Alex")
col2.text_input("Business name", max_chars=80, key="business_name", placeholder="e.g., Amsys Insurance")
st.text_input("Website (optional)", key="website", placeholder="https://example.com")

section_header("2) Voice & Language")
voice_choice = st.radio(
    "Voice gender",
    options=["Female", "Male"],
    index=0 if st.session_state["voice_gender"] == "female" else 1,
    horizontal=True,
)
st.session_state["voice_gender"] = voice_choice.lower()
st.multiselect("Languages", options=["English", "Spanish"], default=st.session_state["languages"], key="languages")
st.selectbox(
    "Timezone",
    options=["US/Eastern", "US/Central", "US/Mountain", "US/Pacific", "UTC"],
    index=["US/Eastern", "US/Central", "US/Mountain", "US/Pacific", "UTC"].index(st.session_state["timezone"]),
    key="timezone",
)
st.text_input("Transfer to human (optional)", key="transfer_number", placeholder="+1 555 123 4567")

section_header("3) Information to collect", "Add as many rows as you need; mark must-have items as required.")
info_to_collect = collect_list(key="collect_df")

section_header("4) Additional instructions", "Anything else you want the agent to say or do.")
st.text_area("Instructions", key="free_instructions", height=160, placeholder="E.g. We only write in TX & FL, Mon–Fri 9–5. …")

section_header("5) Build", "Preview the specialized prompt first, then create the live agent & phone number.")
colp, colb = st.columns([1, 1])

def gather_payload() -> Dict[str, Any]:
    return AgentBuilderPayload(
        agent_name=st.session_state["agent_name"].strip(),
        business_name=st.session_state["business_name"].strip(),
        website=st.session_state["website"].strip() or None,
        voice_gender=st.session_state["voice_gender"],
        languages=st.session_state["languages"] or ["English"],
        timezone=st.session_state["timezone"],
        transfer_number=(st.session_state["transfer_number"].strip() or None),
        free_instructions=st.session_state["free_instructions"].strip(),
        info_to_collect=info_to_collect,
    ).model_dump()

def validate_can_submit() -> List[str]:
    errs = []
    if not st.session_state["agent_name"]:
        errs.append("Agent name is required.")
    if not st.session_state["business_name"]:
        errs.append("Business name is required.")
    if not info_to_collect:
        errs.append("Please add at least one item to collect.")
    return errs

def activation_countdown(seconds: int = 120):
    # Visual countdown so users know the number will be callable shortly
    timer = st.empty()
    bar = st.progress(0)
    for remaining in range(seconds, -1, -1):
        m, s = divmod(remaining, 60)
        timer.info(f"Activating phone number… {m:02d}:{s:02d}")
        done = int(((seconds - remaining) / max(seconds, 1)) * 100)
        bar.progress(done)
        time.sleep(1)
    timer.success("Number should be active now. Try calling!")
    bar.empty()

with colp:
    if st.button("🔎 Preview prompt", width="stretch"):
        errs = validate_can_submit()
        if errs:
            st.error("\n".join(errs))
        else:
            try:
                payload = gather_payload()
                resp = preview_agent(payload)
                missing_fields = (resp or {}).get("missing", {}).get("missing_fields", [])
                if missing_fields:
                    st.warning(f"Missing required inputs: {', '.join(missing_fields)}")
                else:
                    st.success("Preview ready.")
                    with st.expander("Show generated preview prompt"):
                        st.code((resp.get("preview") or {}).get("system_prompt", ""), language="markdown")
            except ValidationError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Preview failed: {e}")

with colb:
    if st.button("🚀 Build my agent", type="primary", width="stretch"):
        errs = validate_can_submit()
        if errs:
            st.error("\n".join(errs))
        else:
            try:
                payload = gather_payload()
                resp = create_agent(payload)
                st.success("Your agent is live!")
                st.write(f"**Assistant ID:** `{resp.get('assistantId')}`")

                st.session_state["last_slug"] = resp.get("slug") or ""
                st.session_state["last_token"] = resp.get("editToken") or ""
                st.session_state["last_phone"] = (resp.get("phoneNumber") or "").strip()

                phone_placeholder = st.empty()
                phone_label = st.session_state["last_phone"] or "provisioning…"
                phone_placeholder.write(f"**Phone number:** {phone_label}")

                # Show the activation countdown *after* we have any number text
                if st.session_state["last_phone"]:
                    activation_countdown(120)

                if st.button("🔁 Refresh phone number"):
                    try:
                        if st.session_state["last_slug"] and st.session_state["last_token"]:
                            refreshed = load_agent(st.session_state["last_slug"], st.session_state["last_token"])
                            st.session_state["last_phone"] = refreshed.get("phoneNumber") or st.session_state["last_phone"]
                            phone_placeholder.write(f"**Phone number:** {st.session_state['last_phone'] or 'provisioning…'}")
                        else:
                            st.warning("No saved agent in this session to refresh.")
                    except Exception as e:
                        st.error(f"Refresh failed: {e}")

                st.info("Save this edit link to update later (no login needed):")
                st.code(f"/edit/{resp.get('slug')}?token={resp.get('editToken')}")
            except ValidationError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Create failed: {e}")

with st.expander("Template defaults (read-only)"):
    st.json(load_template())
