---
name: tenable-purple-team-dashboard
description: Red Team vs. Blue Team (Purple Team) dashboard: joins attack findings (pentest / attack-path results with MITRE ATT&CK technique IDs) against remediation and compliance evidence and computes what is STILL exposed. ALWAYS use for: purple team dashboard, red vs blue scorecard, residual risk, ATT&CK / MITRE coverage heatmap, technique coverage, validate remediation, retest results, "what can Red still do", pentest findings vs remediation, control coverage gaps; PT: red vs blue, risco residual, heatmap ATT&CK, validar remediacao, cobertura de tecnicas. ALWAYS pulls base data live from the Tenable MCP (findings, asset ACR/exposure, finding state, compliance); uploaded CSV/XLSX/JSON are optional overlays only (pentest evidence, ticket status, GRC mappings, manual Blue edits: owner, retest date, ticket). Produces a standalone HTML dashboard (scorecard, ATT&CK heatmap, validation scoreboard with editable Blue fields, residual risk, run-over-run delta) updated in place each engagement. Read-only.
---

# Tenable Purple Team Dashboard

Red and Blue data live in separate silos — pentest / attack-path findings on one side, remediation tickets and compliance rules on the other — so nobody can answer "given what Blue actually fixed, what can Red still do?" This skill joins the two sides on **ATT&CK technique ID + finding ID**, computes residual risk from what is still unmitigated, and renders one shared dashboard for Red, Blue, Purple leads and security managers.

Every run produces four components in a single standalone HTML file:

1. **Scorecard** — each Red finding next to the Blue mitigation(s) mapped to it, with effective status (open / in progress / mitigated / validated).
2. **ATT&CK heatmap** — techniques Red demonstrated vs. techniques Blue's controls actually block, colored by coverage gap.
3. **Validation scoreboard** — for each claimed mitigation, whether it was re-tested and confirmed to block the attack (not just "ticket closed").
4. **Residual risk** — unmitigated finding × severity × exploitability × exposure, rolled up by attack path, technique and overall, plus the top N residual items.

Plus a **Data quality** tab (unmapped findings, orphan mitigations, unknown statuses — never silently dropped) and a **Changes since last run** tab when a prior version exists.

The skill is read-only: it never changes Tenable, tickets or compliance systems.

---

## Workflow

### Step 1 — Pull the three entities from the Tenable MCP (mandatory)

The Tenable MCP is the source of truth for every run. Do not ask the user for files first, do not offer file mode as an alternative, and do not run on sample data for a real engagement.

1. **Load the Tenable tools.** They are deferred: call `tool_search` with specific queries (e.g. `"tenable one search findings"`, `"workbenches list vulnerabilities"`, `"tenable one search assets"`) and note the exact parameter names returned. Generic queries such as "purple team" find nothing.
2. **If no Tenable MCP tool comes back**, stop and tell the user the skill needs the Tenable connector enabled in this chat (Settings → Connectors) — then wait. Do not fall back to uploads or to `assets/sample_data/`. A demo run on sample data is allowed only when the user explicitly asks for a demo and the output is labeled as sample.
3. **Pull each entity** following `references/connector-mode.md` exactly — it is the operating procedure, not an optional appendix. In short:

| Entity | Tenable MCP source | Optional overlay (only if the user provides it) |
|---|---|---|
| **Findings** (Red) | Attack-path steps (technique IDs native) → `tenable_one_search_findings` Critical/High → `workbenches_list_vulnerabilities` severity=critical, then high in small pages. Enrich `acr` / `internet_exposed` from `tenable_one_search_assets` (asset_class=DEVICE). | Pentest report CSV/XLSX/JSON with Red-confirmed techniques and evidence — merged by `finding_id`; overlay wins on `technique_id`, `exploitability`, `red_evidence`. |
| **Mitigations** (Blue) | Tenable compliance findings (CIS/PCI audit results), each rule → one mitigation, pass = `remediated`, fail = `open`. | GRC / control export with ATT&CK mappings. |
| **Status** | Tenable finding state: New / Active → `open`, Fixed → `remediated`, Resurfaced → `validated_failed`. | Jira / ServiceNow export or connector — merged by `finding_id`, latest `updated_date` wins. |

4. **Write each entity to JSON** in the working directory (`purple-team/inputs/findings.json`, `mitigations.json`, `status.json`) using the canonical columns in `references/data-model.md`, and always pass `--source-findings "Tenable MCP (live, <date>)"` etc. so the dashboard header shows provenance.

