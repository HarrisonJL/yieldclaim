# YieldClaim: deployment and live proof

## Deployment

| | |
|---|---|
| Network | GenLayer Studio Next, chain 61997 (`chains.studioDevnet`, genlayer-js 2.0.0-rc.1) |
| YieldClaim | [`0xE8fDfd4F9FB3d4Df9E67e61Db9F25D6dcF9Df0bc`](https://explorer-studio-dev.genlayer.com/address/0xE8fDfd4F9FB3d4Df9E67e61Db9F25D6dcF9Df0bc) - deploy tx [`0x0746ab98…`](https://explorer-studio-dev.genlayer.com/tx/0x0746ab983255e85e42ab2b5abeae0f7f7a386ef98475e7d33c6237b8df7e46b9) |
| VaultGate | [`0x9876768863B6fDacA59b39f227c3C3A0E751DBa6`](https://explorer-studio-dev.genlayer.com/address/0x9876768863B6fDacA59b39f227c3C3A0E751DBa6) - deploy tx [`0x0f2a1c86…`](https://explorer-studio-dev.genlayer.com/tx/0x0f2a1c86d8848105f6716506b15010e37288b9a22c049aeeb97bfe2662373398); constructed with YieldClaim's address, `max_age_seconds` 86400, `min_realised_bps` 300 (3.00%) and a cap of 1,000,000 |
| VaultGate (strict) | [`0x13A6464Ea508FDD64aCBEcFA5056b62d77D7F4c9`](https://explorer-studio-dev.genlayer.com/address/0x13A6464Ea508FDD64aCBEcFA5056b62d77D7F4c9) - deploy tx [`0x4aaff62b…`](https://explorer-studio-dev.genlayer.com/tx/0x4aaff62b152daa4d0a5a27a3faa9d7e4f7323171af7fc996d474583266986e60); the same, but wants a check no more than 1 second old (to show a stale check refused) |
| Runner | `py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng` (v0.3.0) |
| Deployer and gate owner | `0x5cdb5699bc1038e115A973bb91A646f7E98C075b` |

Both contracts passed the live runner's `getContractSchemaForCode` check before deploying, and **the code on-chain is byte-identical to this repo**: `cd studio-next && npx tsx verify_code.ts <address> <file>` fetches it with `gen_getContractCode` and compares.

| Contract | SHA-256 on-chain = SHA-256 of the repo file |
|---|---|
| YieldClaim / `contracts/yield_claim_studio_next.py` | `5fd0097e6d6a5508b99862a107beeca1d78127cf8e43268f7d81177dfedc5999` |
| VaultGate / `contracts/vault_gate_studio_next.py` | `faf97669a5243ba07a7eb34c2f7ac6830125102f529bcfcdb5e79db35f51e05a` |

## Live proof (2026-10-18)

Reproduce with `cd studio-next && npx tsx prove.ts <yieldclaim> <register|check|demo|gate|read> [vaultgate] [strict gate]`. Every row is from [`studio-next/live_proof.json`](studio-next/live_proof.json), written as it ran (it resumes where it stopped). "Agree" counts the validators that actively voted (Studio Next leaves the rest of the 5-seat committee idle). **All 25 transactions reached consensus, 24 of them with every voting validator agreeing and 1 with a dissenting vote (shown as "disagree" in the tables)**, including the ones the contracts refused: a refusal is a decided outcome.

### 1. Claims registered

Registration is itself a consensus read: every validator fetched the page, found a percentage written by the label, and read the vault's share price at three blocks from three archive nodes. A claim is permissionless and immutable.

| Claim | Page | Label | Vault and call | Tx |
|---|---|---|---|---|
| `sky-susds` - Sky's sUSDS page against the sUSDS vault | https://sky.money/susds | `sUSDS` | `0xa3931d71…7fbd` `0x07a2d13a…`, tolerance 50 bps | [`0x022bf534…`](https://explorer-studio-dev.genlayer.com/tx/0x022bf5341c40aaecbbee3daa296fb47e0f12c9680d7282fd52a324cbe4f5c062) 3 agree |
| `sky-stusds` - Sky's stUSDS page against the stUSDS vault | https://sky.money/stusds | `stUSDS` | `0x99cd4ec3…eeb9` `0x07a2d13a…`, tolerance 50 bps | [`0xb7d63061…`](https://explorer-studio-dev.genlayer.com/tx/0xb7d6306100f8ee684165c0337fe86580e81de2b84ffb993926c1d4e10f7d3171) 3 agree |
| `lido-steth` - Lido's staking APR against wstETH's stEthPerToken() | https://www.lido.fi/ | `staking with stETH` | `0x7f39c581…2ca0` `0x035faf82…`, tolerance 50 bps | [`0x81b55774…`](https://explorer-studio-dev.genlayer.com/tx/0x81b5577481bd167b4a0832d50298faab861d0a6b353305b7107f876cd2737a8d) 3 agree |
| `ethena-susde` - Ethena's home page, where the only yield figure is promotional | https://ethena.fi/ | `sUSDe` | `0x9d39a5de…3497` `0x07a2d13a…`, tolerance 50 bps | [`0x03946632…`](https://explorer-studio-dev.genlayer.com/tx/0x03946632f27c8415c8673fbb8cb8b6ab013c9b5c56492025b5852e8bc1d2f325) 4 agree |
| `sky-home-susds` - five figures near the label: the reader has to choose | https://sky.money/ | `sUSDS` | `0xa3931d71…7fbd` `0x07a2d13a…`, tolerance 50 bps | [`0x76d30b49…`](https://explorer-studio-dev.genlayer.com/tx/0x76d30b4921c14bf633c93ff7eb3ce60d8774f1b60a138cb09e8d6e61907d568c) 3 agree |
| `sky-ssr-unchecked` - a claim with no check yet (for the gate) | https://sky.money/susds | `Sky Savings Rate` | `0xa3931d71…7fbd` `0x07a2d13a…`, tolerance 50 bps | [`0x1e012f7e…`](https://explorer-studio-dev.genlayer.com/tx/0x1e012f7ec58887a9d6d7b900c19ea062384d1897d54ed62ed907fe49f9738670) 3 agree |

### 2. What registration refuses

| What it tries | Tx | Outcome |
|---|---|---|
| a label the page never shows | [`0x04b96689…`](https://explorer-studio-dev.genlayer.com/tx/0x04b966895a3395b29b1aa39fd59e2bd17c2b49f44a1654b366d6bbfc529f5dba) 3 agree | refused: `claim refused: no_figure_near_the_label` |
| a contract that has no such view (USDC has no convertToAssets) | [`0xcd044117…`](https://explorer-studio-dev.genlayer.com/tx/0xcd044117bbe98deee0b66643f0a9b74d1b1373e0467b2445bbe4f4fed55175a9) 3 agree | refused: `claim refused: too_few_sources_at_block_26220774, too_few_sources_at_block_26170374, too_few_sources_at_block_26004774` |
| the same page, label, vault and call again | [`0xbf1477f2…`](https://explorer-studio-dev.genlayer.com/tx/0xbf1477f26ea5312ab04fbfba4baeeaa6b1a5c45935d96be0ce8ae89fb84e8771) 3 agree | refused: `that page, label, vault and call are already registered as 'sky-susds'` |
| a tolerance below the 10 basis point minimum | [`0xe557a86d…`](https://explorer-studio-dev.genlayer.com/tx/0xe557a86d5fae2223795664ab5e7fea3f48aab248152c62ae3e59945fabcbe074) 3 agree | refused: `tolerance_bps must be between 10 and 500` |
| a page that is not https | [`0x26031c0f…`](https://explorer-studio-dev.genlayer.com/tx/0x26031c0f3a93e0a401501e97bb5f3f2bc8be1f3dcec74b31780bc7b93d4e37ba) 3 agree | refused: `page_url must be an https URL on a named host, without a port or fragment` |
| a claim id with a space and a bang | [`0x05dcff78…`](https://explorer-studio-dev.genlayer.com/tx/0x05dcff781aa7bf2d054e7dfc9a893979f013c37a7613b7bda672cd6db76a82ce) 3 agree | refused: `claim_id must be 1-32 characters of A-Z, a-z, 0-9, _ or -` |

### 3. The checks: each page against its vault

One `check` is one consensus transaction: every validator fetches the page and reads the vault's share price at the latest finalized block, 7 and 30 days earlier (from at least two of three archive nodes that must agree to the last digit); the language model chooses among the page's own figures; the verdict is arithmetic on what was agreed. Basis points; "vault paid" is on the basis the page states, over the window its period selects.

| Claim | The page says (recorded quote) | Read as | Vault paid | Gap | Verdict | Tx |
|---|---|---|---|---|---|---|
| `sky-susds` | “control, set, or guarantee the rate. 3.80% APY” | APY, current, none | 3.80% (APY, 7d) | +0 | **MATCHES** | [`0x7301ef63…`](https://explorer-studio-dev.genlayer.com/tx/0x7301ef631b1172d715d948cd3494034744b71e54e5f2843f4c36269af612fc89) 3 agree |
| `sky-stusds` | “the rate. All yields are variable. 5.64% APY” | APY, current, none | 5.69% (APY, 7d) | -5 | **MATCHES** | [`0x1453389b…`](https://explorer-studio-dev.genlayer.com/tx/0x1453389b7a34c02f8f68c8b07c600ef002fc8f6632b62e0173bda7b9da87bcb5) 3 agree |
| `lido-steth` | “Empowering and securing Ethereum since 2020 2.2% APR*” | APR, current, none | 2.21% (APR, 7d) | -1 | **MATCHES** | [`0x2cc95aac…`](https://explorer-studio-dev.genlayer.com/tx/0x2cc95aacdaf3b6553667a92355dee584d4650b0038e0ac5022c62487786950c9) 3 agree |
| `ethena-susde` | no headline rate |  | n/a |  | **NOT_COMPARABLE** - the page states no headline rate for this product | [`0x5dc56a75…`](https://explorer-studio-dev.genlayer.com/tx/0x5dc56a750481cb915025041b910095f7e2c61c99e8b8885186d827d0d7ca0bd5) 3 agree |
| `sky-home-susds` | “rate. View more details here . 3.80% APY” | APY, current, none | 3.80% (APY, 7d) | +0 | **MATCHES** | [`0x0c450bee…`](https://explorer-studio-dev.genlayer.com/tx/0x0c450beeeccd63d7099a24c360b54ebe18dcff795640043a17528a1577ce77bc) 3 agree, 1 disagree |

The on-chain facts behind every row (block numbers, timestamps, share prices) are in the check's record: `get_check(id)`; the explorer links above show the validators' votes.

### 5. VaultGate: a consumer that acts on the verdict

The gate records an allocation to a claim only if YieldClaim's standing for it is fresh, MATCHES or UNDERSTATED, a verified yield at or above the gate's floor, and within the cap. It reads `get_standing` at the moment of the call, from YieldClaim's own record.

| What it shows | Gate | Call | Outcome | Tx |
|---|---|---|---|---|
| MATCHES and the vault paid 3.80% (above the 3.00% floor): allowed | gate | `allocate(sky-susds, 400,000)` | **recorded** | [`0xd650dd97…`](https://explorer-studio-dev.genlayer.com/tx/0xd650dd97f3d9e95a767dd39333f9ffb8dba71211ddd711506aac896ac33e98d6) 3 agree |
| MATCHES and the vault paid about 5.7%: allowed | gate | `allocate(sky-stusds, 250,000)` | **recorded** | [`0x548515b3…`](https://explorer-studio-dev.genlayer.com/tx/0x548515b3754e5da7791279af87d34da242d06a906806e57297906a7c1a501c8d) 3 agree |
| MATCHES, but the vault paid 2.21%, below the gate's 3.00% floor: refused | gate | `allocate(lido-steth, 100,000)` | refused: `'lido-steth' refused: the vault paid 221 basis points, below this gate's floor 300` | [`0x0e71e87a…`](https://explorer-studio-dev.genlayer.com/tx/0x0e71e87ac071fbad35aa5767d5b40e0d19ab46ff6e8d8686ca348225d18d5cfd) 3 agree |
| a promotional figure: NOT_COMPARABLE: refused | gate | `allocate(ethena-susde, 1)` | refused: `'ethena-susde' refused: its page is NOT_COMPARABLE (this gate accepts MATCHES, UNDERSTATED)` | [`0x70c4e9bd…`](https://explorer-studio-dev.genlayer.com/tx/0x70c4e9bdbe517ad05a18a30ee2171bbb166d61b2bcbee6c4ef16fe5230e68246) 3 agree |
| 400,000 already allocated; 700,000 more would pass the 1,000,000 cap: refused | gate | `allocate(sky-susds, 700,000)` | refused: `'sky-susds' refused: this would take the total past the cap 1000000` | [`0x82da6c6d…`](https://explorer-studio-dev.genlayer.com/tx/0x82da6c6d117a04c5695830bfe491e673a2e052ceffe8c8eca0b9cd4c24b6c515) 3 agree |
| registered, never checked: refused | gate | `allocate(sky-ssr-unchecked, 1)` | refused: `'sky-ssr-unchecked' refused: no decided check yet` | [`0x2f9b1f72…`](https://explorer-studio-dev.genlayer.com/tx/0x2f9b1f728c5f948010cd6bf39b4be86180fdeca6a416dea158e72a8d57bc0bce) 3 agree |
| a claim YieldClaim has never heard of: refused | gate | `allocate(ghost, 1)` | refused: `'ghost' refused: YieldClaim has no such claim` | [`0xc9df0564…`](https://explorer-studio-dev.genlayer.com/tx/0xc9df0564b72662173ab501356679fde85ca792e887e0a960246bd85ae6c5b385) 3 agree |
| a gate that wants a check no more than a second old: refused | strict | `allocate(sky-susds, 1)` | refused: `'sky-susds' refused: its latest decided check is 227 seconds old; this gate wants at most 1` | [`0xf8f75c40…`](https://explorer-studio-dev.genlayer.com/tx/0xf8f75c4026dda1bd40edd804d9c215d712de12888e9c52d5426f6b5199e5b68f) 3 agree |

## What the live run found

- **Three of the four real pages state a figure the vault paid.** Sky's sUSDS page says 3.80% APY and the vault paid 3.80% APY over the week (gap 0); Sky's stUSDS page says 5.64% against the 5.69% the vault paid (-5 basis points); Lido says 2.2% APR against 2.21% (-1). All three are `MATCHES`, graded on the basis each page states, with every voting validator agreeing.
- **Ethena's only yield figure is not the vault's.** The home page offers "~12% APY" promotional rewards on a lending market, and the headline "Avg sUSDe APY" is filled in by the browser. The check recorded `NOT_COMPARABLE` (no headline rate for sUSDe on the page a validator reads), all three voting validators agreeing, and the gate refused it. The vault itself paid 4.82% APY over the week; that is recorded beside the verdict.
- **A page with five figures by the label is the hard case.** On Sky's home page five percentages sit within 250 characters of "sUSDS": its own 3.80%, a fixed-yield 5.64%, an "up to 5.31%", a rewards 5.23%, and a second 3.80%. The reader chose the sUSDS card's 3.80% and the check was `MATCHES` - with one of four voting validators disagreeing. That is the model-variance limitation, in the record.
- **The gate acts on the verified yield, not the advertised one.** Lido's page `MATCHES` its vault, but the vault paid 2.21% APR, below the gate's 3.00% floor, so the allocation was refused. Sky's two pages paid 3.80% and 5.69% and were allocated to (400,000 and 250,000); a third allocation that would have passed the 1,000,000 cap was refused.
- **Registration is a consensus read and it refuses what cannot be checked.** A label the page never shows, a contract with no `convertToAssets` (USDC: the three nodes had no answer at any of the three blocks), a duplicate, a tolerance below 10 basis points, a page that is not https and a claim id with a space were each refused by the validators.
- **The first deployment taught two things and was replaced.** Its Ethena check recorded the right verdict but with two of five validators voting DISAGREE, because validators compared the whole classification rather than the decision; and the reader's choice on the five-figure page was the "up to" figure. Both are in [research/README.md](research/README.md); the deployment in this repository is the second.

## Superseded deployments

| Contract | Address | Why it is superseded |
|---|---|---|
| YieldClaim (first deployment) | `0x26A19739cbec6928F046412B44b213988043cEfa` | Deployed earlier the same day (deploy tx 0x2d03d46f…). Validators compared the model's whole classification, so two readings that led to the same NOT_COMPARABLE verdict counted as a disagreement, and the reader's prompt did not say the figures were listed nearest the product's name first. The code differs in `_decision_key` and the prompt only; its proof is kept in studio-next/live_proof_superseded_v1.json. |
| VaultGate and the strict VaultGate (first deployment) | `0x5A3256946F30d566e1825Ab6eDC82fe4da7A0DAe and 0xA289270C51fdb228563b66fba10E8917B43eDDB1` | Constructed with the superseded YieldClaim's address. |

## Proven in tests, not live

Direct Mode proves these on the captured pages and on-chain values (and on edited copies of them, marked SYNTHETIC in the tests); none has a live transaction:

- **The consensus boundary**: a validator rejecting a leader whose chain facts, block, quote or decision differ from its own, and accepting an honest one. Direct Mode runs the validator function against changed inputs; the live run shows the committee's votes on an honest leader, including the dissent in section 3.
- **Every format refusal** not listed in section 2, the tolerance bounds, claim ids, labels, vault and call formats, and the page-url rules.
- **Weekly and monthly windows**: the 30-day window and averages (`AVG_7D`, `AVG_30D`), an unspecified basis, qualified figures, and the periods that are not compared.
- **One node down, two nodes down, a node that lies about a price or a timestamp, a node without an old block, a window the blocks do not cover**: the chain read's fail-closed branches.
- **The gate's age rule for a check dated in the future, a floor exactly met, a cap exactly met**, and the owner-only rule (every live call came from the owner). VaultGate's logic after its read of YieldClaim is also run in Direct Mode against a stand-in with `get_standing`'s exact shape; the live section shows the same refusals against the real contract.
- The language model is never run in Direct Mode: it is replaced by a reader that chooses the figure a test names. What the live run shows is the real validators' models choosing and classifying figures, with the votes in the tables above.
