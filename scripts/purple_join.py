#!/usr/bin/env python3
"""purple_join.py — normalize, join and score Red findings vs Blue mitigations vs Status.

Usage:
  python3 purple_join.py --findings f.csv --mitigations m.csv --status s.csv \
      [--prior previous_state.json|previous_dashboard.html] [--engagement "Q3 2026"] \
      [--top 15] [--weights w.json] [--status-map extra.json] \
      [--source-findings "..."] [--source-mitigations "..."] [--source-status "..."] \
      --out purple_state.json

Inputs: CSV / XLSX / JSON. Only --findings is mandatory; missing entities are tolerated and flagged.
Read-only: never writes anywhere except --out (and <out>.previous.json when a prior exists).
"""
import argparse, csv, json, os, re, sys, copy
from datetime import datetime, timezone

SKILL_VERSION = "1.0.0"
TECH_RE = re.compile(r"^T\d{4}(\.\d{3})?$")
SPLIT_RE = re.compile(r"[;,|\n]+")

# ---------------------------------------------------------------- aliases
ALIASES = {
    "findings": {
        "finding_id": ["finding_id", "id", "finding", "ref", "issue_id", "vuln_id", "findingid"],
        "technique_id": ["technique_id", "technique", "techniques", "attack_technique", "mitre", "mitre_id", "ttp", "att&ck", "attck", "technique_ids"],
        "title": ["title", "name", "summary", "description"],
        "severity": ["severity", "sev", "risk", "rating", "cvss", "vpr"],
        "asset": ["asset", "target", "host", "hostname", "target_asset", "system"],
        "attack_path": ["attack_path", "path", "chain", "scenario", "kill_chain", "attackpath"],
        "tactic": ["tactic", "mitre_tactic", "phase"],
        "exploitability": ["exploitability", "exploit", "exploited", "demonstrated"],
        "internet_exposed": ["internet_exposed", "external", "internet_facing", "public", "internetfacing"],
        "acr": ["acr", "asset_criticality", "criticality"],
        "red_evidence": ["red_evidence", "evidence", "proof", "poc"],
        "date_found": ["date_found", "found", "discovered", "date"],
        "status": ["status", "state"],
        "mapping_source": ["mapping_source"],
    },
    "mitigations": {
        "mitigation_id": ["mitigation_id", "id", "control_id", "rule_id", "ticket", "change", "mitigationid"],
        "name": ["name", "control", "rule", "title", "description"],
        "type": ["type", "category", "kind"],
        "technique_ids": ["technique_ids", "technique", "techniques", "mitre", "blocks", "covers", "technique_id"],
        "finding_ids": ["finding_ids", "findings", "finding", "addresses", "fixes", "finding_id"],
        "status": ["status", "state", "implementation"],
        "validation_status": ["validation_status", "validated", "retest", "retest_result", "verified"],
        "validated_date": ["validated_date", "retest_date", "verified_date"],
        "owner": ["owner", "assignee", "team"],
        "ticket_id": ["ticket_id", "ticket_number", "ticketnumber", "jira", "incident", "change_ticket"],
        "evidence": ["evidence", "proof", "reference", "link"],
        "framework": ["framework", "standard", "source"],
    },
    "status": {
        "finding_id": ["finding_id", "id", "finding", "key", "issue", "ref", "findingid"],
        "status": ["status", "state", "resolution", "workflow_status"],
        "validation_status": ["validation_status", "retest", "retest_result", "verified", "validated"],
        "validated_date": ["validated_date", "retest_date"],
        "ticket_id": ["ticket_id", "ticket", "jira", "incident"],
        "owner": ["owner", "assignee"],
        "updated_date": ["updated_date", "updated", "last_updated", "modified"],
        "notes": ["notes", "comment", "resolution_notes"],
    },
    "overrides": {
        "target_id": ["target_id", "id", "mitigation_id", "finding_id", "ref"],
        "owner": ["owner", "assignee", "team"],
        "validated_date": ["validated_date", "retest_date", "data_do_reteste", "data_retest"],
        "ticket_id": ["ticket_id", "ticket_number", "ticket", "jira", "incident"],
        "validation_status": ["validation_status", "retest", "retest_result", "validation"],
        "note": ["note", "notes", "comment"],
        "edited_at": ["edited_at", "updated", "updated_date", "date"],
        "edited_by": ["edited_by", "editor", "user"],
    },
}

