Few-Shot and Grounding
Why this matters on an engagement
The claim that will be challenged hardest in a BFS or Insurance engagement is not that the system is accurate. It is that the system's output is traceable to something. A compliance function can live with a model that gets a field wrong, because a human reviews it. It cannot live with a model that produces a statement nobody can locate in a source document, because that statement will end up in a case file, and the case file is the thing an auditor reads two years later. Grounding is what turns an answer into evidence, and it is a design property rather than a quality you hope for.

Examples are the other half. Some things about a task cannot be written down usefully. How terse a note should be, what counts as a conflict worth flagging rather than a wording difference, where the line sits between a document that is a policy and one that merely mentions policy. You can spend three paragraphs failing to define that boundary, or you can show two cases from either side of it. Choosing which two is most of the skill.

Core concepts
Examples specify what prose cannot. Few-shot examples are specification by instance. They are the right tool where a rule is easier to demonstrate than to state, and they are particularly effective on judgment boundaries: which of two adjacent categories a marginal case belongs to, how much detail a note carries, when a discrepancy is worth reporting. They are the wrong tool for anything you can simply state, and they are the wrong tool for structure, because structure is already enforced by the schema and by validation.

Examples are input tokens, paid on every call, forever. Four examples of a policy document with its expected extraction can easily double the input size of every request you ever make. Day 1's arithmetic applies directly: this is a permanent addition to cost per case, incurred whether or not the case is one the examples help with. That does not make examples a bad idea. It makes each one a decision that has to justify itself, and it makes the examples section the first place to look when cost per case is above budget. Where a provider supports caching a stable prefix, examples are exactly the kind of content that benefits, provided nothing above them varies between requests.

Choose examples from the edges, not the middle. The instinct is to show a clean, typical case, and that is the case the model already handles. Every example you spend should buy you behavior on a boundary. The productive sources are the failure shapes you meet in every week of this program: a document that is silent on a required field, a document that contradicts itself, a document that has been superseded, content that carries instructions aimed at the reader, and a case that is outside the task entirely. Two examples drawn from those cost less and teach more than five typical ones.

Examples leak, in two directions. Outward, the model copies surface detail from the example into real answers. You will see a section number, an entity name, or a phrase from your example appear in output about a completely different document, and it looks like a hallucination until you recognize where it came from. Inward, examples drawn from your evaluation cases contaminate the measurement, because you are now testing the model on material it was shown. Metrics rise, production does not, and the gap is invisible from inside the harness. Keep a separate example pool, never draw an example from the twelve cases you score against, and check outputs for values that exist only in your examples.

Negative examples need their correction attached. Showing a wrong output on its own frequently teaches the wrong output, because the example is the most concrete thing in the prompt and its status as a counterexample is carried by one word of surrounding prose. If you show a failure, show the input, mark the wrong output clearly, state in one line what is wrong with it, and show the correct output for the same input. If that feels like a lot of tokens for one lesson, it is, which is why the better move is usually to show only the correct handling of the case that produced the failure.

Grounding is a procedure, not an adjective. A model does not become grounded by being told to be. It becomes grounded when the prompt gives it a source, restricts it to that source, requires it to identify where in the source each statement came from, and gives it a defined way to report that the source does not contain the answer. Those four things are mechanical, and each one is checkable. Ordering matters too: requiring the citation to be produced alongside or before the claim, rather than appended afterward, tends to produce claims that follow the evidence rather than citations that decorate a conclusion the model already reached.

Grounding fails in two directions, and only one of them looks wrong. The first is a statement with no support, which validation catches when a citation is required. The second is more dangerous: a statement that is entirely correct, carrying a real citation, that the source document does not actually say. The model knew it from training, the citation points at a plausible section, and the answer is true. It is still a defect, because the system's claim is that its output is traceable to the supplied document, and here that claim is false. The failure survives review precisely because the content is right. The defenses are to require the citation to name something that exists in the document, and to spot-check whether the cited section supports the claim. Turning those checks into measurements is tomorrow's work.

Worked example
Here is the examples section added to the extraction prompt, producing prompts/extract.v2.md. The schema is the one from the previous article, so structure is enforced rather than demonstrated.

## Examples
These examples show how to handle documents that do not yield a clean answer.
They are not drawn from any document you will be given.

