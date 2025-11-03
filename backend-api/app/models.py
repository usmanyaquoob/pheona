# backend-api/app/models.py
from pydantic import BaseModel, HttpUrl, Field, constr
from typing import List, Optional, Literal, Dict, Any

VoiceGender = Literal["male", "female"]

class AgentBuilderPayload(BaseModel):
    # Template selection
    template_key: constr(strip_whitespace=True, min_length=1) = "insurance/motor_trucking/inbound"
    industry: str = "insurance"
    subcategory: str = "motor_trucking"
    use_case: str = "inbound_lead_capture"

    # Core identity
    agent_name: constr(strip_whitespace=True, min_length=1)
    business_name: constr(strip_whitespace=True, min_length=1)
    website: Optional[HttpUrl] = None

    # Voice & behavior
    voice_gender: VoiceGender
    languages: List[str] = ["English"]
    timezone: Optional[str] = None
    transfer_number: Optional[str] = None

    # Freeform modifiers
    free_instructions: str = ""

    # Dynamic “information to collect” -> list of dicts: {field, label, required}
    info_to_collect: List[Dict[str, Any]] = Field(default_factory=list)

    # Optional US area code for phone provisioning
    area_code: Optional[constr(strip_whitespace=True, min_length=3, max_length=3)] = None

class MissingFieldReport(BaseModel):
    missing_fields: List[str] = Field(default_factory=list)

class PromptPreview(BaseModel):
    system_prompt: str
    first_message: str

class PreviewResponse(BaseModel):
    missing: MissingFieldReport
    preview: Optional[PromptPreview] = None

class CreateAgentRequest(AgentBuilderPayload):
    # MVP default: provision a free US number (subject to account limits)
    provision_phone_number: bool = True

class CreateAgentResponse(BaseModel):
    slug: str
    editToken: str
    assistantId: str
    phoneNumber: Optional[str] = None
    payload: AgentBuilderPayload
    system_prompt: str
    first_message: str

class SavedAgent(BaseModel):
    slug: str
    editToken: str
    assistantId: str
    phoneNumber: Optional[str]
    payload: AgentBuilderPayload
    system_prompt: str
    first_message: str

class LoadAgentResponse(SavedAgent):
    pass

class LoadAgentRequest(BaseModel):
    token: str