Rules:
- The MCP pull is the base for all three entities. An uploaded file never replaces the MCP data; it is merged on top and its rows are labeled `overlay` in the detail drawer.
- If Tenable has no compliance data, proceed without mitigations — the scorecard shows "no mapped mitigation", the heatmap shows Red without Blue, and Data quality says so. Do not block the run and do not invent controls.
- `finding_id` and `technique_id` are the only hard requirements for findings; findings the MCP cannot map to a technique are kept and flagged `missing_technique` with `mapping_source=plugin_default` when a default table was used.
- Respect the tenant-level blockers in `references/connector-mode.md` (no CSV export pipeline, no unfiltered High-severity queries, Critical-first pagination).

### Step 1b — Collect manual Blue edits (retest date, owner, ticket)

Tenable does not know who owns a mitigation, which ticket tracks it, or when Red re-tested it. Those come from people, in one of two ways — both use the same `blue_edits` schema (`references/data-model.md` §4):

- **Before the run**: a `purple-team/blue_edits.json` or `.csv` the user maintains (or exported from the previous dashboard). Pass it with `--overrides`. Check the working folder / uploads for it before asking.
- **After the run, inside the HTML**: the Validation tab lets the user type the retest date, owner, ticket number and retest result directly into the table, then *Export edits* (JSON/CSV) or *Download dashboard with edits*. Either artifact feeds the next run (`--overrides` or `--prior`).

Edits embedded in the prior state are carried forward automatically; the overrides file is applied on top (later wins per `target_id`). Unknown target IDs surface in Data quality as `unknown_edit_target` — tell the user rather than silently dropping them.

### Step 2 — Locate the prior run (recurring-update case)

The dashboard is meant to be updated in place each engagement/quarter, so before computing anything look for a previous version, in this order:

1. In Cowork: the working folder — look for `purple-team/purple_state.json` or `purple-team/tenable-purple-team-dashboard.html`.
2. In claude.ai: a prior state JSON or prior dashboard HTML the user uploaded.
3. Ask: "Is there a previous purple team dashboard I should diff against?"

Every rendered dashboard embeds its own state (`<script id="purple-state" type="application/json">`), so the prior HTML alone is enough — no separate database. If nothing is found, this is run 1 and the Changes tab is omitted.

### Step 3 — Normalize, join, score (deterministic script)

Copy the inputs to a working directory and run the join script. Do not hand-compute the join or the risk score in reasoning — the script is deterministic and reproducible across quarters, which is the point of a recurring dashboard.

```bash
python3 scripts/purple_join.py \
  --findings <findings.csv|xlsx|json> \
  --mitigations <mitigations.csv|xlsx|json> \
  --status <status.csv|xlsx|json> \
  --prior <previous purple_state.json or dashboard .html>   # omit on run 1
  --overrides purple-team/blue_edits.json|csv                # manual owner / retest date / ticket edits, if any
  --engagement "Q3 2026 internal pentest" \
  --top 15 \
  --out purple_state.json
```

What it does (details in `references/data-model.md` and `references/residual-risk.md`):
- Matches columns by alias, splits multi-valued technique/finding cells (`;` `,` `|`), validates technique IDs (`T####` or `T####.###`), normalizes ticket vocabularies into six effective statuses.
- Joins Status → Finding by `finding_id` (latest update wins); joins Mitigation → Finding by explicit `finding_id`, else by shared `technique_id`.
- Computes per-finding residual risk and rolls it up by technique, tactic, attack path and overall; normalizes to a 0–100 residual index.
- Flags data-quality issues instead of dropping rows: findings with no or invalid technique ID, mitigations that map to nothing in the Red data, status rows for unknown findings, findings with no status row (defaulted to open and flagged), unrecognized status strings.
- Diffs against the prior state: new / resolved / regressed / changed findings and score deltas per technique.
- Applies Blue edits (owner, retest date, ticket, retest result) from the prior state and `--overrides`, and embeds the merged list as `blue_edits[]` so it survives the next run.

Read the script's summary output. If the data-quality count is large (say >20 % of findings unmapped), tell the user before rendering — the heatmap will under-represent Red and the residual score will be optimistic.

### Step 4 — Render the dashboard

```bash
python3 scripts/render_dashboard.py --state purple_state.json --out tenable-purple-team-dashboard.html [--lang pt|en]
```

