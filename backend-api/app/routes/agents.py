# backend-api/app/routes/agents.py
from fastapi import APIRouter, Depends, HTTPException, Query
from ..auth import require_api_key
from ..models import (
    AgentBuilderPayload, PreviewResponse, MissingFieldReport,
    PromptPreview, CreateAgentRequest, CreateAgentResponse,
    LoadAgentResponse, SavedAgent
)
from ..templates import load_template, load_prompt_text, check_required
from ..prompt_specializer import specialize
from .. import vapi_client
from ..redis_client import r
from ..utils import slugify, short_id, new_edit_token
from ..config import settings
import json
import httpx
import logging

log = logging.getLogger("pheona.routes.agents")
router = APIRouter(prefix="/v1", tags=["agents"])

@router.get("/health")
async def health():
    return {"ok": True, "service": "pheona-backend", "env": settings.ENV}

@router.post("/agent/preview", response_model=PreviewResponse, dependencies=[Depends(require_api_key)])
async def agent_preview(payload: AgentBuilderPayload):
    template = load_template(payload.template_key)
    missing = check_required(template, payload.model_dump())
    if missing:
        return PreviewResponse(missing=MissingFieldReport(missing_fields=missing), preview=None)

    base_system = load_prompt_text(template["system_prompt_base_path"])
    meta_instr = None
    if template.get("prompt_specialization_instructions_path"):
        meta_instr = load_prompt_text(template["prompt_specialization_instructions_path"])

    base_first = f"Hi, this is {payload.agent_name} with {payload.business_name}. How can I help today?"
    system_prompt, first_message = specialize(base_system, base_first, payload.model_dump(), meta_instr)

    return PreviewResponse(
        missing=MissingFieldReport(missing_fields=[]),
        preview=PromptPreview(system_prompt=system_prompt, first_message=first_message)
    )

@router.post("/agent/create", response_model=CreateAgentResponse, dependencies=[Depends(require_api_key)])
async def agent_create(body: CreateAgentRequest):
    template = load_template(body.template_key)
    missing = check_required(template, body.model_dump())
    if missing:
        raise HTTPException(status_code=422, detail={"missing_fields": missing})

    base_system = load_prompt_text(template["system_prompt_base_path"])
    meta_instr = None
    if template.get("prompt_specialization_instructions_path"):
        meta_instr = load_prompt_text(template["prompt_specialization_instructions_path"])

    base_first = f"Hi, this is {body.agent_name} with {body.business_name}. How can I help today?"
    system_prompt, first_message = specialize(base_system, base_first, body.model_dump(), meta_instr)

    # Create Vapi assistant
    try:
        assistant = await vapi_client.create_assistant(
            name=body.agent_name,
            system_prompt=system_prompt,
            first_message=first_message,
            voice_gender=body.voice_gender,
            business_name=body.business_name,
            # If your Vapi org routes to Groq automatically, you can omit provider/model here.
            # model_provider="groq",
            # model_name=settings.GROQ_MODEL,
        )
    except httpx.HTTPStatusError as e:
        detail_txt = e.response.text if e.response is not None else str(e)
        log.error("Assistant create failed: %s", detail_txt)
        raise HTTPException(status_code=400, detail={"error": "vapi_assistant_create_failed", "upstream": detail_txt})

    assistant_id = assistant.get("id")
    if not assistant_id:
        raise HTTPException(status_code=502, detail="Vapi assistant creation failed (no id in response)")

    phone_number = None
    if body.provision_phone_number:
        try:
            pn = await vapi_client.create_phone_number(
                assistant_id=assistant_id,
                label=f"{body.agent_name} Line",
            )
            # Response shape includes "number" for VapiPhoneNumber objects.
            phone_number = pn.get("number") or pn.get("e164") or pn.get("name")
        except httpx.HTTPStatusError as e:
            detail_txt = e.response.text if e.response is not None else str(e)
            log.error("Phone provisioning failed: %s", detail_txt)
            # Soft-fail: keep building the agent record; phone can be added later.
            phone_number = None

    slug = f"{slugify(body.agent_name)}-{short_id()}"
    edit_token = new_edit_token()

    # Persist to Redis
    r.hset(f"agent:{slug}", mapping={
        "assistantId": assistant_id,
        "phoneNumber": phone_number or "",
        "payload": json.dumps(body.model_dump()),
        "system_prompt": system_prompt,
        "first_message": first_message,
        "editToken": edit_token,
    })
    r.set(f"agent:by_token:{edit_token}", slug)

    return CreateAgentResponse(
        slug=slug,
        editToken=edit_token,
        assistantId=assistant_id,
        phoneNumber=phone_number,
        payload=body,
        system_prompt=system_prompt,
        first_message=first_message,
    )

@router.get("/agent/{slug}", response_model=LoadAgentResponse, dependencies=[Depends(require_api_key)])
async def load_agent(slug: str, token: str = Query(..., description="edit token")):
    data = r.hgetall(f"agent:{slug}")
    if not data:
        raise HTTPException(status_code=404, detail="Not found")
    if data.get("editToken") != token:
        raise HTTPException(status_code=403, detail="Invalid token")

    payload = json.loads(data["payload"])
    obj = SavedAgent(
        slug=slug,
        editToken=data["editToken"],
        assistantId=data["assistantId"],
        phoneNumber=data.get("phoneNumber") or None,
        payload=payload,
        system_prompt=data["system_prompt"],
        first_message=data["first_message"]
    )
    return LoadAgentResponse(**obj.model_dump())
