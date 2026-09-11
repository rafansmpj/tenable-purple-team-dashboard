# Dashboard spec — what `render_dashboard.py` produces

Standalone HTML, inline CSS/JS, no external requests. Opens from disk. Works on desktop widths ≥ 1100 px and degrades to stacked cards below.

## Design system (Rafael's Tenable skills palette)

- Background `#44494B`, card surface `#363A3C`, borders `#5A5F62`, text `#F2F2F2`, muted text `#B5B9BC`
- Accent `#E7FF00` (headline number, active tab, primary buttons)
- Semantic: Blue `#4EA5FF` (info / untested coverage / new), Green `#71FFC6` (validated / resolved), Purple `#BB8FF2` (in progress / Purple team), Orange `#FF8837` (claimed, not validated), Red `#FF4B4B` (open / validated_failed / regressed)
- Typography: system sans (Inter, Segoe UI, Roboto fallback); monospace for IDs
- Red team elements use a subtle red left border, Blue team elements a blue left border, so the "side-by-side" reads at a glance.

## Header

- Title, engagement name, run date, run number (`Run 3`), "vs. previous run" date when a prior exists
- Language toggle **PT / EN** (all labels via `data-i18n`; technical terms stay in English in PT)
- KPI cards: **Residual index** (0–100, accent, with ▲/▼ delta vs prior), Findings by effective status (5 mini-bars), **Validation rate**, Techniques demonstrated / covered / validated, Data-quality issues (orange badge if > 0)

## Tabs

1. **Scorecard** — table: Finding ID · Title · Technique(s) · Severity · Asset · Attack path · Red status (demonstrated / exploit available / theoretical) · Blue mitigation(s) (chips, link type shown as `by finding` / `by technique`) · Effective status badge · Residual. Row click → drawer with all original columns, evidence, linked mitigations and status history. Filters: status, tactic, attack path, search. Export CSV.
2. **ATT&CK heatmap** — Enterprise tactics as columns (Reconnaissance → Impact), technique cells inside each column, only techniques present in Red or Blue data (toggle "show full matrix" collapsed by default). Cell color: red gap (no mitigation, or a retest failed) · orange claimed not validated · green validated · blue untested coverage · gray risk accepted; out-of-scope cells only appear with "show full matrix". Cell shows technique ID, short name if known, finding count, residual. Hover → tooltip; click → filters the scorecard. Legend and the "multi-technique findings count in each technique" footnote.
3. **Validation** — scoreboard of every mitigation and every remediated finding: Mitigation · Type · Framework · Techniques · Findings covered · Blue status · Retest result (not re-tested / pass / fail) · Retest date · Owner · Ticket number. **Retest result, Retest date, Owner and Ticket number are inline-editable** (for when Tenable has no value): edited cells get an accent outline, the row a ↺ revert button, and a banner counts pending edits. Toolbar: *Import edits (JSON/CSV)*, *Export edits JSON*, *Export edits CSV*, *Download dashboard with edits* (re-serializes the HTML with `blue_edits` embedded so the next `--prior` picks them up). Edits change what is displayed; scoring is only recomputed by re-running `purple_join.py`, which the banner says. Summary strip: claimed vs validated vs failed counts, `claimed_unproven_residual`, and a "retest queue" list (remediated findings ordered by residual — what Red should re-test first).
4. **Residual risk** — top N findings table; rollup panels by technique, tactic and attack path (horizontal bars, accent fill, gray inherent background so the mitigated share is visible); accepted risk shown separately in muted style.
5. **Data quality** — count per flag, affected rows per flag, export CSV. Empty state: green "all rows joined cleanly".
6. **Changes** (only when prior exists) — new findings, resolved (→ validated), regressed (validated → open / validated_failed), status changes, techniques whose residual moved most, overall index before → after. If weights differ from the prior run, a banner says scores are not directly comparable.

## Embedded state contract

The renderer writes the full `purple_state.json` into

```html
<script id="purple-state" type="application/json">{ ... }</script>
```

`purple_join.py --prior` accepts either that HTML or the JSON. The state includes `meta` (skill version, run number, generated_at, engagement, weights, source descriptions), `findings[]` (normalized, with effective status, residual, flags, linked mitigation IDs), `mitigations[]`, `techniques{}`, `tactics{}`, `attack_paths{}`, `top[]`, `validation{}`, `data_quality{}`, `blue_edits[]` (manual overrides, see data-model §4), and `delta` (when prior existed). Keep this schema stable across versions — it is what makes quarter-over-quarter diffs possible.

## i18n

Every label is in a `I18N` dictionary with `en` and `pt` keys; the toggle swaps `textContent` for all `[data-i18n]` nodes and re-renders tables. Effective status labels PT: open → "Aberto", in_progress → "Em andamento", remediated → "Remediado (não validado)", validated → "Validado", validated_failed → "Reteste falhou", accepted → "Risco aceito". Terms kept in English: residual risk, attack path, technique, tactic, ATT&CK, Red Team, Blue Team, Purple Team, VPR, ACR.
