# L0-ROLE-CONTRACT — draft for Founder review

Date: 2026-11-03, Asia/Shanghai. **L0-DESIGN ONLY; proposed contracts, not deployed.**
Baseline `main`: `aada128c065854b30f28dbdbe61fd2b0784ff1a0`.
See [protocol](L0-PROTOCOL.md), [evaluation](L0-EVALUATION-SPEC.md),
and [readiness](L0-READINESS-REPORT.md).

## Roster and boundaries

The Founder confirmed the eight existing roles in this task: Macro, News,
Company, Market, Skeptic, Chief, Review, Memory. M1 explicitly references the
first six roles; the mission names Review and Memory. The repository does not
contain deployed identity IDs, prompt versions, or signed responsibility
bindings. The role roster is confirmed; binding deployed identities to these
contracts remains a pre-pilot verification requirement. No ninth Bot is proposed.
Codex is the engineering agent, not a trading specialist or additional Bot.

Chief is the sole research decision authority: only Chief selects probabilities,
thresholds, primary research conclusions and final study hypotheses. The
`primary_call` for a formal forecast is **derived deterministically** from the
frozen `probs` vector by argmax and the precommitted tie-breaking order; it
cannot contradict the frozen probabilities. Specialists recommend; Skeptic
cannot choose the forecast; Codex cannot choose or tune a strategy.

Founder grants gates and activation permissions. Review and Memory cannot rewrite
frozen evidence, even with Chief's agreement.

## Shared input/output envelope

Every request includes `request_id`, `draft_revision_ref`, `as_of_utc`,
`knowledge_cutoff_utc`, `requested_by`, `recipient_role`, `task_scope`,
`strategy_ref` (version/hash), `memory_snapshot_ref`, allowed input record refs,
permitted source policy, horizon/session, and evidence class. A post-freeze task
also includes the original `prediction_ref` (ID/hash kind/hash), freeze receipt,
and the relevant outcome/score refs. Missing required inputs produce a blocked
response, not fabricated defaults.

Every response includes the common record envelope from L0-PROTOCOL plus
`request_ref`, exact input refs, `as_of_utc`, `claims`, `source_refs`,
`uncertainties`, `missing_inputs`, `status` (`COMPLETE`, `PARTIAL`, or `BLOCKED`),
and a content hash. Claims distinguish observed fact, inference, and assumption.
Each source ref includes publisher, instrument/topic, publication UTC time,
version or archived bytes/hash, retrieval UTC time, and cited passage/data field.
Unknown time/version is explicitly unknown. The full input/output transcript,
model/prompt identifiers when available, and tool-access record accompany it.

Pre-freeze inputs must be available by the shared cutoff. Review/Memory can read
later outcomes only in labeled post-outcome records. Chief's next research view
can read only approved memory and outcomes available by that next cutoff.
No role may silently fetch later revisions, rewrite dates, omit adverse evidence,
or use the synthetic price book as actual market data. Source collection itself
requires a later approved access procedure; no API collection happens now.

## Role-specific contracts