STATUS_MAP = [  # (substring, effective) — order matters: more specific first
    ("retest fail", "validated_failed"), ("retest failed", "validated_failed"), ("validation failed", "validated_failed"),
    ("still exploitable", "validated_failed"), ("reopened after retest", "validated_failed"),
    ("retest pass", "validated"), ("closed-verified", "validated"), ("confirmed fixed", "validated"),
    ("validated", "validated"), ("verified", "validated"), ("retested", "validated"),
    ("risk accepted", "accepted"), ("accepted", "accepted"), ("won't fix", "accepted"), ("wontfix", "accepted"),
    ("exception", "accepted"), ("waived", "accepted"), ("deferred", "accepted"),
    ("in progress", "in_progress"), ("in-progress", "in_progress"), ("inprogress", "in_progress"), ("working", "in_progress"),
    ("assigned", "in_progress"), ("doing", "in_progress"), ("scheduled", "in_progress"), ("planned", "in_progress"),
    ("mitigating", "in_progress"), ("awaiting patch", "in_progress"),
    ("remediated", "remediated"), ("fixed", "remediated"), ("resolved", "remediated"), ("closed", "remediated"),
    ("done", "remediated"), ("complete", "remediated"), ("patched", "remediated"), ("mitigated", "remediated"),
    ("implemented", "remediated"), ("deployed", "remediated"), ("pass", "remediated"),
    ("reopened", "open"), ("open", "open"), ("new", "open"), ("to do", "open"), ("todo", "open"), ("backlog", "open"),
    ("reported", "open"), ("confirmed", "open"), ("unresolved", "open"), ("pending", "open"), ("fail", "open"),
]
EFFECTIVE = ["open", "in_progress", "remediated", "validated", "validated_failed", "accepted"]

DEFAULT_WEIGHTS = {
    "severity": {"critical": 10, "high": 7, "medium": 4, "low": 1, "info": 0},
    "exploitability": {"demonstrated": 1.0, "exploit_available": 0.8, "theoretical": 0.5},
    "exposure": {"internal": 1.0, "internet": 1.3, "acr_base": 0.6, "acr_slope": 0.08},
    "mitigation": {"open": 1.0, "in_progress": 0.8, "remediated": 0.4, "validated": 0.0, "validated_failed": 1.0, "accepted": 0.0},
}

TACTICS = ["Reconnaissance", "Resource Development", "Initial Access", "Execution", "Persistence", "Privilege Escalation",
           "Defense Evasion", "Credential Access", "Discovery", "Lateral Movement", "Collection", "Command and Control",
           "Exfiltration", "Impact"]

# Compact Enterprise ATT&CK technique → (name, primary tactic). Extend as needed; unknowns map to "Unknown".
TECH_TABLE = {
    "T1595": ("Active Scanning", "Reconnaissance"), "T1589": ("Gather Victim Identity Information", "Reconnaissance"),
    "T1590": ("Gather Victim Network Information", "Reconnaissance"), "T1583": ("Acquire Infrastructure", "Resource Development"),
    "T1588": ("Obtain Capabilities", "Resource Development"),
    "T1190": ("Exploit Public-Facing Application", "Initial Access"), "T1133": ("External Remote Services", "Initial Access"),
    "T1566": ("Phishing", "Initial Access"), "T1078": ("Valid Accounts", "Initial Access"), "T1199": ("Trusted Relationship", "Initial Access"),
    "T1195": ("Supply Chain Compromise", "Initial Access"), "T1091": ("Replication Through Removable Media", "Initial Access"),
    "T1059": ("Command and Scripting Interpreter", "Execution"), "T1203": ("Exploitation for Client Execution", "Execution"),
    "T1047": ("Windows Management Instrumentation", "Execution"), "T1053": ("Scheduled Task/Job", "Execution"),
    "T1569": ("System Services", "Execution"), "T1204": ("User Execution", "Execution"),
    "T1098": ("Account Manipulation", "Persistence"), "T1136": ("Create Account", "Persistence"), "T1543": ("Create or Modify System Process", "Persistence"),
    "T1547": ("Boot or Logon Autostart Execution", "Persistence"), "T1505": ("Server Software Component", "Persistence"),
    "T1068": ("Exploitation for Privilege Escalation", "Privilege Escalation"), "T1548": ("Abuse Elevation Control Mechanism", "Privilege Escalation"),
    "T1134": ("Access Token Manipulation", "Privilege Escalation"), "T1484": ("Domain or Tenant Policy Modification", "Privilege Escalation"),
    "T1562": ("Impair Defenses", "Defense Evasion"), "T1070": ("Indicator Removal", "Defense Evasion"), "T1036": ("Masquerading", "Defense Evasion"),
    "T1027": ("Obfuscated Files or Information", "Defense Evasion"), "T1218": ("System Binary Proxy Execution", "Defense Evasion"),
    "T1550": ("Use Alternate Authentication Material", "Defense Evasion"), "T1055": ("Process Injection", "Defense Evasion"),
    "T1003": ("OS Credential Dumping", "Credential Access"), "T1110": ("Brute Force", "Credential Access"), "T1558": ("Steal or Forge Kerberos Tickets", "Credential Access"),
    "T1557": ("Adversary-in-the-Middle", "Credential Access"), "T1552": ("Unsecured Credentials", "Credential Access"), "T1040": ("Network Sniffing", "Credential Access"),
    "T1649": ("Steal or Forge Authentication Certificates", "Credential Access"), "T1555": ("Credentials from Password Stores", "Credential Access"),
    "T1187": ("Forced Authentication", "Credential Access"), "T1212": ("Exploitation for Credential Access", "Credential Access"),
    "T1087": ("Account Discovery", "Discovery"), "T1046": ("Network Service Discovery", "Discovery"), "T1018": ("Remote System Discovery", "Discovery"),
    "T1482": ("Domain Trust Discovery", "Discovery"), "T1069": ("Permission Groups Discovery", "Discovery"), "T1083": ("File and Directory Discovery", "Discovery"),
    "T1021": ("Remote Services", "Lateral Movement"), "T1210": ("Exploitation of Remote Services", "Lateral Movement"),
    "T1570": ("Lateral Tool Transfer", "Lateral Movement"), "T1080": ("Taint Shared Content", "Lateral Movement"),
    "T1005": ("Data from Local System", "Collection"), "T1039": ("Data from Network Shared Drive", "Collection"), "T1114": ("Email Collection", "Collection"),
    "T1560": ("Archive Collected Data", "Collection"), "T1213": ("Data from Information Repositories", "Collection"),
    "T1071": ("Application Layer Protocol", "Command and Control"), "T1105": ("Ingress Tool Transfer", "Command and Control"),
    "T1572": ("Protocol Tunneling", "Command and Control"), "T1090": ("Proxy", "Command and Control"), "T1219": ("Remote Access Software", "Command and Control"),
    "T1041": ("Exfiltration Over C2 Channel", "Exfiltration"), "T1048": ("Exfiltration Over Alternative Protocol", "Exfiltration"),
    "T1567": ("Exfiltration Over Web Service", "Exfiltration"),
    "T1486": ("Data Encrypted for Impact", "Impact"), "T1485": ("Data Destruction", "Impact"), "T1489": ("Service Stop", "Impact"),
    "T1490": ("Inhibit System Recovery", "Impact"), "T1498": ("Network Denial of Service", "Impact"), "T1531": ("Account Access Removal", "Impact"),
}