The renderer produces a standalone HTML (inline CSS/JS, no CDN) following `references/dashboard-spec.md`: dark theme, background `#44494B`, accent `#E7FF00`, semantic colors Blue `#4EA5FF` / Green `#71FFC6` / Purple `#BB8FF2` / Orange `#FF8837` / Red `#FF4B4B`, PT/EN toggle, sortable tables, CSV export per table, and the embedded state block used by the next run. Technical terms (residual risk, attack path, technique, VPR, ACR) stay in English in the Portuguese copy.

Only edit the renderer if the user asks for a layout change; ordinary runs should not touch it.

### Step 5 — Persist in place and present

- **Cowork**: write `purple_state.json` and `tenable-purple-team-dashboard.html` to `<working folder>/purple-team/`, overwriting the previous version (the previous state is already captured in the Changes tab and in `purple_state.previous.json`, which the script writes when a prior exists). This is the artifact that gets refreshed next quarter — do not create `dashboard-v2.html`.
- **claude.ai**: write both files to `/mnt/user-data/outputs/` and present them with `present_files`. Tell the user to upload either file next time to get the delta — and that owner / retest date / ticket can be filled in directly in the Validation tab and exported as `blue_edits.json` for the next run.

Then give a short readout in chat (5–8 lines, no tables): overall residual index and direction vs. last run, top 3 residual techniques, validated-vs-claimed ratio, and the data-quality headline. The dashboard carries the detail; the chat message carries the decision.

---

## Interpretation rules (what the numbers mean)

- **Effective status** per finding: `open` → `in_progress` → `remediated` (Blue says fixed, not re-tested) → `validated` (Red re-tested, attack blocked). `validated_failed` (re-test showed the attack still works) counts as open with a red flag. `accepted` (formal risk acceptance) is excluded from residual but listed separately — it is still a Red capability, just a governed one.
- **Residual risk** counts `remediated` at 40 % weight by default: a closed ticket that was never re-tested is not evidence the attack is blocked. Only `validated` drops a finding to zero. This is deliberate and should be explained if a Blue lead asks why closed tickets still score; weights are configurable via `--weights` (see `references/residual-risk.md`).
- **Heatmap colors**: red = Red demonstrated and nothing blocks it (no mitigation, or the retest failed); orange = mitigation claimed, not validated; green = validated block; blue = Blue control exists but Red never tested it (untested coverage — a Purple backlog item, not a win); gray = risk accepted.
- **Validation rate** = validated ÷ (remediated + validated). This is the single most useful Purple metric: it shows how much of Blue's claimed progress has actually been proven.

## Edge cases

- Multiple technique IDs on one finding: the finding contributes its full residual to each technique's rollup (so technique totals can exceed the overall total — say so in the dashboard footnote, which the renderer includes). Attack-path and overall rollups count each finding once.
- Sub-techniques (`T1003.001`) roll up into the parent (`T1003`) on the heatmap, and are listed individually in the technique table.
- A mitigation mapped by technique only (no finding IDs) links to every finding with that technique. If that produces an implausible fan-out (one control "covering" 40 findings), flag it in Data quality as a coarse mapping.
- Conflicting status: status file says `remediated`, mitigation says `retest_fail` → `validated_failed` wins (evidence beats claim).
- No prior run but the user expects a delta: say plainly there is nothing to diff against and that this run becomes the baseline.
- Connector timeouts (common on large Tenable tenants): fall back to Critical-first pagination as described in `references/connector-mode.md`, then smaller High-severity pages; never fall back to fabricated sample data or to file-only mode for a real engagement. If the pull is partial, say which severities/pages were covered in the chat readout and in Data quality.
- Tenable MCP not connected: stop at Step 1 and ask the user to enable it — do not proceed with uploads alone.

## Files in this skill

- `scripts/purple_join.py` — load, normalize, join, score, diff → `purple_state.json`
- `scripts/render_dashboard.py` — `purple_state.json` → standalone HTML with embedded state
- `references/data-model.md` — three entity schemas, column aliases, status vocabulary, join rules, data-quality flags, and the `blue_edits` manual-override schema
- `references/residual-risk.md` — formula, default weights, rollups, how to override
- `references/dashboard-spec.md` — tabs, components, palette, i18n, embedded state contract
- `references/connector-mode.md` — MANDATORY operating procedure for pulling the three entities live from the Tenable MCP (plus optional ticketing overlay)
- `assets/sample_data/` — `findings.csv`, `mitigations.csv`, `status.csv`, `blue_edits.csv` templates showing the overlay schema; usable for a demo run ONLY when the user explicitly asks for a demo — never as a substitute for the MCP pull
