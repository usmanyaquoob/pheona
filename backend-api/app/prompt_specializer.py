# backend-api/app/prompt_specializer.py
from typing import Dict, Any, Tuple, Optional
from groq import Groq
from .config import settings

"""
Use Groq Structured Outputs when the model supports JSON Schema.
If not, fall back to JSON Object mode, which enforces valid JSON syntax.

Docs:
- Structured Outputs & supported models: https://console.groq.com/docs/structured-outputs
- API reference (response_format json_schema / json_object): https://console.groq.com/docs/api-reference
"""

client = Groq(api_key=settings.GROQ_API_KEY)

# Known models that support response_format={"type":"json_schema"} per Groq docs.
SUPPORTED_JSON_SCHEMA_MODELS = {
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-safeguard-20b",
    "moonshotai/kimi-k2-instruct-0905",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "meta-llama/llama-4-scout-17b-16e-instruct",
}

def specialize(
    base_system_prompt: str,
    base_first_message: str,
    inputs: Dict[str, Any],
    meta_instructions: Optional[str] = None
) -> Tuple[str, str]:
    model = settings.GROQ_MODEL
    use_schema = model in SUPPORTED_JSON_SCHEMA_MODELS

    # Common meta
    meta = meta_instructions or "Return STRICT JSON for the required keys."

    # Build the meta-prompt (control prompt engineering)
    meta_prompt = f"""
{meta}

### Base system prompt:
{base_system_prompt}

### Base first message:
{base_first_message}

### Agent inputs (JSON):
{inputs}

Return JSON with keys: system_prompt, first_message.
"""

    messages = [
        {"role": "system", "content": "You return only valid JSON for the requested keys."},
        {"role": "user", "content": meta_prompt},
    ]

    if use_schema:
        # Full schema enforcement
        schema = {
            "name": "pheona_prompt",
            "schema": {
                "type": "object",
                "properties": {
                    "system_prompt": {"type": "string"},
                    "first_message": {"type": "string"}
                },
                "required": ["system_prompt", "first_message"],
                "additionalProperties": False
            },
            "strict": True,
        }
        resp = client.chat.completions.create(
            model=model,
            response_format={"type": "json_schema", "json_schema": schema},
            messages=messages,
            temperature=0.3,
        )
    else:
        # Fallback: JSON Object mode (valid JSON syntax, no schema guarantee)
        # Add explicit instruction to output *only* the two keys we need.
        messages[0]["content"] = (
            "You MUST return only a JSON object with keys: system_prompt and first_message. "
            "Do not include code fences or extra text."
        )
        resp = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=messages,
            temperature=0.3,
        )

    content = resp.choices[0].message.content
    import json as _json
    obj = _json.loads(content)
    # Minimal sanity fallback, in case a model adds extra keys.
    system_prompt = obj.get("system_prompt") or ""
    first_message = obj.get("first_message") or ""
    return system_prompt, first_message