### Example A: a required field the document does not state
<document>
Corporate Client Review Standard, version 2.0, effective 2025-03-01
Section 3. Review cadence. Clients rated standard risk are reviewed every
36 months. Section 4. Documentation. Reviewers collect current registry
extracts and confirm the registered address.
</document>

Expected, in part:
  "required_documents": {
    "status": "present",
    "value": ["current registry extract", "confirmation of registered address"],
    "section": "Section 4"
  },
  "beneficial_ownership_threshold_percent": {
    "status": "absent"
  }

The document never states an ownership threshold. Absence is reported, not
inferred from what such policies usually say.

### Example B: a document that contradicts itself
<document>
Client Onboarding Policy, version 5.1, effective 2026-02-01
Section 2. Scope. This policy applies to entities incorporated in the
United Kingdom and Ireland. Appendix A. Coverage table: United Kingdom,
Ireland, Jersey, Guernsey.
</document>

Expected, in part:
  "jurisdictions": {
    "status": "ambiguous",
    "value": ["United Kingdom", "Ireland"],
    "section": "Section 2",
    "note": "Section 2 lists two jurisdictions. Appendix A lists four. Not resolved."
  }

Both readings are reported. The conflict is described rather than settled.

And the grounding constraints, which sit in the constraints section rather than here.

Every value you return must appear in the text between the document markers.
Give the section heading or number that contains it, exactly as the document
writes it. If you cannot name a section that contains the value, the field is
absent, whatever you may know about policies of this kind.

Four things about those choices.

Neither example is a normal case. A clean policy document with every field present would consume input tokens on every call for the rest of the engagement and would teach the model nothing it does not already do. Example A buys reporting of absence and Example B buys reporting of conflict, and both are failure shapes that appear in the case set and in all three capstone use cases.

The example documents are deliberately unlike the cases they will run against. Different document titles, different section numbering style, jurisdictions you can grep for. That is what makes leakage detectable. If Jersey or Section 4 shows up in an extraction from a document that contains neither, you know exactly where it came from, and you found it by searching rather than by noticing.

The examples show only the fields under discussion, not a full object. The schema and its validator already guarantee shape, so demonstrating shape is paying tokens for something you get free.

The final constraint sentence carries the weight of the second grounding failure mode. Instructing the model that a field is absent whatever it may know about policies of this kind is the difference between a system that reports what the document says and one that reports what is probably true. In a review packet destined for an auditor, those are not close.

Failure modes
Examples that teach the schema. Full expected objects shown for structure the validator already enforces. This is the most common way an examples section triples in size while adding nothing, and it makes the real lesson in each example harder to see.

Examples drawn from the evaluation set. Scores improve, the improvement is not real, and nothing in the harness reports the problem. Once an example has been taken from a scored case, that case is no longer evidence of anything, and the only clean fix is a separate example pool maintained from the start.

Surface copying. Entity names, section numbers, dates, and phrasing bleeding from examples into unrelated outputs. It reads as hallucination and it is contamination, so the diagnosis is a text search rather than a prompt rewrite. Examples whose surface detail is distinctive make this a five second check.

The unpaired negative example. A wrong output shown without its correction, or with the correction implied by surrounding prose, is as likely to be imitated as avoided. Either pair it with the corrected output for the same input or do not show it.

Grounded-sounding output. A statement that is true, carries a citation, and is not in the document. Review does not catch it, because reviewers check whether the answer is right. The check that catches it is whether the cited section exists and contains the claim, which is a different question and has to be asked deliberately.

Checklist
[ ] Every example earns its input token cost by covering a boundary rather than a typical case.

[ ] No example is drawn from any case in the scored set.

[ ] Example documents are distinctive enough in surface detail that leakage is detectable by search.

[ ] Examples show only the fields under discussion, not structure the schema already enforces.

[ ] Any negative example is paired with the correct output for the same input.

[ ] The prompt restricts answers to the marked source, requires a section citation, and defines what to return when the source is silent.

[ ] The prompt states that a value the document does not contain is absent regardless of what the model knows.

[ ] Outputs have been searched for values that exist only in the examples.

[ ] Cited sections have been checked, on at least a sample, for whether they exist and support the claim.

