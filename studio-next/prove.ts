// Reproducible live proof for YieldClaim. Every step's tx hash, result, votes and the contract's recorded
// output are appended to live_proof.json - the source for CONTRACT.md's tables. Steps already in
// live_proof.json are skipped and each run stops at a time budget, so a stall costs nothing: run the same
// command again.
//
//   npx tsx prove.ts <yieldclaim> <phase> [vaultgate] [strict vaultgate]     (the gates' addresses, or - )
//   phases: register | check | gate | demo | read
//     register  four real product pages, each with its vault, and every refusal registration has
//     check     one consensus read of each (page + three archive nodes + the reader)
//     gate      VaultGate allocating to claims, and every refusal it has; needs the two gates' addresses
//     demo      SYNTHETIC pages (demo/*.html in the repo) that claim 12% and 1% for the sUSDS vault, and the gate refusing the first
//     read      the final state, for CONTRACT.md
import * as fs from "fs";
import { client, readClient, write, safeJson } from "./lib";

const CONVERT = "0x07a2d13a" + (10n ** 18n).toString(16).padStart(64, "0");   // convertToAssets(1e18)
const SUSDS = "0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD";
const STUSDS = "0x99CD4Ec3f88A45940936F469E4bB72A2A701EEB9";
const SUSDE = "0x9D39A5DE30e57443BfF2A8307A4256c8797A3497";
const WSTETH = "0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0";
const USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48";
const DEMO = "https://raw.githubusercontent.com/HarrisonJL/yieldclaim/main/demo/";

// [claim id, page, label, vault, rate call, tolerance bps, note, what it shows]
type Claim = [string, string, string, string, string, number, string, string];
const CLAIMS: Claim[] = [
  ["sky-susds", "https://sky.money/susds", "sUSDS", SUSDS, CONVERT, 50, "Sky Savings Rate: sUSDS", "Sky's sUSDS page against the sUSDS vault"],
  ["sky-stusds", "https://sky.money/stusds", "stUSDS", STUSDS, CONVERT, 50, "stUSDS", "Sky's stUSDS page against the stUSDS vault"],
  ["lido-steth", "https://www.lido.fi/", "staking with stETH", WSTETH, "0x035faf82", 50, "Lido staking APR", "Lido's staking APR against wstETH's stEthPerToken()"],
  ["ethena-susde", "https://ethena.fi/", "sUSDe", SUSDE, CONVERT, 50, "Ethena sUSDe", "Ethena's home page, where the only yield figure is promotional"],
  ["sky-home-susds", "https://sky.money/", "sUSDS", SUSDS, CONVERT, 50, "sUSDS on Sky's home page", "five figures near the label: the reader has to choose"],
  ["sky-ssr-unchecked", "https://sky.money/susds", "Sky Savings Rate", SUSDS, CONVERT, 50, "registered, never checked", "a claim with no check yet (for the gate)"],
];
const DEMO_CLAIMS: Claim[] = [
  ["demo-overstated", DEMO + "overstated-vault.html", "Example Vault", SUSDS, CONVERT, 50, "SYNTHETIC page: claims 12.00% for the sUSDS vault", "a page that claims far more than its vault paid"],
  ["demo-understated", DEMO + "understated-vault.html", "Example Vault", SUSDS, CONVERT, 50, "SYNTHETIC page: claims 1.00% for the sUSDS vault", "a page that claims far less than its vault paid"],
];
// Registrations the contract must refuse: [id, args, what it shows]
const REFUSALS: [string, any[], string][] = [
  ["refuse-label", ["x-label", "https://sky.money/susds", "Ethena", SUSDS, CONVERT, 50, ""], "a label the page never shows"],
  ["refuse-vault", ["x-vault", "https://sky.money/susds", "sUSDS", USDC, CONVERT, 50, ""], "a contract that has no such view (USDC has no convertToAssets)"],
  ["refuse-duplicate", ["x-dup", "https://sky.money/susds", "sUSDS", SUSDS, CONVERT, 50, ""], "the same page, label, vault and call again"],
  ["refuse-tolerance", ["x-tol", "https://sky.money/susds", "sUSDS", SUSDS, CONVERT, 5, ""], "a tolerance below the 10 basis point minimum"],
  ["refuse-http", ["x-http", "http://sky.money/susds", "sUSDS", SUSDS, CONVERT, 50, ""], "a page that is not https"],
  ["refuse-claim-id", ["bad id!", "https://sky.money/susds", "sUSDS", SUSDS, CONVERT, 50, ""], "a claim id with a space and a bang"],
];
// The gate, in order: [id, which gate, claim, amount, what it shows]
const GATE_STEPS: [string, "gate" | "strict", string, string, string][] = [
  ["g-susds", "gate", "sky-susds", "400000", "MATCHES and the vault paid 3.80% (above the 3.00% floor): allowed"],
  ["g-stusds", "gate", "sky-stusds", "250000", "MATCHES and the vault paid about 5.7%: allowed"],
  ["g-floor", "gate", "lido-steth", "100000", "MATCHES, but the vault paid 2.21%, below the gate's 3.00% floor: refused"],
  ["g-notcomparable", "gate", "ethena-susde", "1", "a promotional figure: NOT_COMPARABLE: refused"],
  ["g-cap", "gate", "sky-susds", "700000", "400,000 already allocated; 700,000 more would pass the 1,000,000 cap: refused"],
  ["g-nocheck", "gate", "sky-ssr-unchecked", "1", "registered, never checked: refused"],
  ["g-ghost", "gate", "ghost", "1", "a claim YieldClaim has never heard of: refused"],
  ["g-stale", "strict", "sky-susds", "1", "a gate that wants a check no more than a second old: refused"],
];
const DEMO_GATE_STEPS: [string, "gate" | "strict", string, string, string][] = [
  ["g-overstated", "gate", "demo-overstated", "1", "OVERSTATED: refused"],
];