# ---------------------------------------------------------------- loading
def norm_key(s):
    return re.sub(r"[\s_\-]+", "", str(s).strip().lower())

def load_rows(path, entity):
    """Return list of dict rows from csv/xlsx/json. XLSX: sheet named like entity if present else first."""
    if not path:
        return []
    if not os.path.exists(path):
        sys.exit(f"ERROR: file not found: {path}")
    ext = os.path.splitext(path)[1].lower()
    if ext in (".csv", ".tsv", ".txt"):
        with open(path, newline="", encoding="utf-8-sig") as f:
            sample = f.read(4096); f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            except csv.Error:
                dialect = csv.excel
            return [dict(r) for r in csv.DictReader(f, dialect=dialect)]
    if ext in (".xlsx", ".xlsm"):
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        sheet = None
        for ws in wb.worksheets:
            if norm_key(ws.title).startswith(entity[:6]):
                sheet = ws; break
        sheet = sheet or wb.worksheets[0]
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [str(h) if h is not None else f"col{i}" for i, h in enumerate(rows[0])]
        return [{headers[i]: ("" if v is None else v) for i, v in enumerate(r)} for r in rows[1:] if any(v not in (None, "") for v in r)]
    if ext == ".json":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for k in (entity, entity.rstrip("s"), "rows", "data", "items", "blue_edits", "edits"):
                if k in data and isinstance(data[k], list):
                    return data[k]
            return []
        return data
    sys.exit(f"ERROR: unsupported input format: {path}")

def canonicalize(rows, entity):
    aliases = ALIASES[entity]
    out = []
    for r in rows:
        nk = {norm_key(k): (v if v is not None else "") for k, v in r.items() if k is not None}
        c = {}
        used = set()
        for canon, al in aliases.items():
            for a in al:
                a2 = norm_key(a)
                if a2 in nk and a2 not in used and str(nk[a2]).strip() != "":
                    c[canon] = str(nk[a2]).strip(); used.add(a2); break
        c["_extra"] = {k: str(v) for k, v in r.items() if k is not None and norm_key(k) not in used and str(v).strip() != ""}
        out.append(c)
    return out

# ---------------------------------------------------------------- normalizers
def split_ids(v):
    return [x.strip().upper() for x in SPLIT_RE.split(str(v or "")) if x.strip()]

def norm_technique(t):
    t = t.strip().upper().replace(" ", "")
    return t if TECH_RE.match(t) else None

def parent_tech(t):
    return t.split(".")[0]

def norm_status(raw, extra_map):
    s = str(raw or "").strip().lower()
    if not s:
        return None, None
    for k, v in extra_map.items():
        if k.lower() in s:
            return v, None
    for sub, eff in STATUS_MAP:
        if sub in s:
            return eff, None
    return "open", f"unknown_status:{raw}"

