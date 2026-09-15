from __future__ import annotations

import json
import re

from pydantic import BaseModel, ValidationError

from promptlab.adapters.base import CompletionRequest, ModelAdapter

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
_SCHEMA_META_KEYS = {
    "$defs",
    "$schema",
    "additionalProperties",
    "definitions",
    "properties",
    "required",
    "title",
    "type",
}


class StructuredCompletionError(Exception):
    """Raised when a structured completion cannot be validated within the repair budget."""

    def __init__(self, message: str, *, repairs: int) -> None:
        super().__init__(message)
        self.repairs = repairs


def _parse_json_payload(text: str) -> object:
    stripped = _FENCE_RE.sub("", text.strip()).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(stripped[start : end + 1])


def _coerce_instance(payload: object) -> object:
    if not isinstance(payload, dict):
        return payload
    cleaned = {key: value for key, value in payload.items() if key not in _SCHEMA_META_KEYS}
    properties = payload.get("properties")
    if isinstance(properties, dict):
        for key, value in properties.items():
            if key in cleaned or key in _SCHEMA_META_KEYS:
                continue
            if isinstance(value, dict) and ("status" in value or "value" in value):
                cleaned[key] = value
            if key == "document_status" and isinstance(value, str):
                cleaned[key] = value
    return cleaned


def _validate[T: BaseModel](schema: type[T], text: str | None) -> T:
    if text is None or not text.strip():
        raise ValueError("empty model response")
    payload = _parse_json_payload(text)
    try:
        return schema.model_validate(payload)
    except ValidationError:
        return schema.model_validate(_coerce_instance(payload))


def _repair_request(request: CompletionRequest, error: str) -> CompletionRequest:
    repair_content = (
        f"{request.user_content}\n\n"
        "Your previous response failed validation with the following error. "
        "Return a corrected JSON instance that validates against the schema. "
        "Do not echo JSON Schema metadata such as $defs, properties, type, or title. "
        "document_status must be a bare string enum value, not an object. "
        "Every EvidenceField must include value (use null when absent). "
        "Correct only what the validation error concerns.\n"
        f"<error>{error}</error>"
    )
    return request.model_copy(update={"user_content": repair_content})


def complete_structured[T: BaseModel](
    adapter: ModelAdapter,
    request: CompletionRequest,
    schema: type[T],
    run_id: str,
    max_repairs: int = 1,
) -> T:
    """Return a schema-validated completion with a bounded semantic repair loop.

    Transport retry remains inside the adapter.
    Schema/content repair belongs here.

    On validation failure, send the validation error text back to the model and
    instruct it to correct only what the error concerns. Do not perform more
    than max_repairs semantic repair attempts.
    """

    current = request
    repairs = 0

    while True:
        result = adapter.complete(current, run_id)
        if not result.succeeded:
            raise StructuredCompletionError(
                result.error_type or "adapter call failed",
                repairs=repairs,
            )
        try:
            return _validate(schema, result.text)
        except (ValidationError, ValueError, json.JSONDecodeError, TypeError) as exc:
            if repairs >= max_repairs:
                raise StructuredCompletionError(str(exc), repairs=repairs) from exc
            repairs += 1
            current = _repair_request(request, str(exc))