| Existing role | Exact required inputs beyond envelope | Required outputs | Forbidden authority/actions |
| --- | --- | --- | --- |
| **Macro** | Instrument exposure, target session, cutoff, approved historical macro snapshots/calendar | Macro thesis; each catalyst's scheduled release time as known at cutoff; observed releases versus future scenarios; causal channel; alternate interpretation; uncertainty/source gaps | Cannot use unreleased values, future realized events, change Chief forecast or place orders |
| **News** | Cutoff-bounded news inventory, issuer/theme scope and target horizon | Timestamped material event inventory; fact versus headline interpretation; duplicates/corrections; expected direction conditional on scenarios; opposing news; source confidence | Cannot treat later headlines/edited articles as earlier knowledge or freeze a prediction |
| **Company** | Ticker and point-in-time constituent/exposure snapshot, relevant filings/results available by cutoff | Company/sector concentration map; earnings/guidance facts; known catalyst schedule; instrument transmission hypothesis; contradictory evidence and missing coverage | Cannot use current constituents to reconstruct history without as-of evidence or promote a strategy |
| **Market** | Manually approved point-in-time baseline price/session/source, historical price/volume snapshots and definitions | Baseline provenance reconciliation; market/volatility/liquidity observations with windows and formulas; split/adjustment flags; band/measurement ambiguity; unavailable data | Cannot substitute synthetic marks, future closes, adjusted prices for the frozen price basis, or generate fills |
| **Skeptic** | Exact Chief draft revision/hash; all four specialist responses and source inventory; strategy/memory refs | At least **three distinct substantive challenge records**, each with `challenge_id`, challenged claim/ref, failure mechanism, supporting evidence or explicit unknown, alternative hypothesis, possible probability/band implication, severity and resolution test | Cannot satisfy quota with reworded objections, choose final probabilities, veto based only on disagreement, or waive provenance failures |
| **Chief** | Four specialist responses (including explicit partial/blocked statuses), ≥3 substantive challenges, source/cutoff report, active strategy/memory versions | Challenge disposition for every ID; final `prediction_v1` for new eligible samples; final rationale/assumptions; prefreeze L0 measurement envelope; freeze authorization and custody handoff; after review, memory/candidate disposition; formal `primary_call` derived from frozen probabilities | Cannot freeze through critical evidence failure, edit frozen artifacts, activate a version without Founder approval, clear risk halts or authorize infrastructure |
| **Review** | Original frozen bytes/ref and strategy; verified outcome and score refs; research/challenge transcripts; provenance and exclusion report | Separate forecast correctness, probability quality, reasoning quality and data quality; challenge follow-through; leakage/selection checks; sample eligibility with reasons; proposed lesson and counterevidence; review hash and Chief response request | Cannot recast probabilities/bands, choose a more favorable close, erase failed samples, score before verified outcome, or turn one result into a learning claim |
| **Memory** | Immutable review refs and all original prediction refs; current memory version/hash; Chief disposition; prior lessons/counterevidence | `memory_revision` proposal with parent ref; lesson, evidence refs, counterevidence, scope, confidence, action/avoidance rule, expiry/review trigger, falsification condition and proposed strategy diff | Cannot activate itself, revise old memory in place, relabel training evidence as holdout, backdate availability, or alter frozen forecast/score evidence |
| **Codex (engineering)** | Approved record contracts, exact source bytes, hashes and timing evidence; Chief's frozen outputs; independently verified outcome after horizon | Integrity/eligibility validation report; reproducible arithmetic specification and, only after implementation approval, deterministic scoring outputs; audit/defect report; versioned engineering changes only within later authorized scope | Cannot make research/trading decisions, fetch market APIs here, run simulator/trading fixtures, tune candidates to outcomes, modify accepted G1/G2a, self-approve gates, deploy or merge without authority |

## Handshake and escalation rules

1. Chief issues one request scope; specialists return content-addressed responses.
   A missing specialist response must be visible; Chief cannot label an incomplete
   packet complete. Founder must approve any narrower pilot coverage in advance.
2. Skeptic challenges the same draft revision Chief will finalize. Chief records
   each disposition. Rejected challenges retain their original wording and
   evidence. Unresolved substantive disagreement can remain disclosed; critical
   integrity/cutoff failures block freeze.
3. Codex checks technical completeness without substituting a forecast. Chief
   authorizes the research freeze; a contemporaneous receipt proves custody.
   The minimum proposed custody is immutable exact bytes plus explicit hash
   and a separately verifiable server-recorded receipt before the outcome.
   Git author date or local file mtime alone is not sufficient.
4. Once authorized and due, Review verifies outcome provenance; Codex produces
   arithmetic; Review signs off the score/input linkage. Disagreement creates
   `OUTCOME_DISPUTED` or `SCORE_DISPUTED`; no preferred result is selected silently.
   Track `lifecycle_status` and `eligibility_status` as separate record axes.
5. Memory proposes; Chief accepts, rejects, or defers; Founder controls eligibility
   and activation. Every version is immutable and availability-dated. Research
   receives an explicit memory snapshot, never an evolving unlogged conversation.

No Bot is started by this task. Existing instances may share a model/provider;
role separation alone does not establish independent judgment. Record shared
inputs and model/prompt identities; Founder must accept this limitation before
piloting or approve an independent human review arrangement without adding Bots.

## Scope and authority at this handoff

This role contract is a versioned design draft only. The eight role names are
confirmed; deployed Bot identities remain UNVERIFIED. No role prompt or runtime
identity was changed. No service, model or external API has been invoked.

Founder adoption of the protocol, custody/access plan and role bindings is a
separate later decision; this Draft PR does not grant an experiment pilot, scoring
implementation, broker/Alpaca connectivity, G2b, automation or any orders.