def norm_validation(raw):
    s = str(raw or "").strip().lower()
    if not s:
        return "not_retested"
    if any(w in s for w in ("fail", "bypass", "still exploitable", "not blocked", "reproduc")):
        return "retest_fail"
    if any(w in s for w in ("pass", "verified", "blocked", "validated", "ok", "true", "yes", "confirmed")):
        return "retest_pass"
    return "not_retested"

def norm_severity(raw, w):
    s = str(raw or "").strip().lower()
    if not s:
        return "medium", w["severity"]["medium"]
    try:
        n = float(s)
        if n >= 9: return "critical", n
        if n >= 7: return "high", n
        if n >= 4: return "medium", n
        if n > 0: return "low", n
        return "info", 0.0
    except ValueError:
        pass
    for k in ("critical", "high", "medium", "low", "info"):
        if k in s or (k == "critical" and "crit" in s) or (k == "medium" and "moderate" in s):
            return k, float(w["severity"][k])
    return "medium", float(w["severity"]["medium"])

def norm_exploit(raw):
    s = str(raw or "").strip().lower()
    if not s: return "demonstrated"
    if any(w in s for w in ("demonstr", "exploited", "confirmed", "proven", "yes", "true")): return "demonstrated"
    if any(w in s for w in ("available", "public", "poc", "weaponized")): return "exploit_available"
    if any(w in s for w in ("theor", "potential", "no", "false", "unproven")): return "theoretical"
    return "demonstrated"

def norm_bool(raw):
    return str(raw or "").strip().lower() in ("1", "true", "yes", "y", "external", "internet", "public", "sim")

def norm_acr(raw):
    s = str(raw or "").strip().lower()
    if not s: return None
    try:
        n = float(s); return max(1.0, min(10.0, n))
    except ValueError:
        return {"critical": 9.0, "high": 7.0, "medium": 5.0, "low": 2.0}.get(s)