function load(): any[] {
  return fs.existsSync("live_proof.json") ? JSON.parse(fs.readFileSync("live_proof.json", "utf-8")) : [];
}
function log(entry: Record<string, unknown>) {
  const all = load();
  all.push(entry);
  fs.writeFileSync("live_proof.json", JSON.stringify(all, null, 1));
}
const done = (id: string) => load().some((e) => e.id === id);

function revertMessage(tx: any): string {
  const found: string[] = [];
  const walk = (o: any) => {
    if (typeof o === "string") {
      const m = o.match(/(claim refused: [^\n"]*|[^\n"]*refused: [^\n"]*|that page, label, vault and call are already[^\n"]*|claim_id [^\n"]*|page_url must[^\n"]*|tolerance_bps must[^\n"]*|only the owner[^\n"]*|amount must[^\n"]*|unknown claim_id)/);
      if (m) found.push(m[0]);
    } else if (o && typeof o === "object") Object.values(o).forEach(walk);
  };
  walk(tx);
  return found[0] ?? "";
}

async function main() {
  const [yc, phase, gate, strict] = process.argv.slice(2);
  const c = client();
  const r = readClient();
  const votes = (tx: any) => tx.last_round?.validator_votes_name ?? [];
  const started = Date.now();
  const outOfTime = () => Date.now() - started > 330_000;
  const view = async (address: string, fn: string, args: unknown[] = []) => {
    await new Promise((res) => setTimeout(res, 2200));
    return JSON.parse(safeJson(await r.readContract({ address, functionName: fn, args })));
  };
  const stop = () => console.log("  (time budget reached - run this phase again to continue)");

  const registerAll = async (claims: Claim[], prefix: string) => {
    for (const [id, page, label, vault, call, tol, note, shows] of claims) {
      if (done(prefix + id)) continue;
      if (outOfTime()) return stop();
      const args = [id, page, label, vault, call, tol, note];
      const { hash, tx } = await write(c, yc, "register_claim", args);
      const claim = tx.txExecutionResultName === "FINISHED_WITH_RETURN" ? await view(yc, "get_claim", [id]) : null;
      log({ id: prefix + id, step: "register", args, note: shows, tx: hash, result: tx.txExecutionResultName, votes: votes(tx), revert: tx.txExecutionResultName === "FINISHED_WITH_ERROR" ? revertMessage(tx) : "", claim });
      console.log(`  register ${id}: ${tx.txExecutionResultName} ${claim ? "" : revertMessage(tx)}`);
    }
  };
  const checkAll = async (ids: string[], shows: Record<string, string>) => {
    for (const id of ids) {
      if (done("check-" + id)) continue;
      if (outOfTime()) return stop();
      const { hash, tx } = await write(c, yc, "check", [id]);
      const state = await view(yc, "get_state");
      const rec = await view(yc, "get_check", [state.check_count - 1]);
      log({ id: "check-" + id, step: "check", args: [id], note: shows[id] ?? "", tx: hash, result: tx.txExecutionResultName, votes: votes(tx), check: rec });
      console.log(`     ${id}: ${rec.verdict} ${rec.summary?.claim_bps ?? ""} vs ${rec.summary?.realised_bps ?? ""} ${(rec.reasons ?? []).join("; ")}`);
    }
  };
  const runGate = async (steps: typeof GATE_STEPS) => {
    for (const [id, which, claim, amount, note] of steps) {
      if (done(id)) continue;
      if (outOfTime()) return stop();
      const address = which === "gate" ? gate : strict;
      if (!address || address === "-") { console.log(`  ${id}: needs the ${which} gate's address`); continue; }
      // allocate(claim_id, amount_raw): the amount is a u256, so it goes as a BigInt.
      const { hash, tx } = await write(c, address, "allocate", [claim, BigInt(amount)]);
      const message = tx.txExecutionResultName === "FINISHED_WITH_ERROR" ? revertMessage(tx) : "";
      const total = await view(address, "get_total", [claim]);
      log({ id, step: "gate", which, args: [claim, amount], note, tx: hash, result: tx.txExecutionResultName, votes: votes(tx), revert: message, total });
      console.log(`  allocate(${claim}, ${amount}) on ${which} -> ${tx.txExecutionResultName} ${message}`);
    }
  };

  if (phase === "register") {
    await registerAll(CLAIMS, "reg-");
    for (const [id, args, note] of REFUSALS) {
      if (done(id)) continue;
      if (outOfTime()) return stop();
      const { hash, tx } = await write(c, yc, "register_claim", args);
      const message = tx.txExecutionResultName === "FINISHED_WITH_ERROR" ? revertMessage(tx) : "";
      log({ id, step: "refuse-register", args, note, tx: hash, result: tx.txExecutionResultName, votes: votes(tx), revert: message });
      console.log(`  ${id}: ${tx.txExecutionResultName} ${message}`);
    }
    return process.exit(0);
  }
  if (phase === "check") {
    const shows = Object.fromEntries(CLAIMS.map((x) => [x[0], x[7]]));
    await checkAll(CLAIMS.filter((x) => x[0] !== "sky-ssr-unchecked").map((x) => x[0]), shows);
    return process.exit(0);
  }
  if (phase === "demo") {
    await registerAll(DEMO_CLAIMS, "reg-");
    await checkAll(DEMO_CLAIMS.map((x) => x[0]), Object.fromEntries(DEMO_CLAIMS.map((x) => [x[0], x[7]])));
    await runGate(DEMO_GATE_STEPS);       // needs the gate's address, like the gate phase
    return process.exit(0);
  }
  if (phase === "gate") {
    await runGate(GATE_STEPS);
    return process.exit(0);
  }
  if (phase === "read") {
    const claims = await view(yc, "list_claims");
    const standings: Record<string, any> = {};
    for (const cl of claims) standings[cl.claim_id] = await view(yc, "get_standing", [cl.claim_id]);
    const state = await view(yc, "get_state");
    const rules = await view(yc, "get_rules");
    const gateConfig = gate && gate !== "-" ? await view(gate, "get_config") : null;
    const allocations = gate && gate !== "-" ? await view(gate, "get_allocations", [0, 20]) : [];
    if (!done("read")) log({ id: "read", step: "read", claims, standings, state, rules, gate_config: gateConfig, allocations });
    return process.exit(0);
  }
  console.log("phases: register | check | demo | gate | read");
  process.exit(1);
}

main().catch((e) => {
  console.error(e?.shortMessage ?? e?.message ?? e);
  process.exit(1);
});
