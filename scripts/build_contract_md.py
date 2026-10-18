"""
Writes CONTRACT.md from studio-next/live_proof.json (the log prove.ts wrote as it ran), so no transaction hash,
verdict or percentage in it is ever transcribed by hand.   python3 scripts/build_contract_md.py
Deployment facts come from studio-next/deployment.json (written by hand once, from the deploy logs).
"""
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
L = json.loads((REPO / "studio-next" / "live_proof.json").read_text())
D = json.loads((REPO / "studio-next" / "deployment.json").read_text())
X = "https://explorer-studio-dev.genlayer.com"


def tx(h): return f"[`{h[:10]}…`]({X}/tx/{h})"
def votes(v):
    a, d = v.count("AGREE"), v.count("DISAGREE")
    return f"{a} agree" + (f", {d} disagree" if d else "")
def pct(bps): return "" if bps is None else f"{bps / 100:.2f}%"
def short(a): return a[:10] + "…" + a[-4:]


regs = [e for e in L if e["step"] == "register" and e["result"] == "FINISHED_WITH_RETURN" and not e["id"].startswith("reg-demo")]
demo_regs = [e for e in L if e["step"] == "register" and e["id"].startswith("reg-demo")]
refusals = [e for e in L if e["step"] == "refuse-register"]
checks = [e for e in L if e["step"] == "check" and not e["args"][0].startswith("demo")]
demo_checks = [e for e in L if e["step"] == "check" and e["args"][0].startswith("demo")]
gates = [e for e in L if e["step"] == "gate"]
read = next((e for e in L if e["step"] == "read"), None)
assert all(e["result"] in ("FINISHED_WITH_RETURN", "FINISHED_WITH_ERROR") for e in L if "result" in e)
decided = [e for e in L if "tx" in e]
dissent = [e for e in decided if "DISAGREE" in e.get("votes", [])]

o = []
w = o.append
w("# YieldClaim: deployment and live proof\n")
w("## Deployment\n")
w("| | |\n|---|---|")
w("| Network | GenLayer Studio Next, chain 61997 (`chains.studioDevnet`, genlayer-js 2.0.0-rc.1) |")
w(f"| YieldClaim | [`{D['yieldclaim']['address']}`]({X}/address/{D['yieldclaim']['address']}) - deploy tx {tx(D['yieldclaim']['deploy_tx'])} |")
w(f"| VaultGate | [`{D['gate']['address']}`]({X}/address/{D['gate']['address']}) - deploy tx {tx(D['gate']['deploy_tx'])}; constructed with YieldClaim's address, `max_age_seconds` 86400, `min_realised_bps` 300 (3.00%) and a cap of 1,000,000 |")
w(f"| VaultGate (strict) | [`{D['strict']['address']}`]({X}/address/{D['strict']['address']}) - deploy tx {tx(D['strict']['deploy_tx'])}; the same, but wants a check no more than 1 second old (to show a stale check refused) |")
w("| Runner | `py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng` (v0.3.0) |")
w("| Deployer and gate owner | `0x5cdb5699bc1038e115A973bb91A646f7E98C075b` |\n")
w("Both contracts passed the live runner's `getContractSchemaForCode` check before deploying, and **the code on-chain is byte-identical to this repo**: `cd studio-next && npx tsx verify_code.ts <address> <file>` fetches it with `gen_getContractCode` and compares.\n")
w("| Contract | SHA-256 on-chain = SHA-256 of the repo file |\n|---|---|")
w(f"| YieldClaim / `contracts/yield_claim_studio_next.py` | `{D['yieldclaim']['sha256']}` |")
w(f"| VaultGate / `contracts/vault_gate_studio_next.py` | `{D['gate']['sha256']}` |\n")
w(f"## Live proof ({D['date']})\n")
w(f"Reproduce with `cd studio-next && npx tsx prove.ts <yieldclaim> <register|check|demo|gate|read> [vaultgate] [strict gate]`. Every row is from [`studio-next/live_proof.json`](studio-next/live_proof.json), written as it ran (it resumes where it stopped). \"Agree\" counts the validators that actively voted (Studio Next leaves the rest of the 5-seat committee idle). **All {len(decided)} transactions reached consensus, {len(decided) - len(dissent)} of them with every voting validator agreeing and {len(dissent)} with a dissenting vote (shown as \"disagree\" in the tables)**, including the ones the contracts refused: a refusal is a decided outcome.\n")

w("### 1. Claims registered\n")
w("Registration is itself a consensus read: every validator fetched the page, found a percentage written by the label, and read the vault's share price at three blocks from three archive nodes. A claim is permissionless and immutable.\n")
w("| Claim | Page | Label | Vault and call | Tx |\n|---|---|---|---|---|")
for e in regs:
    c = e["claim"]
    w(f"| `{c['claim_id']}` - {e['note']} | {c['page_url']} | `{c['label']}` | `{short(c['vault'])}` `{c['rate_call'][:10]}…`, tolerance {c['tolerance_bps']} bps | {tx(e['tx'])} {votes(e['votes'])} |")

w("\n### 2. What registration refuses\n")
w("| What it tries | Tx | Outcome |\n|---|---|---|")
for e in refusals:
    w(f"| {e['note']} | {tx(e['tx'])} {votes(e['votes'])} | refused: `{e['revert']}` |")

