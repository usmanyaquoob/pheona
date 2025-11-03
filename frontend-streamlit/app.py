from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd
import streamlit as st
from pydantic import BaseModel, Field, HttpUrl, ValidationError
from dotenv import load_dotenv

from client.api import preview_agent, create_agent, is_backend_configured
from components.collect_list import collect_list

# Load local .env if present
load_dotenv()

# ---------- Config ----------
st.set_page_config(page_title="Pheona – Build your Voice Agent", page_icon="🎙️", layout="centered")

TEMPLATES_DIR = Path(os.getenv("PHEONA_TEMPLATES_DIR", Path(__file__).resolve().parents[1] / "templates"))
MOTOR_TRUCKING_TEMPLATE = TEMPLATES_DIR / "insurance/motor_trucking/inbound.json"

# ---------- Models ----------
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

# ---------- UI ----------
st.title("Pheona")
st.write("Spin up a production-grade **inbound** voice agent for **Motor Trucking Insurance** in minutes.")

with st.sidebar:
    st.markdown("#### Build status")
    st.write("Backend configured:", "✅" if is_backend_configured() else "❌")
    st.write("Template:", f"`{MOTOR_TRUCKING_TEMPLATE.name}`")
    st.divider()
    st.markdown("**Tips**")
    st.caption("You can add any number of fields in *Information to collect*. The agent will keep asking until all required items are captured.")

tpl = load_template()

# Step 1: identity
section_header("1) Identity")
col1, col2 = st.columns(2)
agent_name = col1.text_input("Agent name", placeholder="e.g., Alex", max_chars=40)
business_name = col2.text_input("Business name", placeholder="e.g., Anvil Insurance", max_chars=80)
website = st.text_input("Website (optional)", placeholder="https://example.com")

# voice & language
section_header("2) Voice & Language")
voice_gender = st.radio("Voice gender", options=["Female", "Male"], index=0, horizontal=True).lower()
languages = st.multiselect("Languages", options=["English", "Spanish"], default=["English"])
timezone = st.selectbox("Timezone", options=["US/Eastern", "US/Central", "US/Mountain", "US/Pacific", "UTC"], index=0)
transfer_number = st.text_input("Transfer to human (optional)", placeholder="+1 555 123 4567")

# info to collect (dynamic table)
section_header("3) Information to collect", "Add as many rows as you need; mark must-have items as required.")
info_to_collect = collect_list(key="collect_df")

# freeform instructions to shape behavior
section_header("4) Additional instructions", "Anything else you want the agent to say or do.")
free_instructions = st.text_area(
    "Instructions",
    placeholder=(
        "Examples:\n"
        "- We only write in TX & FL, Mon–Fri 9–5.\n"
        "- Ask for renewal date; if within 60 days, escalate to human.\n"
        "- Never quote prices on the call; just collect data and promise a follow-up."
    ),
    height=160
)

# Preview + Build
section_header("5) Build", "Preview the specialized prompt first, then create the live agent & phone number.")
colp, colb = st.columns([1,1])

def gather_payload() -> Dict[str, Any]:
    return AgentBuilderPayload(
        agent_name=agent_name.strip(),
        business_name=business_name.strip(),
        website=website.strip() if website else None,
        voice_gender=voice_gender,
        languages=languages or ["English"],
        timezone=timezone,
        transfer_number=transfer_number.strip() if transfer_number else None,
        free_instructions=free_instructions.strip(),
        info_to_collect=info_to_collect,
    ).model_dump()

def validate_can_submit() -> List[str]:
    errs = []
    if not agent_name:
        errs.append("Agent name is required.")
    if not business_name:
        errs.append("Business name is required.")
    if not info_to_collect:
        errs.append("Please add at least one item to collect.")
    return errs

with colp:
    if st.button("🔎 Preview prompt", width="stretch"):
        errs = validate_can_submit()
        if errs:
            st.error("\n".join(errs))
        else:
            try:
                payload = gather_payload()
                resp = preview_agent(payload)
                # Backend shape: {"missing":{"missing_fields":[...]}, "preview":{"system_prompt":"...", "first_message":"..."}}
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
                st.write(f"**Phone number:** {resp.get('phoneNumber')}")
                st.info("Save this edit link to update later (no login needed):")
                st.code(f"/edit/{resp.get('slug')}?token={resp.get('editToken')}")
            except ValidationError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Create failed: {e}")

# Context block (template peek)
with st.expander("Template defaults (read-only)"):
    st.json(tpl)
