from __future__ import annotations

import json
import types
from typing import Literal, Union, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field

TaskName = Literal["triage", "summarization", "extraction"]
FieldStatus = Literal["present", "absent", "ambiguous"]
DocumentStatus = Literal["valid", "contradictory", "superseded", "unsupported"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceField(StrictModel):
    value: str | list[str] | None
    status: FieldStatus
    citation: str | None = None


class TriageOutput(StrictModel):
    queue: Literal[
        "card_dispute",
        "fraud_report",
        "account_servicing",
        "lending",
        "complaint",
        "escalate",
        "unsupported",
    ]
    escalation_required: bool
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    draft_reply: str
    human_review_required: Literal[True]
    customer_outcome: None = None


class SummarizationOutput(StrictModel):
    document_status: DocumentStatus
    title: EvidenceField
    version: EvidenceField
    effective_date: EvidenceField
    purpose: EvidenceField
    required_steps: EvidenceField
    exceptions: EvidenceField

    def evidence_fields(self) -> dict[str, EvidenceField]:
        return {
            "title": self.title,
            "version": self.version,
            "effective_date": self.effective_date,
            "purpose": self.purpose,
            "required_steps": self.required_steps,
            "exceptions": self.exceptions,
        }


class PolicyExtraction(StrictModel):
    document_status: DocumentStatus
    policy_name: EvidenceField
    version: EvidenceField
    effective_date: EvidenceField
    jurisdictions: EvidenceField
    beneficial_ownership_threshold: EvidenceField
    review_frequency: EvidenceField
    required_documents: EvidenceField

    def evidence_fields(self) -> dict[str, EvidenceField]:
        return {
            "policy_name": self.policy_name,
            "version": self.version,
            "effective_date": self.effective_date,
            "jurisdictions": self.jurisdictions,
            "beneficial_ownership_threshold": self.beneficial_ownership_threshold,
            "review_frequency": self.review_frequency,
            "required_documents": self.required_documents,
        }


OUTPUT_SCHEMAS: dict[TaskName, type[StrictModel]] = {
    "triage": TriageOutput,
    "summarization": SummarizationOutput,
    "extraction": PolicyExtraction,
}


def schema_description(model: type[BaseModel]) -> str:
    """Return an instance-shaped description generated from a Pydantic model."""

    guide = {
        name: _describe_annotation(field.annotation) for name, field in model.model_fields.items()
    }
    return json.dumps(guide, indent=2)


def _describe_annotation(annotation: object) -> object:
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Literal:
        return " | ".join(str(arg) for arg in args)

    if origin is Union or origin is types.UnionType:
        without_none = [arg for arg in args if arg is not type(None)]
        has_none = len(without_none) != len(args)
        described = [_describe_annotation(arg) for arg in without_none]
        if len(described) == 1:
            inner = described[0]
            if has_none:
                return f"{inner} | null" if isinstance(inner, str) else [inner, None]
            return inner
        parts = [item if isinstance(item, str) else json.dumps(item) for item in described]
        joined = " | ".join(parts)
        return f"{joined} | null" if has_none else joined

    if origin is list:
        item = _describe_annotation(args[0]) if args else "any"
        return [item]

    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return {
            name: _describe_annotation(field.annotation)
            for name, field in annotation.model_fields.items()
        }

    if annotation is str:
        return "string"
    if annotation is bool:
        return "boolean"
    if annotation is int:
        return "integer"
    if annotation is float:
        return "number"
    if annotation is type(None):
        return "null"
    return getattr(annotation, "__name__", str(annotation))

