// Keeps the official claims' standings fresh. A consumer wants a decided check no older than a day or so; left
// alone, the official claims' standings age out. This asks YieldClaim for a fresh check of every checked claim its
// deployer registered: one consensus transaction each, in which every validator reads the page and the vault's
// share price. (A claim nobody has checked is left alone: the proof keeps one unchecked on purpose.) Checks are permissionless, so it signs with a throwaway testnet account created for this run and
// funded from Studio Next's faucet: no stored key, nothing to leak.
//
//   npx tsx refresh.ts [claim ...]      (all of the deployer's claims, or just those named)
import * as crypto from "crypto";
import * as fs from "fs";
import { createAccount, createClient, chains } from "genlayer-js";
import { fees, safeJson, waitDecided, EXPLORER } from "./lib";

const chain: any = (chains as any).studioDevnet;
const deployment = JSON.parse(fs.readFileSync(`${__dirname}/deployment.json`, "utf-8"));
const YIELDCLAIM: string = deployment.yieldclaim.address;
const OWNER: string = deployment.deployer.toLowerCase();
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function rpc(method: string, params: unknown[]) {
  const r = await fetch(chain.rpcUrls.default.http[0], {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
  });
  const j: any = await r.json();
  if (j.error) throw new Error(`${method}: ${j.error.message}`);
  return j.result;
}

async function main() {
  const account = createAccount(`0x${crypto.randomBytes(32).toString("hex")}` as `0x${string}`);
  const c: any = createClient({ chain, account });
  await rpc("sim_fundAccount", [account.address, 100000000000000000000]);
  console.log(`throwaway account ${account.address}, funded from the faucet`);

  // Studio Next allows 30 reads a minute: pace them.
  const view = async (address: string, fn: string, args: unknown[] = []) => {
    await sleep(2200);
    return JSON.parse(safeJson(await c.readContract({ address, functionName: fn, args })));
  };
  const claims: string[] = (await view(YIELDCLAIM, "list_claims")).filter((k: any) => k.registrant.toLowerCase() === OWNER && k.check_count > 0).map((k: any) => k.claim_id);
  console.log(`YieldClaim ${YIELDCLAIM}: ${claims.length} official claims`);
  const only = process.argv.slice(2);
  const todo = claims.filter((id) => only.length === 0 || only.includes(id));

  const failed: string[] = [];
  for (const id of todo) {
    try {
      const hash = await c.writeContract({ address: YIELDCLAIM, functionName: "check", args: [id], fees: await fees(c) });
      const tx = await waitDecided(c, hash);
      const ok = String(tx.status) === "5" || String(tx.status) === "7";
      const standing = ok ? await view(YIELDCLAIM, "get_standing", [id]) : null;
      console.log(`${id}: status ${tx.status} ${tx.txExecutionResultName ?? ""} ${standing ? standing.verdict + " " + (standing.gap_bps ?? "") : ""} ${EXPLORER}/tx/${hash}`);
      if (!ok || tx.txExecutionResultName !== "FINISHED_WITH_RETURN") failed.push(id);
    } catch (e: any) {
      console.log(`${id}: ${e?.shortMessage ?? e?.message ?? e}`);
      failed.push(id);
    }
  }
  if (failed.length) {
    console.log(`not refreshed: ${failed.join(", ")}`);
    process.exit(1);
  }
  process.exit(0);
}

main().catch((e) => {
  console.error(e?.shortMessage ?? e?.message ?? e);
  process.exit(1);
});
