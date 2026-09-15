Structured Outputs
Why this matters on an engagement
Everything downstream of the model is ordinary software. A queue that expects one of six values, a case record with typed fields, a report that counts how many reviews came back incomplete. None of that can consume a paragraph. The moment a model output has to be acted on by code rather than read by a person, the interesting question stops being whether the answer is good and becomes whether the answer has a shape you can rely on, every time, including on the cases where the model has nothing useful to say.

This is also where most of the integration pain in an agentic engagement actually lives. Teams spend a week on prompt wording and then lose a fortnight to output that is right in substance and unparseable in form, or parseable but subtly wrong in ways that only appear when a downstream system branches on a value nobody constrained. The work in this article is what prevents that fortnight.

Core concepts
The schema is the contract, and the prompt is how you obtain it. Define the output as a Pydantic v2 model in src/promptlab/schemas.py, and treat that definition as the single source of truth. The prompt describes the required output, and where it does, the description should be generated from the model rather than typed out beside it. Two hand-maintained descriptions of the same structure will drift, and the drift is invisible until a field you removed from the schema is still being requested by the prompt and quietly discarded on parse. Everything downstream, including the scorer you build tomorrow, imports the schema and not the prompt.

Providers offer three levels of guarantee, and you build for the weakest one you support. At the strongest, a provider accepts a schema and constrains decoding so the response conforms structurally. In the middle sits a mode that guarantees syntactically valid JSON without guaranteeing it matches your schema, so you can parse but you cannot assume fields. At the weakest, you instruct, and you validate whatever arrives. The support differs by provider and by model and it changes, so check it for the versions you pinned rather than assuming. What matters architecturally is that your harness calls two providers behind one adapter, so the validation and repair path has to exist regardless. Where a provider offers a stronger guarantee, it reduces how often that path runs. It does not let you delete it.

Every field a downstream system branches on is an enumeration. A routing value returned as free text is not a routing value, it is a string that resembles one, and you will discover the difference the first time you get card disputes instead of card_dispute. Define the permitted values in the schema as an enum, and make sure the enum contains the values that represent trouble as well as the ones that represent success. If the only legal outputs describe outcomes the task handles, the model has no way to report a case it cannot handle, and the out-of-scope path from the previous article has nowhere to land.

Absent, ambiguous, and present are different states, and null cannot carry all three. A field returned as null might mean the document does not state the value, or that it states it twice in conflicting terms, or that the model failed to find something that is there. Those lead to different human actions: request the document, escalate the contradiction, and fix the prompt respectively. Collapsing them into one representation destroys information at exactly the point where the system is supposed to be producing it. Give each field an explicit status, and require the status rather than inferring it from whether a value came back.

Per-field citation is a schema decision before it is a prompt decision. The instruction to cite is worth little if the output has nowhere to put the citation, because the model will either append it to the value, corrupting the field, or drop it. Put the citation in the structure next to the value it supports. Cite a section identifier rather than a quoted span. Quoted spans multiply your output tokens, and output tokens are the expensive side of the bill, as Day 1's arithmetic showed. A section reference is enough for a human to verify and enough for the grounding checks you build tomorrow.

Validation is a boundary, and a validation failure is data. Parse the response into the schema and let it fail loudly when it does not conform. On failure, do not simply try again with the same input, because you will get the same result at twice the cost. Send the validation error back as part of a repair attempt, cap the attempts, and record every attempt through C1 so the true cost of the case includes what the repair cost. Track the rate. A schema that fails validation on one case in eight is telling you something about the schema, and the rate is the fastest signal you have that a change made things worse.

Schema shape affects adherence, so keep it shallow and small. Deeply nested objects, very large enumerations, and long lists of optional fields all degrade how reliably a model produces conforming output, and they inflate the output tokens on every call. Prefer flat structures with a handful of required fields. Never ask the model to echo back input you already have, which is a habit that produces schemas containing the entire source document and a bill to match. If a schema is getting large, the usual cause is that one prompt is doing two tasks, and splitting it will improve both adherence and cost.

Worked example
This is the extraction schema from src/promptlab/schemas.py.

from enum import StrEnum
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, model_validator

T = TypeVar("T")


class FieldStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    AMBIGUOUS = "ambiguous"


class Evidence(BaseModel, Generic[T]):
    """One extracted field, carrying its own status and citation."""

    model_config = ConfigDict(extra="forbid")

    status: FieldStatus
    value: T | None = None
    section: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def status_matches_content(self) -> "Evidence[T]":
        if self.status is FieldStatus.PRESENT:
            if self.value is None or self.section is None:
                raise ValueError("present requires both value and section")
        if self.status is FieldStatus.ABSENT and self.value is not None:
            raise ValueError("absent must not carry a value")
        if self.status is FieldStatus.AMBIGUOUS and not self.note:
            raise ValueError("ambiguous requires a note describing the conflict")
        return self


class PolicyExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_kind: Literal["kyc_periodic_review_policy", "other"]
    out_of_scope_reason: str | None = None

    document_version: Evidence[str]
    effective_date: Evidence[str]
    superseded_by: Evidence[str]
    entity_types_in_scope: Evidence[list[str]]
    review_triggers: Evidence[list[str]]
    required_documents: Evidence[list[str]]
    beneficial_ownership_threshold_percent: Evidence[float]
    jurisdictions: Evidence[list[str]]

    @model_validator(mode="after")
    def out_of_scope_is_explained(self) -> "PolicyExtraction":
        if self.document_kind == "other" and not self.out_of_scope_reason:
            raise ValueError("document_kind 'other' requires out_of_scope_reason")
        return self

Several decisions in there are worth more than the code.

Evidence is generic, which is one of the few places in this week's work where a generic earns its keep. The status, citation, and note logic is identical for every field, and the only thing that varies is the type of the value. Writing it once means the rule that present requires a citation is enforced everywhere rather than remembered in eight places.

The validator does the work the prompt cannot. An instruction to cite is a request. A model that returns status: present with no section fails validation, gets a repair attempt carrying that exact message, and either produces a citation or is recorded as a failure. That is the difference between requiring evidence and hoping for it.

extra="forbid" on both models means an invented field is an error rather than something silently dropped. Silent dropping is worse than it sounds, because the field the model invented is usually the one it put the real answer in.

document_kind carries the out-of-scope path that the previous article's prompt referred to and did not define. When the document is not a policy, there is a legal output that says so and requires a reason, and none of the extraction fields have to be forced into a shape they do not fit.

beneficial_ownership_threshold_percent is a float, not a string, and the field name states the unit. A threshold that arrives as twenty-five percent, 25%, or 0.25 in three different runs is not usable by anything downstream, and the type is what forces the question to be settled once.

Here is what a repair attempt looks like when validation fails.

Attempt 1 returned:
  "beneficial_ownership_threshold_percent": {"status": "present", "value": 25.0}

Validation error:
  beneficial_ownership_threshold_percent: present requires both value and section

Attempt 2 sends the original request plus:
  Your previous response failed validation with the following error. Return a
  corrected response. Do not change any field the error does not concern.
  <error>...</error>

Both attempts write a CallRecord, both count toward the case cost, and both count toward the spend ceiling. This is the mechanism behind the retry rate that made a real difference to the cost per case in Day 1's arithmetic, which is why it is worth measuring rather than assuming.

Failure modes
The schema that also lives in the prompt. A structure described by hand in the prompt and separately defined in Python will diverge, usually when a field is renamed in one place. The symptoms are strange: a field that is always absent, or a value that never validates, with no error anywhere. Generate the description from the model, or at minimum have one test that fails when they disagree.

Free text where code branches. A routing value, a status, or a category returned as an unconstrained string will eventually arrive in a form your code does not expect, and the failure lands in whatever consumes it rather than at the model boundary. Anything a downstream system compares against a fixed set belongs in an enum.

One null carrying three meanings. When absent, ambiguous, and not-found collapse into a single empty value, the human reading the output cannot tell whether to chase the document, escalate the conflict, or ignore the field. The information existed at the moment of extraction and the schema threw it away.

Retry without the error. Sending the identical request again after a validation failure usually produces the identical failure, at full price, and then a third time. Repair attempts must carry the validation message, must be capped, and must be recorded. An uncapped repair loop against a schema the model cannot satisfy is the fastest way to hit a spend ceiling.

The schema that grew. Nesting, optional sprawl, enormous enumerations, and fields that ask the model to repeat the input all reduce adherence and increase cost simultaneously. When adherence drops after a schema change, look at shape before you look at wording.

Checklist
[ ] The output schema is a Pydantic v2 model and is the only definition of the structure.

[ ] Any prompt text describing the output is generated from the schema or covered by a test that catches divergence.

[ ] Every field a downstream system branches on is an enum or a Literal.

[ ] The enum includes the values representing escalation and out-of-scope, not only successful outcomes.

[ ] Absent, ambiguous, and present are distinct states carried explicitly per field.

[ ] Citation has a place in the structure, and a present value without a citation fails validation.

[ ] extra="forbid" is set, so invented fields error rather than disappearing.

[ ] Repair attempts carry the validation error, are capped, and write a CallRecord each.

[ ] No field asks the model to return input you already have.

