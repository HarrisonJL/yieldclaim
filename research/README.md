# Research notes

What was checked before YieldClaim was built, what the data showed, and the decisions that followed. Dates are 2026-10-18 unless stated. Everything here can be re-run: the captured inputs are in [`tests/fixtures/`](../tests/fixtures/), the probe that asked Studio Next's validators what they can reach is in this folder.

## Is it already done?

The GenLayer portal publishes its accepted Projects (`/api/v1/explorer/`, 213 on the day). I searched their descriptions for yield, APY, vault, reserve, collateral, treasury and listing language, and searched GitHub for GenLayer contracts about yield. Nothing compares a product page's advertised yield with what the vault paid. The nearest are:

| Project | What it does | Why it is not this |
|---|---|---|
| Reserve Lens | assets against liabilities from two reports, a coverage ratio | solvency, not yield; both sides are web reports |
| Pride | a promise recorded against a later commit of the same source | the promise is text against text |
| OpenProof | what a project promised against what its contract showed on a date (`owner()`, `unlockTime()`, an EIP-1967 slot) | reads fixed fields, not a rate, and does no arithmetic over a window |
| Collateral Guard | a 5-source price ratio for a loan position | prices, not yields |
| ChangeProof | whether a page changed | no on-chain side |

Unaccepted submissions are not visible, so this is a search, not a proof of absence.

## What the validators can reach (step 0)

A throwaway probe contract ([`probe_studio_next.py`](probe_studio_next.py), deployed at `0xe68c541d584C72E4Cd9Aa747b88c72091db2cf5e`) asked Studio Next's validators to fetch each candidate source, because a source can answer a validator (a US-region sandbox) differently from a laptop. [`probe_run.ts`](probe_run.ts) sent three transactions; the raw answers are in [`probe_results.json`](probe_results.json).

| Source | What the validators received |
|---|---|
| `eth.drpc.org`, `gateway.tenderly.co/public/mainnet`, `eth-pokt.nodies.app` (POST, JSON-RPC) | `eth_call` at a historical block and `eth_getBlockByNumber` both answered; `gl.nondet.web.post` works |
| `ethereum-rpc.publicnode.com` | answers `eth_call` at the head but refuses archive state ("requires a personal token"), so it cannot be a source |
| `eth.blockscout.com/api/eth-rpc` | answered a handful of calls, then returned HTTP 429 to everything, including a 20-call burst. Not used |
| `sky.money/susds`, `/stusds`, `/` | 200; the rate is in the server-rendered text |
| `www.lido.fi/` (3.1 MB) | 200; "2.2% APR*" is in the server-rendered text |
| `ethena.fi/` | 200; the home page's only yield figure is "~12% APY" promotional rewards. The headline "Avg sUSDe APY" is filled in by the browser, so it is not on the page a validator reads |
| `spark.fi` | 200, but its rate is inside a script's JSON, not in the visible text |

Archive support across keyless public Ethereum RPCs, tested with a 30-day-old `eth_call`: dRPC, Tenderly (two hostnames, one operator), Nodies/POKT and Blast answered; publicnode, 1RPC, bloXroute, NOWNodes and Meowrpc did not. A burst of 20 historical calls to each of the first four ran without a single rate limit. YieldClaim uses dRPC, Tenderly and Nodies: three operators.

## What the real vaults paid, against what their pages say

Read on 2026-10-18 at the latest finalized block (26,219,945) and 7 and 30 days earlier, by all three nodes, which agreed to the last digit. APY here is daily compounding of the simple annualised growth.

| Product | The page says | Vault paid, 7 days | Vault paid, 30 days |
|---|---|---|---|
| sUSDS (`sky.money/susds`) | 3.80% APY | 3.73% APR / **3.80% APY** | 3.61% APR / 3.67% APY |
| stUSDS (`sky.money/stusds`) | 5.64% APY | 5.54% APR / **5.70% APY** | 5.15% APR / 5.29% APY |
| stETH via wstETH (`www.lido.fi`) | 2.2% APR* | **2.21% APR** / 2.24% APY | 2.30% APR / 2.33% APY |
| sUSDe (`ethena.fi`) | ~12% APY, promotional rewards on Aave | 4.70% APR / 4.82% APY | 4.78% APR / 4.90% APY |

