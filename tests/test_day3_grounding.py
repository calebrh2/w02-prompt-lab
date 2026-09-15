from __future__ import annotations

from pathlib import Path

from promptlab.config import PROJECT_ROOT
from promptlab.day3 import (
    LEAKAGE_MARKERS,
    citation_existence_failures,
    citation_matches_heading,
    leakage_hits,
    source_headings,
)
from promptlab.schemas import EvidenceField, PolicyExtraction


def test_numbered_headings_are_extracted() -> None:
    source = (
        "1. Document Control\nPolicy name: Example.\n"
        "2. Scope and Jurisdictions\nThe policy applies to Pennsylvania."
    )
    headings = source_headings(source)
    assert "1. Document Control" in headings
    assert "Document Control" in headings
    assert "2. Scope and Jurisdictions" in headings


def test_present_citation_must_match_a_heading() -> None:
    source = "1. Document Control\nTitle: Card Dispute Intake Procedure.\n"
    present = EvidenceField(
        value="Card Dispute Intake Procedure",
        status="present",
        citation="1. Document Control",
    )
    invented = EvidenceField(
        value="Card Dispute Intake Procedure",
        status="present",
        citation="Section 99",
    )
    fields = {"title": present, "version": invented}
    assert citation_matches_heading("1. Document Control", source)
    assert not citation_matches_heading("Section 99", source)
    assert citation_existence_failures(fields, source) == 1


def test_leakage_markers_are_absent_from_scored_extraction_cases() -> None:
    corpus = (PROJECT_ROOT / "cases" / "extraction.jsonl").read_text(encoding="utf-8")
    for marker in LEAKAGE_MARKERS:
        assert marker not in corpus


def test_leakage_hits_count_example_only_strings() -> None:
    clean = PolicyExtraction.model_validate(
        {
            "document_status": "valid",
            "policy_name": {
                "value": "Community Merchant Review Policy",
                "status": "present",
                "citation": "1. Document Control",
            },
            "version": {"value": "1.5", "status": "present", "citation": "1. Document Control"},
            "effective_date": {
                "value": "2025-02-01",
                "status": "present",
                "citation": "1. Document Control",
            },
            "jurisdictions": {
                "value": ["Pennsylvania"],
                "status": "present",
                "citation": "2. Scope and Jurisdictions",
            },
            "beneficial_ownership_threshold": {"value": None, "status": "absent"},
            "review_frequency": {
                "value": "24 months",
                "status": "present",
                "citation": "4. Review Frequency",
            },
            "required_documents": {
                "value": ["formation documents"],
                "status": "present",
                "citation": "5. Required Documents",
            },
        }
    ).model_dump()
    leaked = dict(clean)
    leaked["policy_name"] = {
        "value": "Northglass Merchant Review Standard",
        "status": "present",
        "citation": "1. Document Control",
    }
    assert leakage_hits(clean) == 0
    assert leakage_hits(leaked) >= 1


def test_extract_v2_does_not_embed_scored_case_ids() -> None:
    text = Path("src/prompts/extract.v2.md").read_text(encoding="utf-8")
    for case_id in [f"E{index:02d}" for index in range(1, 13)]:
        assert case_id not in text
