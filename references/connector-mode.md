# Connector mode — pulling the three entities live from the Tenable MCP

**This is the default and mandatory path for every run.** The Tenable MCP is the base source for Findings, Mitigations and Status; uploaded files are optional overlays merged on top of it, never a replacement. Everything here is read-only. After pulling, write each entity to a JSON file with the canonical columns from `data-model.md` and run `purple_join.py` exactly as documented — connector mode changes where data comes from, not how it is scored.

## 0. Load the tools and verify the connector

1. The Tenable tools are deferred. Call `tool_search` with specific, tool-shaped queries and use the parameter names it returns — never guess them:
   - `"tenable one search findings"` → `tenable_one_search_findings`
   - `"workbenches list vulnerabilities"` → `workbenches_list_vulnerabilities`, `workbenches_get_vulnerability_outputs`
   - `"tenable one search assets"` → `tenable_one_search_assets`
   - `"attack path"` → any attack-path / exposure-graph tool the tenant exposes
2. If none of these load, the connector is not enabled in this chat. Stop, tell the user to enable the Tenable connector, and wait. Do not switch to file mode.
3. Run one cheap probe (`workbenches_list_vulnerabilities` with no parameters) to confirm the tenant answers before starting the paginated pulls. An empty result from `workbenches_get_vulnerability_outputs` for a plugin is a valid healthy-state answer, not an error.

## Tenant-level blockers (do not retry these)

- **CSV export pipeline** (`workbenches_export_workbenches` → status → download) fails with HTTP 406/500 on some tenants. Never use it; paginated list calls are the reliable path.
- **Unfiltered or large High-severity queries** time out or exceed size limits. Pull `severity=critical` first (complete), then `severity=high` in small pages; if High still times out, record the partial coverage in Data quality rather than retrying indefinitely.
- **Plugin output truncation**: `workbenches_get_vulnerability_outputs` truncates trailing fields on large plugins (e.g. 19506). Use outputs only for evidence text on the top findings.
- Filtering `tenable_one_search_findings` by plugin ID works with `"operator": "in"` and string-cast plugin IDs.

## Pull sequence (do it in this order)

1. Assets: `tenable_one_search_assets` with `asset_class=DEVICE`, sorted by `aes:desc`, paginated — build a hostname/IP → `{acr, aes, internet_exposed, tags}` map.
2. Findings: attack paths first, then `tenable_one_search_findings` (Critical/High), then workbenches Critical → High. Dedupe on `plugin_id + asset`.
3. Status: derived from the same finding records (`state` / `tracking.state`), see below.
4. Mitigations: compliance findings, see below.
5. Write `purple-team/inputs/{findings,mitigations,status}.json` and record provenance labels.

## Findings (Red) from Tenable One

Tenable does not tag ordinary vulnerability findings with ATT&CK technique IDs, but attack-path data does. Preferred order:

1. **Attack paths** — if the session has an attack-path dashboard skill (`tenable-attack-path-dashboard`, `tenable-top-assets-attack-paths`) or an MCP call that returns attack-path steps with MITRE technique IDs, use those: each step becomes a finding with `technique_id`, `asset`, `attack_path` (the path name), severity from the step's VPR, `exploitability=exploit_available` (Tenable shows reachable paths, not demonstrated ones — set `demonstrated` only if a Red engagement confirmed it).
2. **Findings inventory** — `tenable_one_search_findings` filtered to Critical/High (paginate; do not request all severities at once on large tenants). Map to techniques with the plugin-family → technique table below; findings you cannot map are kept and flagged `missing_technique`.
3. **Workbenches** — `workbenches_list_vulnerabilities` with `severity=critical` first, then `high` in smaller pages. Enrich the top plugins with `workbenches_get_vulnerability_outputs` only when the output is needed for evidence text (outputs truncate on large plugins such as 19506).

Do **not** use the workbenches CSV export pipeline (`workbenches_export_workbenches` → status → download): it fails with HTTP 406/500 on some tenants. Paginated list calls are the reliable path.

Asset enrichment: `tenable_one_search_assets` with `asset_class=DEVICE` gives `acr` and internet exposure per asset — join by hostname/IP to populate `acr` and `internet_exposed`.

