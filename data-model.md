# Data model — three entities, one join key

The join key across all three entities is **technique ID + finding ID**. Findings carry both; mitigations carry at least one of them; status rows carry the finding ID.

Input formats: CSV, XLSX (single sheet per file, or one workbook with sheets named `findings` / `mitigations` / `status`), or JSON (array of objects, or `{"findings": [...], "mitigations": [...], "status": [...]}`).

Column matching is case-insensitive, ignores spaces/underscores/dashes, and accepts the aliases below. Extra columns are kept and shown in detail drawers.

## 1. Findings (Red)

| Canonical column | Required | Aliases accepted | Notes |
|---|---|---|---|
| `finding_id` | yes | id, finding, ref, issue_id, vuln_id | Unique per finding. Duplicates are merged (last row wins) and flagged. |
| `technique_id` | yes* | technique, attack_technique, mitre, mitre_id, ttp, att&ck | One or many, separated by `;` `,` `\|` or newline. `T1003.001` allowed. *Missing → flagged as unmapped, still shown in scorecard. |
| `title` | no | name, summary, description | |
| `severity` | no | sev, risk, rating, cvss, vpr | Critical/High/Medium/Low/Info, or numeric (CVSS/VPR 0–10 → bucketed). Default Medium. |
| `asset` | no | target, host, hostname, target_asset, system | |
| `attack_path` | no | path, chain, scenario, kill_chain | Groups findings for the attack-path rollup. Default `(unassigned)`. |
| `tactic` | no | mitre_tactic, phase | Free text; if absent, derived from technique via the built-in table. |
| `exploitability` | no | exploit, exploited, demonstrated | `demonstrated` / `exploit_available` / `theoretical` (default `demonstrated` — Red found it). |
| `internet_exposed` | no | external, internet_facing, public | true/false/yes/no/1/0. |
| `acr` | no | asset_criticality, criticality | 1–10 (Tenable ACR) or Critical/High/Medium/Low. |
| `red_evidence` | no | evidence, proof, poc | Free text or link. |
| `date_found` | no | found, discovered, date | ISO or common formats. |
| `status` | no | state | Used only if no Status row exists for the finding. |

## 2. Mitigations (Blue)

| Canonical column | Required | Aliases | Notes |
|---|---|---|---|
| `mitigation_id` | yes | id, control_id, rule_id, ticket, change | |
| `name` | no | control, rule, title, description | |
| `type` | no | category, kind | `control` / `compliance_rule` / `remediation` / `detection`. Default `control`. |
| `technique_ids` | one of these two | technique, techniques, mitre, blocks, covers | Techniques this mitigation is meant to block. |
| `finding_ids` | one of these two | findings, finding, addresses, fixes | Explicit finding links (preferred over technique-only mapping). |
| `status` | no | state, implementation | Same vocabulary as Status below. Default `open`. |
| `validation_status` | no | validated, retest, retest_result, verified | `not_retested` / `retest_pass` / `retest_fail`. |
| `validated_date` | no | retest_date, verified_date | |
| `owner` | no | assignee, team | Editable in the dashboard. |
| `ticket_id` | no | ticket_number, jira, incident, change_ticket | Ticket that tracks the mitigation. Editable in the dashboard. |
| `evidence` | no | proof, reference, link | |
| `framework` | no | standard, source | e.g. CIS 5.2, NIST AC-6, internal. |

## 3. Status

| Canonical column | Required | Aliases | Notes |
|---|---|---|---|
| `finding_id` | yes | id, finding, key, issue, ref | Must match a Findings row; unmatched rows are flagged, not dropped. |
| `status` | yes | state, resolution, workflow_status | Normalized per the vocabulary below. |
| `validation_status` | no | retest, retest_result, verified, validated | |
| `validated_date` | no | retest_date | |
| `ticket_id` | no | ticket, key, jira, incident | |
| `owner` | no | assignee | |
| `updated_date` | no | updated, last_updated, modified | Used to pick the latest row when a finding has several. |
| `notes` | no | comment, resolution_notes | |

## Status vocabulary normalization

Ticketing systems disagree on words. The script maps them into six **effective statuses**:

| Effective status | Matches (case-insensitive, substring) |
|---|---|
| `open` | open, new, to do, todo, backlog, reported, confirmed, reopened, unresolved, pending |
| `in_progress` | in progress, in-progress, working, assigned, doing, scheduled, planned, mitigating, awaiting patch |
| `remediated` | remediated, fixed, resolved, closed, done, complete, patched, mitigated, implemented, deployed |
| `validated` | validated, verified, retest pass, retested, confirmed fixed, closed-verified |
| `validated_failed` | retest fail, retest failed, validation failed, still exploitable, reopened after retest |
| `accepted` | accepted, risk accepted, won't fix, wontfix, exception, waived, deferred |

