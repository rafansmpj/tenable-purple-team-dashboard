# Tenable Purple Team Dashboard

A Claude skill that joins **Red Team** attack findings (pentest / attack-path results tagged with MITRE ATT&CK techniques) against **Blue Team** remediation and compliance evidence, and answers the question nobody can answer from two silos:

> *Given what Blue actually fixed, what can Red still do?*

All base data is pulled **live from the Tenable MCP** (Tenable One / Vulnerability Management / Identity Exposure / ASM). Uploaded files are optional overlays only. The output is a single standalone HTML dashboard that is refreshed in place every engagement, with a run-over-run delta.

![Palette: dark UI, accent #E7FF00, Red/Blue/Purple/Orange/Green semantic colors](https://img.shields.io/badge/Claude_Skill-Tenable-E7FF00?labelColor=44494B)

---

## What you get

Every run produces `tenable-purple-team-dashboard.html` (inline CSS/JS, no CDN, opens from disk) plus `purple_state.json`:

| Tab | What it shows |
|---|---|
| **Scorecard** | Each Red finding next to the Blue mitigation(s) mapped to it, with effective status (open → in progress → remediated → validated), residual vs. inherent risk, filters and CSV export. Row click opens a detail drawer. |
| **ATT&CK heatmap** | Enterprise tactics × techniques. Red = Red demonstrated it and nothing blocks it · Orange = mitigation claimed, not validated · Green = validated block · Blue = Blue control exists, Red never tested it · Gray = risk accepted. |
| **Validation** | Retest queue (what Red should re-test first) and the Blue mitigations scoreboard — **Retest result, Retest date, Owner and Ticket number are editable inline**, exportable/importable as JSON or CSV. |
| **Residual risk** | Top-N residual findings; rollups by technique, tactic and attack path; accepted risk listed separately. |
| **Data quality** | Unmapped findings, orphan mitigations, unknown statuses, coarse mappings — never silently dropped. |
| **Changes** | New / resolved / regressed / changed findings and technique movements vs. the previous run. |

KPI strip: residual index (0–100), findings by status, **validation rate** (validated ÷ claimed — the single most useful Purple metric), technique coverage, data-quality count. PT-BR / EN toggle.

---

## How it works

```
Tenable MCP ──► findings (Critical/High) ─┐
            ──► asset ACR / exposure ─────┤
            ──► finding state ────────────┤        purple_join.py        render_dashboard.py
            ──► compliance / IoE rules ───┼──► normalize · join · score ──► purple_state.json ──► dashboard.html
optional overlays (CSV/XLSX/JSON) ────────┤          ▲                          (embedded state)
  pentest evidence · tickets · GRC maps ──┤          │
  blue_edits.json / .csv ─────────────────┘          └── --prior (previous HTML or JSON) for the delta
```

1. **Pull** — the skill loads the Tenable MCP tools, pulls assets (ACR/AES/exposure), findings (Critical first, then High in small pages), derives status from the Tenable finding state (`Active → open`, `Fixed → remediated`, `Resurfaced → validated_failed`) and builds Blue controls from compliance results or Identity Exposure IoE rules. No connector → the skill stops and asks for it; it never falls back to sample data for a real engagement.
2. **Join** — `scripts/purple_join.py` matches Status → Finding by `finding_id` and Mitigation → Finding by explicit `finding_id`, else by shared ATT&CK `technique_id`. Column names are matched by alias (`references/data-model.md`).
3. **Score** — residual = unmitigated finding × severity × exploitability × exposure × asset criticality, rolled up by technique / tactic / attack path and normalized to a 0–100 index. A closed ticket that was never re-tested keeps **40 %** of its risk by default; only a Red-validated retest drops it to zero (`references/residual-risk.md`).
4. **Render** — `scripts/render_dashboard.py` writes the HTML with the full state embedded, so the previous dashboard alone is enough for the next delta.

---

## Requirements

- Claude with the **Tenable connector (MCP)** enabled — Claude.ai, Claude Desktop / Cowork, or Claude Code.
- Python 3.10+ for the scripts (`openpyxl` only if you feed XLSX overlays).
- Read-only: nothing is written back to Tenable, ticketing or GRC systems.

## Install

**Claude Desktop / Cowork / Claude.ai** — upload the skill folder (or the `.zip`) under *Skills*, or install it from the Tenable CyberAgents Exchange.

**Claude Code**
```bash
git clone https://github.com/rafansmpj/tenable-purple-team-dashboard.git ~/.claude/skills/tenable-purple-team-dashboard
```

## Usage

Just ask, in English or Portuguese:

```
/tenable-purple-team-dashboard
build a purple team dashboard for the Q3 pentest
red vs blue scorecard — what can Red still do?
risco residual e heatmap ATT&CK do ambiente
```

Optional attachments in the same message: a pentest report (CSV/XLSX/JSON with `finding_id`, `technique_id`, evidence), a Jira/ServiceNow export, a GRC control mapping, or a `blue_edits` file. Upload the previous `tenable-purple-team-dashboard.html` or `purple_state.json` to get the **Changes** tab.

### Running the scripts by hand

```bash
python3 scripts/purple_join.py \
  --findings inputs/findings.json --mitigations inputs/mitigations.json --status inputs/status.json \
  --prior purple-team/tenable-purple-team-dashboard.html \   # omit on run 1
  --overrides purple-team/blue_edits.csv \                   # manual owner / retest date / ticket edits
  --engagement "Q3 2026 internal pentest" --top 15 --out purple_state.json

python3 scripts/render_dashboard.py --state purple_state.json --out tenable-purple-team-dashboard.html --lang pt
```

---

## Manual Blue edits (owner · retest date · ticket)

Tenable does not know who owns a mitigation, which ticket tracks it, or when Red re-tested it. Two ways to add that:

- **In the dashboard** — Validation tab → type into the cells → *Export edits JSON / CSV* or *Download dashboard with edits*.
- **In a file** — maintain `blue_edits.csv` and pass it with `--overrides` (template in `assets/sample_data/blue_edits.csv`):

```csv
target_id,owner,retest_date,ticket_number,retest_result,note
IOE-PRIVILEGED-ACCOUNT-NOT-PROTECTED-AGAINST-DELEGATION,AD Team - Ana,2026-09-10,SEC-4471,fail,retested by Red
TEN-53C64C7B-786C2361,Infra - Bruno,2026-09-08,CHG-20991,pass,VMware Tools upgraded and re-tested
```

`target_id` is a mitigation ID or a finding ID. `retest_result = pass` promotes the linked finding to **validated** (residual 0); `fail` → **validated_failed**. Edits embedded in the previous dashboard are carried forward automatically; the file is applied on top (later wins). Unknown IDs are flagged in Data quality, never dropped.

---

## Interpretation rules

| Signal | Meaning |
|---|---|
| `remediated` | Blue says fixed (or the scanner no longer sees it). Not proof the attack is blocked — still scores at 40 %. |
| `validated` | Red re-tested and the attack was blocked. Residual 0. |
| `validated_failed` | Re-test showed the attack still works, or Tenable marked the finding **Resurfaced**. Counts as open with a red flag. Evidence beats claim. |
| `accepted` | Formal risk acceptance. Excluded from residual, listed separately — still a Red capability, just a governed one. |
| Validation rate | validated ÷ (remediated + validated). How much of Blue's claimed progress has actually been proven. |

Technique IDs inferred from plugin families (`mapping_source = plugin_default`) are shown as inferred, not Red-confirmed; a pentest overlay is what turns them into demonstrated techniques.

---

## Repository layout

```
SKILL.md                         skill definition and workflow
README.md
scripts/
  purple_join.py                 load · normalize · join · score · diff  →  purple_state.json
  render_dashboard.py            purple_state.json  →  standalone HTML (embedded state)
references/
  connector-mode.md              MANDATORY Tenable MCP pull procedure, tenant blockers, state mapping
  data-model.md                  entity schemas, aliases, status vocabulary, join rules, blue_edits schema
  residual-risk.md               formula, default weights, overrides
  dashboard-spec.md              tabs, components, palette, i18n, embedded-state contract
assets/sample_data/              findings.csv · mitigations.csv · status.csv · blue_edits.csv templates
```

## Known Tenable MCP behaviors handled

- The workbenches CSV export pipeline fails (HTTP 406/500) on some tenants — paginated list calls are used instead.
- Unfiltered High-severity queries time out — Critical is pulled first, then High in 100-row pages; partial coverage is reported in Data quality.
- Plugin output is truncated on large plugins (e.g. 19506) — used only for evidence text on top findings.

## Contributing

Issues and PRs welcome — especially better plugin-family → ATT&CK mappings (`references/connector-mode.md`) and GRC control mappings. Keep `purple_state.json` schema changes backward-compatible: quarter-over-quarter diffs depend on it.

## Author

Rafael Mello — Senior Security Engenieer , Tenable · [@rafansmpj](https://github.com/rafansmpj)
MCSAc (Master Certified Solution Architect)


## License

MIT