Canonical `finding_id` for MCP-sourced findings: `TEN-<plugin_id>-<asset_uuid or hostname>` (attack-path steps: `AP-<path_id>-<step_n>`). Keep it stable across runs — the delta tab and any ticketing overlay join on it. Populate `red_evidence` with the plugin name plus a short excerpt of the plugin output when available, `date_found` from `first_seen`, and `severity` from VPR (fallback CVSS).

### Plugin-family → technique defaults (coarse; say so in Data quality)

| Tenable signal | Technique |
|---|---|
| Kerberoastable SPN / weak Kerberos | T1558.003 |
| AS-REP roasting | T1558.004 |
| SMB signing not required / NTLM relay | T1557.001 |
| Print Spooler / PrintNightmare | T1068 |
| ADCS misconfiguration (ESC1–8) | T1649 |
| Unconstrained delegation | T1550 |
| Weak / default credentials, credential in cleartext | T1078, T1552.001 |
| Remote code execution (RCE) in exposed service | T1190 (internet-facing) / T1210 (internal) |
| RDP / SSH exposed with weak auth | T1021.001 / T1021.004 |
| Local privilege escalation CVE | T1068 |
| Missing EDR / AV disabled | T1562.001 |
| LSASS protection off / credential dumping possible | T1003.001 |
| DCSync rights on non-admin | T1003.006 |
| Cleartext protocols (Telnet, FTP, HTTP auth) | T1040 |

Mark every finding mapped this way with `mapping_source=plugin_default` so the dashboard can distinguish Red-confirmed techniques from inferred ones.

## Mitigations (Blue)

- **Tenable compliance findings** (CIS/PCI audits via `tenable_one_search_findings` with compliance filters, or workbenches compliance plugins): each rule becomes a mitigation with `type=compliance_rule`, `framework` = benchmark and rule ID, `status=remediated` if the check passes, `open` if it fails. Map rule → technique with the user's own mapping if they have one; otherwise use the defaults table above in reverse and flag as coarse.
- **GRC / compliance connector**: export controls with their technique mapping (many GRC tools carry ATT&CK mappings for NIST 800-53 / CIS controls).
- If no Blue source exists, proceed without mitigations and let the scorecard say "no mapped mitigation" — do not invent controls.

## Status — from Tenable finding state (base), ticketing as overlay

Every MCP-sourced finding gets a status row derived from its Tenable state:

| Tenable state (`state` / `tracking.state`) | Effective status | Note |
|---|---|---|
| New, Active | `open` | Vulnerability currently detected |
| Fixed | `remediated` | Scanner no longer sees it — a Blue claim, not a Red retest; stays at the remediated weight until Red validates |
| Resurfaced | `validated_failed` | Was fixed and came back — evidence that the mitigation did not hold |
| Risk accepted / recast (if the tenant exposes it) | `accepted` | Listed separately, excluded from residual |

Set `updated_date` from `last_seen` / `last_fixed`, `notes` to the raw Tenable state, and `ticket_id` empty. Only a Red retest (from an overlay or from the user's confirmation) may promote a finding to `validated`.

### Ticketing overlay (Jira, ServiceNow, etc.) — optional

If a ticketing connector is present or the user uploads a ticket export, merge it on top of the Tenable-derived status:
- Query the project/board the user names; pull key, summary, status, resolution, assignee, updated, and any custom "finding ID" or "retest result" fields.
- The finding ID is usually in a custom field or the summary prefix (`[TEN-19506-host01] ...`); extract it with the pattern the user confirms. Tickets with no extractable finding ID are written to the status file anyway so they appear as `unknown_finding` in Data quality — the user can then fix the ticket, which is the point.
- Map ticket statuses with the vocabulary in `data-model.md`; if the workflow uses unusual names, pass `--status-map` rather than editing the script.
- Merge rule: for the same `finding_id`, latest `updated_date` wins, except that `retest_fail` and Tenable `Resurfaced` always win over a closed ticket (evidence beats claim).

## Recording provenance

Always pass `--source-findings`, `--source-mitigations` and `--source-status` (free-text labels, e.g. `"Tenable MCP (live, 2026-09-11) + pentest overlay Q3"`). The dashboard header shows them so a reader knows whether the Red column came from a real engagement or from inferred attack paths, and which parts were live MCP data versus overlay.