Anything else → `open` plus a data-quality flag `unknown_status:<original>`. Add domain-specific words via `--status-map extra.json` (`{"my word": "remediated"}`).

Validation status normalizes to `not_retested` (default), `retest_pass` (pass, passed, verified, blocked, validated, ok), `retest_fail` (fail, failed, bypass, still exploitable, not blocked).

## Join rules

1. **Status → Finding**: match on `finding_id`. If several status rows exist, keep the one with the latest `updated_date` (or the last one in file order if no dates). A finding with no status row uses its own `status` column, else `open`, and gets flag `no_status_row`.
2. **Mitigation → Finding**: link by explicit `finding_ids` first. If a mitigation has no finding IDs (or they match nothing), link by shared `technique_id` to every finding with that technique. Technique-only links are marked `link_type=technique` and, if one mitigation fans out to more than 15 findings, flagged `coarse_mapping`.
3. **Effective status** of a finding = the strongest evidence available, in this precedence:
   - `retest_fail` anywhere (status row or linked mitigation) → `validated_failed`
   - `retest_pass` anywhere, or status `validated` → `validated`
   - status `accepted` → `accepted`
   - status `remediated`, or any linked mitigation `remediated`/`validated` with no contrary retest → `remediated`
   - status `in_progress` → `in_progress`
   - else `open`
4. **Technique coverage** (heatmap) per technique:
   - `red_demonstrated` = any finding with that technique
   - `blue_claimed` = any linked mitigation with status remediated/validated, or any finding effective status remediated
   - `blue_validated` = at least one finding on the technique is `validated`, and every finding is `validated` or `accepted`
   - `gap` also whenever any finding on the technique is `validated_failed` — a failed retest beats any claim
   - `accepted` = every finding on the technique is `accepted`
   - `untested_coverage` = mitigation maps to the technique but no finding has it

## Data-quality flags (never dropped, always listed)

| Flag | Meaning | Entity |
|---|---|---|
| `missing_technique` | finding has no technique ID | finding |
| `invalid_technique:<value>` | not `T####` / `T####.###` | finding / mitigation |
| `duplicate_finding_id` | same ID on several rows; last wins | finding |
| `no_status_row` | no status record; defaulted from finding or `open` | finding |
| `unknown_status:<value>` | unrecognized status string; treated as open | finding / mitigation |
| `orphan_mitigation` | mitigation maps to no finding and no technique present in Red data | mitigation |
| `coarse_mapping` | technique-only mitigation linked to >15 findings | mitigation |
| `unknown_finding:<id>` | status row for a finding not in the Red data | status |
| `conflict_claim_vs_retest` | status says remediated but a retest says fail | finding |

The Data quality tab shows counts per flag and the affected rows, exportable to CSV so the owner of each dataset can fix the source.

## 4. Blue edits (manual overrides) — `blue_edits.json` / `blue_edits.csv`

Values Tenable cannot supply (retest date, owner, ticket number, and optionally the retest result) can be entered by hand. They live in one file, keyed by the row they belong to, and are applied by `purple_join.py --overrides` before scoring. Edits made inside the dashboard HTML use exactly this schema, so the file round-trips both ways.

| Canonical column | Required | Aliases | Notes |
|---|---|---|---|
| `target_id` | yes | id, mitigation_id, finding_id, ref | A `mitigation_id` (Blue control) or a `finding_id` (remediated finding with no mapped control — the "ticket" rows of the Validation tab). Unknown IDs are flagged `unknown_edit_target`, not dropped silently. |
| `owner` | no | assignee, team | |
| `validated_date` | no | retest_date, data_do_reteste | Retest date. |
| `ticket_id` | no | ticket_number, ticket, jira, incident | |
| `validation_status` | no | retest, retest_result | `not_retested` / `retest_pass` / `retest_fail` (pass/fail words accepted). Setting `retest_pass` promotes the linked finding to `validated`; `retest_fail` to `validated_failed`. |
| `note` | no | notes, comment | Appended to the mitigation evidence / status notes. |
| `edited_at`, `edited_by` | no | updated, editor | Provenance. |

JSON form: `{"blue_edits": [ {...}, ... ]}` or a bare array. Precedence: edits embedded in the `--prior` state are applied first, then the `--overrides` file — later wins per `target_id`. Edits never override a Tenable **Resurfaced** state (evidence beats claim).
