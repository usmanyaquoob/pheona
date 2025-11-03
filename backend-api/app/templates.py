# backend-api/app/templates.py
import json, os
from typing import Dict, Any, List
from .config import settings

class TemplateNotFound(Exception): ...
class PromptNotFound(Exception): ...

def _template_path(template_key: str) -> str:
    # e.g. "insurance/motor_trucking/inbound" → templates/insurance/motor_trucking/inbound.json
    return os.path.join(settings.PHEONA_TEMPLATES_DIR, f"{template_key}.json")

def load_template(template_key: str) -> Dict[str, Any]:
    path = _template_path(template_key)
    if not os.path.exists(path):
        raise TemplateNotFound(f"Template not found: {template_key} at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_prompt_text(path_from_template: str) -> str:
    # Resolve paths relative to repo root so templates can store "prompts/..../file.md"
    candidate = path_from_template
    if not os.path.isabs(candidate):
        candidate = os.path.join(settings.PHEONA_REPO_ROOT, path_from_template)
    if not os.path.exists(candidate):
        raise PromptNotFound(f"Prompt file not found: {candidate}")
    with open(candidate, "r", encoding="utf-8") as f:
        return f.read().strip()

def check_required(template: Dict[str, Any], payload: Dict[str, Any]) -> List[str]:
    req = template.get("required_fields", [])
    missing: List[str] = []
    for k in req:
        v = payload.get(k, None)
        if v is None:
            missing.append(k)
        elif isinstance(v, str) and not v.strip():
            missing.append(k)
        elif isinstance(v, list) and len(v) == 0:
            missing.append(k)
    return missing
