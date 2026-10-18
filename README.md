# YieldClaim

**Did the vault really pay what its page says?** A GenLayer Intelligent Contract that sets a product page's advertised yield beside what the vault behind it actually paid. Every yield page says "x.xx% APY"; the vault keeps its own books on-chain, in its share price. YieldClaim has validators read the page, an LLM read only the words around the figure, and plain arithmetic compute the realised yield from the share price at three finalized blocks, read from independent archive nodes. The verdict is `MATCHES`, `OVERSTATED`, `UNDERSTATED`, `NOT_COMPARABLE` (a promotional or "up to" figure is not the share price's to refute) or `UNDETERMINED`, and a consumer contract can gate money on it.

| | |
|---|---|
| Network | GenLayer Studio Next (chain 61997) |
| YieldClaim | [`0xE8fDfd4F9FB3d4Df9E67e61Db9F25D6dcF9Df0bc`](https://explorer-studio-dev.genlayer.com/address/0xE8fDfd4F9FB3d4Df9E67e61Db9F25D6dcF9Df0bc) |
| VaultGate (a consumer) | [`0x9876768863B6fDacA59b39f227c3C3A0E751DBa6`](https://explorer-studio-dev.genlayer.com/address/0x9876768863B6fDacA59b39f227c3C3A0E751DBa6) |
| Live proof | [CONTRACT.md](CONTRACT.md): four real pages (Sky's sUSDS and stUSDS, Lido, Ethena) against their vaults, the refusals, two clearly marked synthetic pages for the verdicts no real page earned, and the gate allocating and refusing; 30 transactions, every one linked |
| Research | [research/README.md](research/README.md): what the validators can reach, which keyless archive nodes work, what the real vaults paid, and the decisions that followed |
| Tests | 303 Direct Mode tests on the captured pages and on-chain values; 221 safety mutations, all killed |

> **A comparison, not a recommendation.** YieldClaim says whether a page's headline figure is what its vault paid over the last week or month. It does not say a vault is safe, that the yield will continue, or that a page is honest about everything else. A figure it cannot fairly compare is reported as such, never as a pass.

## Why this exists

A yield page is a claim, and the vault behind it already holds the evidence: an ERC-4626 vault's `convertToAssets` (or wstETH's `stEthPerToken`) grows exactly as fast as the vault pays. Nobody reconciles the two. A treasury choosing where to park stablecoins reads the page; a risk team checks it by hand, once. YieldClaim does the reconciliation with consensus, on demand, and leaves a record a contract can read.

It is deliberately narrow. It compares a **current** or **7 / 30 day average** headline rate with the share price's growth over the same window. A figure that is qualified ("up to", promotional, fixed-term, reward tokens, leveraged), averaged over some other period, or about some other product is recorded as `NOT_COMPARABLE`, because the share price cannot refute it.

## How it decides

**A claim** binds a product page, a *label* that must sit next to the figure (the product's name as the page writes it, e.g. `stUSDS`), and a vault: an address and the calldata of a view that returns a growing index. It also fixes a tolerance (10 to 500 basis points). Registering is permissionless and immutable, and is itself a consensus read: the page must show a figure by the label, and the index must answer on-chain.

**A check** (anyone can ask for one) does four things, in one transaction:

1. **The page.** Every validator fetches it and reduces it to the words a visitor sees. Plain code lists every percentage written within 250 characters of the label, nearest first, at most eight. That list is all the model ever sees.
2. **The reader.** The model chooses one figure (or none) and classifies it: APY or APR; current, a 7-day or 30-day average, some other average, since-inception or projected; and plain or qualified. It cannot write a number: the figure stored is the one the page shows, taken by code. A page that tries to instruct the model can steer a choice among its own figures and nothing else.
3. **The chain.** The leader pins the lowest *finalized* Ethereum block among three keyless archive nodes (dRPC, Tenderly, Nodies). The share price and the block's own timestamp are read at that block and at the blocks 7 and 30 days earlier, from every node. At least two must answer, and **every node that answers must give the same value to the last digit**; one that disagrees fails the read. A validator accepts the leader's block only if a node has finalized it and it is within about six hours of the head, then re-reads everything at that block: a historical block never changes, so agreement is exact.
4. **The verdict.** Pure arithmetic on what was agreed. The realised yield over each window is the index's simple annualised growth (APR) and the same compounded daily, `(1 + apr/365)^365 - 1` (APY), in basis points rounded down; elapsed time comes from the blocks' timestamps. The claim is graded on the basis it states, over the window its period selects:

| Page's figure | Compared with | Verdict |
|---|---|---|
| current, 7-day average | the last 7 days | within the tolerance: `MATCHES`; more than the tolerance above: `OVERSTATED`; more than the tolerance below: `UNDERSTATED` |
| 30-day average | the last 30 days | the same |
| basis not stated | the nearer of APR and APY (a tie takes the lower) | the same: the page gets the benefit of the doubt |
| qualified, or another period, or no headline rate | nothing | `NOT_COMPARABLE`; the realised yield is still recorded beside it |
| page, nodes or model unreadable or in disagreement | nothing | `UNDETERMINED` |

The verdict is recomputed from the agreed facts, never taken from the leader. An `UNDETERMINED` check decides nothing: the **standing** a consumer reads is the latest *decided* check, so a flaky page can neither hide a bad verdict nor invent a good one, and the consumer sees how old it is.

## The calls

| Call | Who | What it does |
|---|---|---|
| `register_claim(claim_id, page_url, label, vault, rate_call, tolerance_bps, note)` | anyone | Binds a page, a label and a vault, after a consensus read of both. Refused if the page shows no figure by the label, the vault does not answer the call, the same page/label/vault/call is already registered, or any format is wrong (https page URL on a named host, a vault address, a lowercase `rate_call`, a tolerance in range). |
| `check(claim_id)` | anyone | One fresh consensus read of the page and the chain; appends a record with the verdict, the quote, the realised yield and the on-chain facts. |

Views: `get_standing(claim_id)` (the latest decided check, how old it is, the claim, the realised yield and the gap), `get_claim`, `list_claims`, `get_check`, `get_checks(offset, limit)`, `get_history(claim_id, limit)`, `get_rules` (the nodes, windows, bounds, enumerations and the APY convention), `get_state`.

## Using it from another contract

```python
yc = gl.contract.get_at(0xE8fDfd4F9FB3d4Df9E67e61Db9F25D6dcF9Df0bcESS)           # Studio Next syntax
s = yc.view().get_standing("sky-susds")
if s["verdict"] not in ("MATCHES", "UNDERSTATED") or s["age_seconds"] > MAX_AGE or s["realised_bps"] < FLOOR:
    raise gl.vm.UserError(f"refused: {s['verdict']}")
```

[`VaultGate`](contracts/vault_gate.py) is exactly that, as a contract: the treasury owner records an allocation to a claim only if its latest decided check is fresh, `MATCHES` or `UNDERSTATED`, the **verified** yield (not the advertised one) meets a floor, and the claim's running total stays within a cap. Each allocation is logged with the claim's vault and page, so a look-alike claim registered against another page is visible in it. It is a consumer, not a vault: it does not move tokens.

## What this proves, and what it doesn't

| It proves | It does not prove |
|---|---|
| What figure a page showed beside a product's name when the validators read it, and how a model classified it, agreed by a committee | That the page is the product's *only* statement, or that a figure elsewhere is honest |
| What the vault's share price was at three finalized blocks, agreed to the last digit by independent nodes, and the yield that implies | That the yield will continue: it is a trailing 7- or 30-day figure |
| That a page's current rate and the vault's realised week agree (or do not) within a tolerance chosen at registration | That a vault is safe, solvent or liquid |
| That a figure which cannot be compared (promotional, "up to", an average since launch...) was recognised as such | That a promotion is misleading: it is only reported as not comparable |

## Known limitations

- **Ethereum mainnet only**, through three keyless archive nodes. Other chains need their own trio of independent nodes.
- **A trailing window.** A "current" rate is graded against the last 7 days. A rate that moved sharply during the week can read as a mismatch that is really a lag; the tolerance is the registrant's lever, bounded to 10-500 basis points.
- **A ticking page.** The recorded quote is the figure with a few words either side, so a changing number elsewhere in the sentence cannot unground it, but a figure that changes between the leader's read and a validator's makes the transaction fail to agree (nothing is recorded) until a read lands on a stable value.
- **The model can disagree with itself.** Validators agree on the decision a consumer acts on (a comparable figure's number, basis and period, or that it cannot be compared), not on the model's exact wording; if they still differ, a majority decides, as in any GenLayer transaction, and a split vote is visible in the transaction. A page with several products' figures side by side is the hard case: on Sky's home page, with five figures by the label, one of four voting validators disagreed in the live run ([CONTRACT.md](CONTRACT.md)). Register the product's own page and a specific label. A model that never returns a usable answer yields `UNDETERMINED`.
- **One index per claim.** The `rate_call` must return a share price that grows with the yield (ERC-4626 `convertToAssets(1e18)`, wstETH `stEthPerToken()`, a cToken exchange rate...). A rebasing token's balance is not one.
- **Server-rendered pages only.** A figure a browser fills in (Ethena's headline "Avg sUSDe APY") is not on the page a validator fetches.
- **A claim's tolerance is fixed at registration**, and so is its identity: the same page, label, vault and call can be registered once. A different tolerance needs a different label.
- **Studio Next only.**

## Running it

```bash
python3 -m venv .venv && .venv/bin/pip install genlayer-test==0.29.2 genvm-linter==0.11.0 pytest
.venv/bin/pytest tests -q                       # the contract and gate tests
.venv/bin/genvm-lint check contracts/yield_claim.py contracts/vault_gate.py    # (one file per call)
python3 scripts/mutation_check.py               # every safety mutation must be killed

cd studio-next && npm ci
npx tsx verify_code.ts <address> yield_claim_studio_next.py     # on-chain code == this repo
npx tsx refresh.ts                                                # ask for a fresh check of every official claim
python3 ../scripts/capture_fixtures.py          # re-capture the test inputs (network; the tests do not need it)
```

## Repository layout

```
contracts/yield_claim.py               tested source (GenVM v0.2.11)
contracts/yield_claim_studio_next.py   deployed port (Studio Next), generated by scripts/port_to_studio_next.py
contracts/vault_gate.py                the consumer, and its deployed port
tests/                                 Direct Mode tests, a stand-in world (harness.py), captured pages and on-chain values (fixtures/), mutations
demo/                                  two SYNTHETIC pages for the live proof's OVERSTATED and UNDERSTATED rows
scripts/                               port, mutation check, fixture capture, CONTRACT.md builder
studio-next/                           deploy, live proof (prove.ts, live_proof.json), verify_code.ts, refresh.ts
research/                              what the validators can reach, what the real vaults paid, the decisions
```