def parse_date(raw):
    s = str(raw or "").strip()
    if not s: return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(s[:len(fmt) + 6] if "%z" in fmt else s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s

# ---------------------------------------------------------------- prior state
def load_prior(path):
    if not path: return None
    if not os.path.exists(path): sys.exit(f"ERROR: prior not found: {path}")
    text = open(path, encoding="utf-8").read()
    if path.lower().endswith(".html") or "<script id=\"purple-state\"" in text:
        m = re.search(r'<script id="purple-state" type="application/json">(.*?)</script>', text, re.S)
        if not m: sys.exit("ERROR: prior HTML has no embedded purple-state block")
        return json.loads(m.group(1))
    return json.loads(text)

# ---------------------------------------------------------------- main compute
def compute(findings_raw, mitig_raw, status_raw, weights, extra_status_map, top_n, meta):
    dq = {}  # flag -> list of {entity,id,detail}
    def flag(name, entity, ident, detail=""):
        dq.setdefault(name, []).append({"entity": entity, "id": ident, "detail": detail})

    # --- findings
    findings = {}
    for r in findings_raw:
        fid = r.get("finding_id")
        if not fid:
            flag("missing_finding_id", "finding", "(row)", json.dumps(r.get("_extra", {}))[:120]); continue
        if fid in findings:
            flag("duplicate_finding_id", "finding", fid, "last row wins")
        techs, bad = [], []
        for t in split_ids(r.get("technique_id")):
            nt = norm_technique(t)
            (techs if nt else bad).append(nt or t)
        for b in bad:
            flag(f"invalid_technique:{b}", "finding", fid)
        if not techs and not bad:
            flag("missing_technique", "finding", fid)
        sev_label, sev_w = norm_severity(r.get("severity"), weights)
        f = {
            "finding_id": fid, "title": r.get("title", ""), "techniques": sorted(set(techs)), "invalid_techniques": bad,
            "severity": sev_label, "severity_w": sev_w, "asset": r.get("asset", ""), "attack_path": r.get("attack_path") or "(unassigned)",
            "tactic": r.get("tactic", ""), "exploitability": norm_exploit(r.get("exploitability")),
            "internet_exposed": norm_bool(r.get("internet_exposed")), "acr": norm_acr(r.get("acr")),
            "red_evidence": r.get("red_evidence", ""), "date_found": parse_date(r.get("date_found")),
            "own_status": r.get("status", ""), "mapping_source": r.get("mapping_source", "red"), "extra": r.get("_extra", {}),
            "status_rows": [], "mitigations": [], "flags": [],
        }
        if not techs: f["flags"].append("missing_technique" if not bad else "invalid_technique")
        findings[fid] = f

    # --- status rows
    for r in status_raw:
        fid = r.get("finding_id")
        if not fid:
            flag("missing_finding_id", "status", "(row)", json.dumps(r.get("_extra", {}))[:120]); continue
        eff, uflag = norm_status(r.get("status"), extra_status_map)
        row = {"status": eff or "open", "raw_status": r.get("status", ""), "validation": norm_validation(r.get("validation_status")),
               "validated_date": parse_date(r.get("validated_date")), "ticket_id": r.get("ticket_id", ""), "owner": r.get("owner", ""),
               "updated_date": parse_date(r.get("updated_date")), "notes": r.get("notes", "")}
        if uflag: flag(uflag, "status", fid)
        if fid in findings:
            findings[fid]["status_rows"].append(row)
        else:
            flag(f"unknown_finding:{fid}", "status", fid, r.get("status", ""))

    # --- mitigations
    tech_index = {}
    for f in findings.values():
        for t in f["techniques"]:
            tech_index.setdefault(t, []).append(f["finding_id"])
            tech_index.setdefault(parent_tech(t), []).append(f["finding_id"]) if "." in t else None
    mitigations = {}
    for r in mitig_raw:
        mid = r.get("mitigation_id")
        if not mid:
            flag("missing_mitigation_id", "mitigation", "(row)", json.dumps(r.get("_extra", {}))[:120]); continue
        techs = []
        for t in split_ids(r.get("technique_ids")):
            nt = norm_technique(t)
            if nt: techs.append(nt)
            else: flag(f"invalid_technique:{t}", "mitigation", mid)
        eff, uflag = norm_status(r.get("status"), extra_status_map)
        if uflag: flag(uflag, "mitigation", mid)
        m = {"mitigation_id": mid, "name": r.get("name", ""), "type": (r.get("type") or "control").lower(), "framework": r.get("framework", ""),
             "techniques": sorted(set(techs)), "explicit_findings": split_ids(r.get("finding_ids")), "status": eff or "open",
             "raw_status": r.get("status", ""), "validation": norm_validation(r.get("validation_status")),
             "validated_date": parse_date(r.get("validated_date")), "owner": r.get("owner", ""), "ticket_id": r.get("ticket_id", ""), "evidence": r.get("evidence", ""),
             "linked_findings": [], "link_type": None, "extra": r.get("_extra", {}), "flags": []}
        linked = [fid for fid in m["explicit_findings"] if fid in findings]
        missing = [fid for fid in m["explicit_findings"] if fid not in findings]
        for fid in missing: flag(f"unknown_finding:{fid}", "mitigation", mid)
        if linked:
            m["link_type"] = "finding"
        else:
            s = set()
            for t in techs:
                s.update(tech_index.get(t, []))
            linked = sorted(s)
            if linked:
                m["link_type"] = "technique"
                if len(linked) > 15:
                    m["flags"].append("coarse_mapping"); flag("coarse_mapping", "mitigation", mid, f"{len(linked)} findings via technique")
        if not linked:
            m["flags"].append("orphan_mitigation"); flag("orphan_mitigation", "mitigation", mid, "maps to no finding/technique in Red data")
        m["linked_findings"] = linked
        for fid in linked:
            findings[fid]["mitigations"].append(mid)
        mitigations[mid] = m

    # --- effective status + scoring
    W = weights
    for f in findings.values():
        rows = sorted(f["status_rows"], key=lambda x: x["updated_date"] or "")
        latest = rows[-1] if rows else None
        if not latest:
            own, uflag = norm_status(f["own_status"], extra_status_map)
            if uflag: flag(uflag, "finding", f["finding_id"])
            f["flags"].append("no_status_row"); flag("no_status_row", "finding", f["finding_id"], f"defaulted to {own or 'open'}")
            base = own or "open"; val = "not_retested"; owner = ""; ticket = ""; vdate = None
        else:
            base = latest["status"]; val = latest["validation"]; owner = latest["owner"]; ticket = latest["ticket_id"]; vdate = latest["validated_date"]
        mits = [mitigations[m] for m in f["mitigations"]]
        retests = [val] + [m["validation"] for m in mits]
        mit_claim = any(m["status"] in ("remediated", "validated") for m in mits)
        if "retest_fail" in retests:
            eff = "validated_failed"
            if base in ("remediated", "validated"): f["flags"].append("conflict_claim_vs_retest"); flag("conflict_claim_vs_retest", "finding", f["finding_id"])
        elif "retest_pass" in retests or base == "validated":
            eff = "validated"
        elif base == "accepted":
            eff = "accepted"
        elif base == "remediated" or (mit_claim and base not in ("in_progress",)):
            eff = "remediated"
        elif base == "in_progress":
            eff = "in_progress"
        else:
            eff = "open"
        exp_w = W["exposure"]["internet"] if f["internet_exposed"] else W["exposure"]["internal"]
        if f["acr"] is not None:
            exp_w *= W["exposure"]["acr_base"] + W["exposure"]["acr_slope"] * f["acr"]
        inherent = f["severity_w"] * W["exploitability"][f["exploitability"]] * exp_w
        f.update({"effective_status": eff, "base_status": base, "validation": val, "validated_date": vdate, "owner": owner, "ticket_id": ticket,
                  "inherent": round(inherent, 2), "residual": round(inherent * W["mitigation"][eff], 2) if eff != "accepted" else 0.0,
                  "accepted_risk": round(inherent, 2) if eff == "accepted" else 0.0,
                  "tactics": sorted({(TECH_TABLE.get(parent_tech(t), ("", "Unknown"))[1]) for t in f["techniques"]} or {f["tactic"] or "Unknown"})})

    # --- rollups
    techniques = {}
    all_techs = set()
    for f in findings.values(): all_techs.update(parent_tech(t) for t in f["techniques"]); all_techs.update(f["techniques"])
    for m in mitigations.values(): all_techs.update(m["techniques"]); all_techs.update(parent_tech(t) for t in m["techniques"])
    for t in sorted(all_techs):
        fids = [f for f in findings.values() if t in f["techniques"] or (("." not in t) and any(parent_tech(x) == t for x in f["techniques"]))]
        mids = [m for m in mitigations.values() if t in m["techniques"] or (("." not in t) and any(parent_tech(x) == t for x in m["techniques"]))]
        statuses = [f["effective_status"] for f in fids]
        red = bool(fids)
        claimed = any(s in ("remediated", "validated") for s in statuses) or any(m["status"] in ("remediated", "validated") for m in mids)
        validated = ("validated" in statuses) and all(s in ("validated", "accepted") for s in statuses)
        partially_validated = ("validated" in statuses) and not validated
        if not red and mids: cov = "untested_coverage"
        elif not red: cov = "out_of_scope"
        elif "validated_failed" in statuses: cov = "gap"          # a failed retest beats any claim
        elif validated: cov = "validated"
        elif all(s == "accepted" for s in statuses): cov = "accepted"
        elif claimed or partially_validated: cov = "claimed"
        else: cov = "gap"
        name, tactic = TECH_TABLE.get(parent_tech(t), ("", "Unknown"))
        techniques[t] = {"technique": t, "parent": parent_tech(t), "name": name, "tactic": tactic, "is_sub": "." in t,
                         "findings": [f["finding_id"] for f in fids], "mitigations": [m["mitigation_id"] for m in mids],
                         "residual": round(sum(f["residual"] for f in fids), 2), "inherent": round(sum(f["inherent"] for f in fids), 2),
                         "status_counts": {s: statuses.count(s) for s in EFFECTIVE if statuses.count(s)}, "coverage": cov}
    tactics = {}
    for t in TACTICS + ["Unknown"]:
        ts = [x for x in techniques.values() if x["tactic"] == t and not x["is_sub"]]
        if ts:
            tactics[t] = {"techniques": [x["technique"] for x in ts], "residual": round(sum(x["residual"] for x in ts), 2),
                          "inherent": round(sum(x["inherent"] for x in ts), 2), "gaps": sum(1 for x in ts if x["coverage"] == "gap")}
    paths = {}
    for f in findings.values():
        p = paths.setdefault(f["attack_path"], {"findings": [], "residual": 0.0, "inherent": 0.0, "weakest_link": None})
        p["findings"].append(f["finding_id"]); p["residual"] += f["residual"]; p["inherent"] += f["inherent"]
        if p["weakest_link"] is None or f["residual"] > findings[p["weakest_link"]]["residual"]: p["weakest_link"] = f["finding_id"]
    for p in paths.values(): p["residual"] = round(p["residual"], 2); p["inherent"] = round(p["inherent"], 2)

    active = [f for f in findings.values() if f["effective_status"] != "accepted"]
    overall_res = round(sum(f["residual"] for f in active), 2)
    overall_inh = round(sum(f["inherent"] for f in active), 2)
    counts = {s: sum(1 for f in findings.values() if f["effective_status"] == s) for s in EFFECTIVE}
    v_den = counts["remediated"] + counts["validated"]
    rf_den = counts["validated"] + counts["validated_failed"]
    validation = {"claimed": counts["remediated"], "validated": counts["validated"], "failed": counts["validated_failed"],
                  "validation_rate": round(100 * counts["validated"] / v_den, 1) if v_den else None,
                  "retest_fail_rate": round(100 * counts["validated_failed"] / rf_den, 1) if rf_den else None,
                  "claimed_unproven_residual": round(sum(f["residual"] for f in findings.values() if f["effective_status"] == "remediated"), 2),
                  "retest_queue": [f["finding_id"] for f in sorted((x for x in findings.values() if x["effective_status"] == "remediated"), key=lambda x: -x["residual"])]}
    top = [f["finding_id"] for f in sorted(active, key=lambda x: (-x["residual"], -x["inherent"]))[:top_n]]
    tech_cov = {c: sum(1 for x in techniques.values() if not x["is_sub"] and x["coverage"] == c) for c in ("gap", "claimed", "validated", "accepted", "untested_coverage")}

    state = {
        "meta": dict(meta, skill_version=SKILL_VERSION, generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), weights=W,
                     counts={"findings": len(findings), "mitigations": len(mitigations), "status_rows": len(status_raw)}),
        "summary": {"residual": overall_res, "inherent": overall_inh, "residual_index": round(100 * overall_res / overall_inh, 1) if overall_inh else 0.0,
                    "accepted_risk": round(sum(f["accepted_risk"] for f in findings.values()), 2), "status_counts": counts,
                    "techniques_demonstrated": sum(1 for x in techniques.values() if not x["is_sub"] and x["findings"]),
                    "technique_coverage": tech_cov, "data_quality_issues": sum(len(v) for v in dq.values())},
        "findings": [findings[k] for k in sorted(findings)], "mitigations": [mitigations[k] for k in sorted(mitigations)],
        "techniques": techniques, "tactics": tactics, "attack_paths": paths, "top": top, "validation": validation,
        "data_quality": {k: v for k, v in sorted(dq.items(), key=lambda kv: -len(kv[1]))},
    }
    return state

