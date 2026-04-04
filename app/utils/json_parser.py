import json
import re
from app.schemas.action_schema import ActionResponse
from app.utils.logger import setup_logger

logger = setup_logger("json_parser")


def extract_json(raw_text: str) -> dict:
    text = raw_text.strip()

    # Intentar parsear directamente
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Buscar JSON dentro de bloques de codigo markdown
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    # Buscar el primer { ... } en el texto
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError(f"No se encontro JSON valido en la respuesta: {text[:200]}")


def validate_action_response(data: dict) -> ActionResponse:
    return ActionResponse(**data)


def parse_llm_response(raw_text: str) -> ActionResponse:
    data = extract_json(raw_text)
    return validate_action_response(data)