(Figures are the contract's own, in basis points rounded down; the bold one is the figure each page's basis and period is graded against.)

Three of the four pages state a figure the vault actually paid, to within six basis points (stUSDS: 5.64% against 5.70%). The fourth states a figure that is not the vault's yield at all (it is a promotion on a lending market), which is the case YieldClaim must call `NOT_COMPARABLE` and not `OVERSTATED`. There was no real page in this snapshot that overstated its yield, so the proof's `OVERSTATED` and `UNDERSTATED` rows use two synthetic pages ([`demo/`](../demo/)), marked as such everywhere they appear.

## Decisions

- **The claim is graded on its own basis.** A page that says APR is compared with the vault's simple annualised growth, one that says APY with the daily-compounded figure. If the page does not say, the basis closer to its figure gets the benefit of the doubt; a tie goes to the lower, so a tie never helps the page.
- **"Current" means the last 7 days.** A rate that moved sharply during the week can read as a mismatch that is really a lag. This is stated as a limitation, not hidden.
- **Only comparable figures are graded.** "Up to", promotional, fixed-term, reward-token and leveraged figures, and averages over other periods, are `NOT_COMPARABLE`: a share price cannot refute them. The realised yield is still recorded beside them.
- **The reader chooses, it does not write.** Plain code finds every percentage near the product's name and marks it in its sentence; the model picks one (or none) and classifies it. The number stored is always a figure the page shows, taken from the page by code. A prompt-injection in the page can steer a choice among the page's own figures and nothing else.
- **Block selection.** The leader pins the lowest finalized head among the nodes; a validator accepts it only if some node has finalized it and it is within 1,800 blocks (about six hours) of the head, then re-reads everything at that block. A historical block never changes, so agreement is exact.
- **Quotes are short on purpose.** A recorded quote is the figure with six words before and one after. Lido's sentence continues with a TVL that changes every few seconds, and a longer quote would stop being found in a second validator's copy of the page.
- **Dropped**: reading a JSON API for the claim (Ethena publishes one; a second mode doubles the surface to audit), other chains (no second keyless archive trio was tested), and rebasing tokens (their balance, not a share price, grows).

## What the first live run taught

The first deployment (`0x26A19739cbec6928F046412B44b213988043cEfa`, superseded; its proof is kept in [`studio-next/live_proof_superseded_v1.json`](../studio-next/live_proof_superseded_v1.json)) read the three unambiguous pages with every voting validator agreeing, and the two hard ones with splits:

- **Ethena's home page** recorded `NOT_COMPARABLE` with **two of five validators voting DISAGREE**. The leader's model found no headline rate; the others' models read the "~12% APY" as a promotion. Both lead to the same verdict, but the validator compared the whole classification, so a harmless difference counted as a disagreement.
- **Sky's home page**, five figures near "sUSDS", recorded the **"Up to 5.31% APY"** figure as the leader's choice (`NOT_COMPARABLE`) with one disagreement, when the card for sUSDS shows 3.80%.

Two changes followed, and the second deployment (the one in this repository) was proven from scratch:

1. **Validators compare the decision a consumer acts on.** A comparable figure is identified by its number, basis and period; anything that cannot be compared (no headline rate, a qualified figure, another period) is one decision, however the model reached it. A validator still rejects a leader that found a plain rate when its own model sees none, or the reverse.
2. **The reader is told the figures are listed nearest the product's name first, and to prefer a plain current rate to a maximum, a promotion or an average.**

Result on the same pages: Ethena's check had all three voting validators agree on `NOT_COMPARABLE`, and Sky's home page chose the 3.80% figure (`MATCHES`), with one of four voting validators still disagreeing. That page, with several products' figures side by side, remains the hard case: register the product's own page and a specific label.