w("\n### 3. The checks: each page against its vault\n")
w("One `check` is one consensus transaction: every validator fetches the page and reads the vault's share price at the latest finalized block, 7 and 30 days earlier (from at least two of three archive nodes that must agree to the last digit); the language model chooses among the page's own figures; the verdict is arithmetic on what was agreed. Basis points; \"vault paid\" is on the basis the page states, over the window its period selects.\n")
w("| Claim | The page says (recorded quote) | Read as | Vault paid | Gap | Verdict | Tx |\n|---|---|---|---|---|---|---|")
for e in checks:
    k = e["check"]
    s, rd = k["summary"], k["reading"]
    quote = f"“{rd['quote']}”" if rd and rd.get("index") is not None else "no headline rate"
    readas = f"{rd['basis']}, {rd['period'].lower()}, {rd['qualifier'].lower()}" if rd and rd.get("index") is not None else ""
    paid = f"{pct(s['realised_bps'])} ({s['basis_used']}, {s['window_days']}d)" if s["realised_bps"] is not None else ("n/a" if s["realised"] else "unread")
    gap = f"{s['gap_bps']:+d}" if s["gap_bps"] is not None else ""
    why = f" - {k['reasons'][0]}" if k["reasons"] else ""
    w(f"| `{k['claim_id']}` | {quote} | {readas} | {paid} | {gap} | **{k['verdict']}**{why} | {tx(e['tx'])} {votes(e['votes'])} |")
w("\nThe on-chain facts behind every row (block numbers, timestamps, share prices) are in the check's record: `get_check(id)`; the explorer links above show the validators' votes.\n")

if demo_checks:
    w("### 4. Two SYNTHETIC pages, for the verdicts no real page earned\n")
    w("On the day of the proof every real page stated a figure its vault had paid (or a promotion that was not the vault's yield at all). To show `OVERSTATED` and `UNDERSTATED` on-chain, two pages were written for this purpose ([`demo/`](demo/), served from `raw.githubusercontent.com`): they present a fictitious \"Example Vault\" and are registered against a REAL vault, Sky's sUSDS. **They are not real products and no issuer made these claims.**\n")
    w("| Claim | The page says | Vault paid | Gap | Verdict | Tx |\n|---|---|---|---|---|---|")
    for e in demo_checks:
        k = e["check"]
        s, rd = k["summary"], k["reading"]
        quote = f"“{rd['quote']}”" if rd and rd.get("index") is not None else "no headline rate"
        gap = f"{s['gap_bps']:+d}" if s["gap_bps"] is not None else ""
        w(f"| `{k['claim_id']}` | {quote} | {pct(s['realised_bps'])} ({s['basis_used']}, {s['window_days']}d) | {gap} | **{k['verdict']}** | {tx(e['tx'])} {votes(e['votes'])} |")
    w("")

w("### 5. VaultGate: a consumer that acts on the verdict\n")
w("The gate records an allocation to a claim only if YieldClaim's standing for it is fresh, MATCHES or UNDERSTATED, a verified yield at or above the gate's floor, and within the cap. It reads `get_standing` at the moment of the call, from YieldClaim's own record.\n")
w("| What it shows | Gate | Call | Outcome | Tx |\n|---|---|---|---|---|")
for e in gates:
    claim, amount = e["args"]
    out_ = "**recorded**" if e["result"] == "FINISHED_WITH_RETURN" else f"refused: `{e['revert']}`"
    w(f"| {e['note']} | {e['which']} | `allocate({claim}, {int(amount):,})` | {out_} | {tx(e['tx'])} {votes(e['votes'])} |")
if read and read.get("gate_config"):
    cfg = read["gate_config"]
    w(f"\nAfter the run the gate's `get_config()` reports {cfg['allocation_count']} allocation(s); each is logged with the claim's vault and page (`get_allocations`), so a look-alike claim shows in the log.")
w("")

w("## What the live run found\n")
for t in D.get("found_live", []):
    w("- " + t)
w("")
if D.get("superseded"):
    w("## Superseded deployments\n")
    w("| Contract | Address | Why it is superseded |\n|---|---|---|")
    for s in D["superseded"]:
        w(f"| {s['contract']} | `{s['address']}` | {s['why']} |")
    w("")
w("## Proven in tests, not live\n")
w("Direct Mode proves these on the captured pages and on-chain values (and on edited copies of them, marked SYNTHETIC in the tests); none has a live transaction:\n")
w("- **The consensus boundary**: a validator rejecting a leader whose chain facts, block, quote or decision differ from its own, and accepting an honest one. Direct Mode runs the validator function against changed inputs; the live run shows the committee's votes on an honest leader, including the dissent in section 3.")
w("- **Every format refusal** not listed in section 2, the tolerance bounds, claim ids, labels, vault and call formats, and the page-url rules.")
w("- **Weekly and monthly windows**: the 30-day window and averages (`AVG_7D`, `AVG_30D`), an unspecified basis, qualified figures, and the periods that are not compared.")
w("- **One node down, two nodes down, a node that lies about a price or a timestamp, a node without an old block, a window the blocks do not cover**: the chain read's fail-closed branches.")
w("- **The gate's age rule for a check dated in the future, a floor exactly met, a cap exactly met**, and the owner-only rule (every live call came from the owner). VaultGate's logic after its read of YieldClaim is also run in Direct Mode against a stand-in with `get_standing`'s exact shape; the live section shows the same refusals against the real contract.")
w("- The language model is never run in Direct Mode: it is replaced by a reader that chooses the figure a test names. What the live run shows is the real validators' models choosing and classifying figures, with the votes in the tables above.")
(REPO / "CONTRACT.md").write_text("\n".join(o) + "\n")
print("wrote CONTRACT.md,", len(o), "lines;", len(decided), "transactions")