def diff(prev, cur):
    pf = {f["finding_id"]: f for f in prev.get("findings", [])}
    cf = {f["finding_id"]: f for f in cur["findings"]}
    new = sorted(set(cf) - set(pf)); gone = sorted(set(pf) - set(cf))
    resolved, regressed, changed = [], [], []
    for fid in sorted(set(cf) & set(pf)):
        a, b = pf[fid]["effective_status"], cf[fid]["effective_status"]
        if a == b: continue
        rec = {"finding_id": fid, "from": a, "to": b, "residual_from": pf[fid]["residual"], "residual_to": cf[fid]["residual"]}
        if b == "validated": resolved.append(rec)
        elif a == "validated" and b in ("open", "in_progress", "validated_failed", "remediated"): regressed.append(rec)
        else: changed.append(rec)
    pt = prev.get("techniques", {}); ct = cur["techniques"]
    tech_moves = []
    for t in set(pt) | set(ct):
        r0 = pt.get(t, {}).get("residual", 0.0); r1 = ct.get(t, {}).get("residual", 0.0)
        if abs(r1 - r0) > 0.005: tech_moves.append({"technique": t, "from": r0, "to": r1, "delta": round(r1 - r0, 2), "coverage_from": pt.get(t, {}).get("coverage"), "coverage_to": ct.get(t, {}).get("coverage")})
    tech_moves.sort(key=lambda x: -abs(x["delta"]))
    ps = prev.get("summary", {})
    return {"previous_generated_at": prev.get("meta", {}).get("generated_at"), "previous_run": prev.get("meta", {}).get("run_number"),
            "previous_engagement": prev.get("meta", {}).get("engagement"),
            "weights_changed": prev.get("meta", {}).get("weights") != cur["meta"]["weights"],
            "index_from": ps.get("residual_index"), "index_to": cur["summary"]["residual_index"],
            "residual_from": ps.get("residual"), "residual_to": cur["summary"]["residual"],
            "new": new, "removed": gone, "resolved": resolved, "regressed": regressed, "changed": changed, "technique_moves": tech_moves[:25],
            "status_counts_from": ps.get("status_counts"), "status_counts_to": cur["summary"]["status_counts"]}

