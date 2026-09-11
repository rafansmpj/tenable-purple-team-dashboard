# Residual risk — formula, weights, rollups

Residual risk answers: *of what Red proved it can do, how much can it still do?* It is computed per finding and rolled up.

## Per-finding score

```
residual(f) = severity_w(f) × exploitability_w(f) × exposure_w(f) × mitigation_factor(f)
inherent(f) = severity_w(f) × exploitability_w(f) × exposure_w(f)          # same thing with factor = 1
```

| Component | Default weights | Source column |
|---|---|---|
| `severity_w` | Critical 10 · High 7 · Medium 4 · Low 1 · Info 0 | `severity`; numeric CVSS/VPR uses the number directly (0–10) |
| `exploitability_w` | demonstrated 1.0 · exploit_available 0.8 · theoretical 0.5 | `exploitability` (default demonstrated) |
| `exposure_w` | internal 1.0 · internet-exposed 1.3; multiplied by ACR factor 0.6 + 0.08×ACR (ACR 5 → 1.0, ACR 10 → 1.4, ACR 1 → 0.68) when ACR present | `internet_exposed`, `acr` |
| `mitigation_factor` | open 1.0 · in_progress 0.8 · remediated 0.4 · validated 0.0 · validated_failed 1.0 · accepted 0.0 (tracked separately) | effective status after join |

Why `remediated` still scores 0.4: a closed ticket is a claim, not evidence. Until Red re-tests, the dashboard assumes a meaningful chance the fix is incomplete, misapplied, or bypassable. This is the mechanism that makes validation visible — the residual number only reaches zero when Purple confirms the block.

## Rollups

- **Overall residual** = Σ residual(f) over all findings (accepted excluded).
- **Overall inherent** = Σ inherent(f).
- **Residual index (0–100)** = 100 × overall residual ÷ overall inherent. 100 = nothing effectively mitigated, 0 = everything validated. This is the headline number on the dashboard and the one to compare across quarters.
- **Accepted risk** = Σ inherent(f) for `accepted` findings, shown beside (not inside) the residual figures.
- **By technique**: Σ residual(f) for each technique on the finding. A finding with two techniques counts fully in both (so the technique column can sum above overall — the dashboard footnotes this). Sub-techniques roll into parents for the heatmap.
- **By tactic**: derived from technique → tactic table (built into the script for Enterprise ATT&CK v15 technique IDs; unknown techniques go to `Unknown tactic`).
- **By attack path**: Σ residual(f) grouped by `attack_path`; each finding counts once. Also shows the path's *weakest link* — the highest residual finding — because breaking one step breaks the path.
- **Top N**: findings sorted by residual desc, ties by inherent desc. Default 15.

## Validation metrics

- `validation_rate` = validated ÷ (remediated + validated) — how much claimed progress is proven.
- `retest_fail_rate` = validated_failed ÷ (validated + validated_failed) — how often claims turned out wrong.
- `claimed_unproven_residual` = Σ residual over `remediated` findings — the score that would disappear if Blue's claims were all validated. This is the single best argument for scheduling a retest.

## Overriding weights

Pass `--weights weights.json` to `purple_join.py`. Only the keys you set are overridden:

```json
{
  "severity": {"critical": 10, "high": 7, "medium": 4, "low": 1, "info": 0},
  "exploitability": {"demonstrated": 1.0, "exploit_available": 0.8, "theoretical": 0.5},
  "exposure": {"internal": 1.0, "internet": 1.3, "acr_base": 0.6, "acr_slope": 0.08},
  "mitigation": {"open": 1.0, "in_progress": 0.8, "remediated": 0.4, "validated": 0.0, "validated_failed": 1.0, "accepted": 0.0}
}
```

The weights used are stored in `purple_state.json` so a later run can detect that the formula changed and say so in the Changes tab (comparing scores computed with different weights is misleading).

## Worked example

Finding F-12: High (7), demonstrated (1.0), internet-exposed (1.3), ACR 8 (0.6 + 0.64 = 1.24), ticket closed but not re-tested (0.4).

- inherent = 7 × 1.0 × 1.3 × 1.24 = 11.28
- residual = 11.28 × 0.4 = 4.51

After Red re-tests and confirms the block → validated → residual 0. If the re-test shows the attack still works → validated_failed → residual 11.28, flagged in red on the scoreboard.
