from __future__ import annotations
import pandas as pd
import streamlit as st

DEFAULT_FIELDS = [
    {"field": "legal_name",   "label": "Legal Business Name", "required": True},
    {"field": "contact_name", "label": "Primary Contact Name", "required": True},
    {"field": "phone",        "label": "Phone",               "required": True},
    {"field": "email",        "label": "Email",               "required": True},
    {"field": "state",        "label": "Operating State",     "required": True},
    {"field": "units_count",  "label": "# Power Units",       "required": True},
    {"field": "radius_band",  "label": "Radius Band",         "required": True},
    {"field": "usdot",        "label": "USDOT (optional)",    "required": False},
]

def collect_list(key: str = "collect_df", initial_rows=None):
    """
    Renders a dynamic table (users can add/remove any number of rows) for 'Information to collect'.
    Uses st.data_editor with num_rows="dynamic".
    Returns a list of dicts with columns: field, label, required (bool).
    """
    if initial_rows is None:
        initial_rows = DEFAULT_FIELDS

    if key not in st.session_state:
        st.session_state[key] = pd.DataFrame(initial_rows)

    st.caption("Add or remove rows. Use short machine-friendly `field` names (snake_case).")
    edited_df = st.data_editor(
        st.session_state[key],
        num_rows="dynamic",
        width="stretch",  # new Streamlit API (replaces use_container_width)
        column_config={
            "field": {"help": "Unique key used in your CRM/payload (snake_case)."},
            "label": {"help": "How the agent will say/confirm the field."},
            "required": st.column_config.CheckboxColumn(
                "required", help="Must be captured before ending the call."
            ),
        },
        hide_index=True,
        key=f"{key}_editor",
    )
    # Persist for reruns
    st.session_state[key] = edited_df
    # Normalize to list[dict] (avoid silent downcasting warning)
    edited_df = edited_df.fillna("")
    edited_df = edited_df.infer_objects(copy=False)

    records = edited_df.to_dict(orient="records")

    # Deduplicate by field name (last one wins)
    seen = set()
    unique = []
    for r in records:
        if not r.get("field"):
            continue
        if r["field"] in seen:
            continue
        seen.add(r["field"])
        unique.append({
            "field": str(r["field"]).strip(),
            "label": str(r.get("label", "")).strip(),
            "required": bool(r.get("required")),
        })
    return unique