# ---------------------------------------------------------------- Blue edits (manual overrides)
def apply_overrides(edits, mr, sr, fr):
    """Apply manual Blue edits (owner / retest date / ticket / retest result) to raw rows before scoring.
    A target_id that matches a mitigation updates that mitigation row; one that matches a finding
    becomes a status row (latest wins by updated_date). Unknown targets are returned for data-quality."""
    mids = {r.get("mitigation_id"): r for r in mr}
    fids = {r.get("finding_id") for r in fr}
    latest = {}
    for r in sr:
        fid = r.get("finding_id")
        if fid and (fid not in latest or (r.get("updated_date") or "") >= (latest[fid].get("updated_date") or "")):
            latest[fid] = r
    unknown = []
    for e in edits:
        tid = str(e.get("target_id") or "").strip()
        if not tid: continue
        fields = {k: e.get(k) for k in ("owner", "validated_date", "ticket_id", "validation_status") if e.get(k) not in (None, "")}
        if tid in mids:
            mids[tid].update(fields)
            if e.get("note"): mids[tid]["evidence"] = (mids[tid].get("evidence") or "") + f" | edit: {e['note']}"
        elif tid in fids:
            base = dict(latest.get(tid) or {"finding_id": tid, "status": next((r.get("status") for r in fr if r.get("finding_id") == tid), None) or "open"})
            base.update(fields); base["updated_date"] = e.get("edited_at") or base.get("updated_date") or ""
            base["notes"] = ((base.get("notes") or "") + f" | manual edit{(' by ' + e['edited_by']) if e.get('edited_by') else ''}").strip(" |")
            sr.append(base); latest[tid] = base
        else:
            unknown.append(tid)
    return unknown

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--findings", required=True); ap.add_argument("--mitigations"); ap.add_argument("--status")
    ap.add_argument("--prior"); ap.add_argument("--engagement", default=""); ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--weights"); ap.add_argument("--status-map"); ap.add_argument("--out", default="purple_state.json")
    ap.add_argument("--source-findings", default=""); ap.add_argument("--source-mitigations", default=""); ap.add_argument("--source-status", default="")
    ap.add_argument("--overrides", help="Blue edits file (JSON or CSV): target_id, owner, validated_date, ticket_id, validation_status, note, edited_at")
    a = ap.parse_args()

    weights = copy.deepcopy(DEFAULT_WEIGHTS)
    if a.weights:
        for k, v in json.load(open(a.weights)).items():
            weights.setdefault(k, {}).update(v)
    extra_map = json.load(open(a.status_map)) if a.status_map else {}
    fr = canonicalize(load_rows(a.findings, "findings"), "findings")
    mr = canonicalize(load_rows(a.mitigations, "mitigations"), "mitigations") if a.mitigations else []
    sr = canonicalize(load_rows(a.status, "status"), "status") if a.status else []
    prior = load_prior(a.prior)
    run_number = (prior.get("meta", {}).get("run_number", 0) + 1) if prior else 1
    # Blue edits: carried forward from the prior state, then the overrides file on top (later wins per target)
    edits = list((prior or {}).get("blue_edits") or [])
    if a.overrides:
        edits += canonicalize(load_rows(a.overrides, "overrides"), "overrides")
    merged = {}
    for e in edits:
        if e.get("target_id"): merged[str(e["target_id"]).strip()] = {**merged.get(str(e["target_id"]).strip(), {}), **{k: v for k, v in e.items() if v not in (None, "")}}
    edits = list(merged.values())
    for e in edits:
        if e.get("validation_status"): e["validation_status"] = norm_validation(e["validation_status"])
    unknown_edits = apply_overrides(edits, mr, sr, fr) if edits else []
    meta = {"engagement": a.engagement, "run_number": run_number,
            "sources": {"findings": a.source_findings or os.path.basename(a.findings),
                        "mitigations": a.source_mitigations or (os.path.basename(a.mitigations) if a.mitigations else "(none provided)"),
                        "status": a.source_status or (os.path.basename(a.status) if a.status else "(none provided)"),
                        "blue_edits": (f"{len(edits)} manual edit(s)" + (f" via {os.path.basename(a.overrides)}" if a.overrides else " carried from prior")) if edits else "(none)"}}
    state = compute(fr, mr, sr, weights, extra_map, a.top, meta)
    state["blue_edits"] = edits
    for tid in unknown_edits:
        state["data_quality"].setdefault("unknown_edit_target", []).append({"entity": "blue_edit", "id": tid, "detail": "target_id matches no mitigation or finding"})
    state["summary"]["data_quality_issues"] = sum(len(v) for v in state["data_quality"].values())
    if prior:
        state["delta"] = diff(prior, state)
        with open(re.sub(r"\.json$", "", a.out) + ".previous.json", "w", encoding="utf-8") as f:
            json.dump(prior, f, ensure_ascii=False, indent=1)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)

    s = state["summary"]; v = state["validation"]
    print(f"purple_join v{SKILL_VERSION} — run {run_number}{' (delta vs run ' + str(prior['meta'].get('run_number')) + ')' if prior else ''}")
    print(f"  findings {state['meta']['counts']['findings']} | mitigations {state['meta']['counts']['mitigations']} | status rows {state['meta']['counts']['status_rows']}")
    print(f"  residual index {s['residual_index']}  (residual {s['residual']} / inherent {s['inherent']}; accepted {s['accepted_risk']})")
    print(f"  status: " + ", ".join(f"{k} {n}" for k, n in s['status_counts'].items()))
    print(f"  validation rate {v['validation_rate']}% | retest fail rate {v['retest_fail_rate']}% | claimed-unproven residual {v['claimed_unproven_residual']}")
    print(f"  technique coverage: " + ", ".join(f"{k} {n}" for k, n in s['technique_coverage'].items()))
    print(f"  data-quality issues {s['data_quality_issues']}: " + ", ".join(f"{k} ({len(x)})" for k, x in list(state['data_quality'].items())[:8]))
    if prior:
        d = state["delta"]
        print(f"  delta: index {d['index_from']} -> {d['index_to']} | new {len(d['new'])} resolved {len(d['resolved'])} regressed {len(d['regressed'])} changed {len(d['changed'])}" + (" | WEIGHTS CHANGED" if d["weights_changed"] else ""))
    if edits: print(f"  blue edits applied: {len(edits)}" + (f" ({len(unknown_edits)} unknown target)" if unknown_edits else ""))
    print(f"  wrote {a.out}")

if __name__ == "__main__":
    main()
