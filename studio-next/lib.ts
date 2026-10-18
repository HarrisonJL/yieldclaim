// Shared helpers for the Studio Next scripts.
import { createClient, createAccount, chains } from "genlayer-js";
import "dotenv/config";

export const EXPLORER = "https://explorer-studio-dev.genlayer.com";

export function client(keyVar = "DEPLOYER_PRIVATE_KEY"): any {
  const rawKey = process.env[keyVar];
  if (!rawKey) throw new Error(`${keyVar} is not set (see .env.example)`);
  const account = createAccount((rawKey.startsWith("0x") ? rawKey : `0x${rawKey}`) as `0x${string}`);
  return createClient({ chain: (chains as any).studioDevnet, account });
}

export function readClient(): any {
  return createClient({ chain: (chains as any).studioDevnet });
}

export async function fees(c: any) {
  const f = await c.estimateTransactionFees({});
  return { distribution: f.distribution, feeValue: f.feeValue };
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
// Decided statuses: ACCEPTED, UNDETERMINED, FINALIZED, CANCELED,
// VALIDATORS_TIMEOUT, LEADER_TIMEOUT. Polled directly because
// waitForTransactionReceipt({waitUntil: "accepted"}) can miss a transaction
// that jumps straight to FINALIZED (seen live on Studio Next).
const DECIDED = new Set(["5", "6", "7", "8", "12", "13"]);

export async function waitDecided(c: any, hash: string, maxSeconds = 600): Promise<any> {
  const started = Date.now();
  let last = "";
  while ((Date.now() - started) / 1000 < maxSeconds) {
    try {
      const tx: any = await c.getTransaction({ hash });
      const s = String(tx.status);
      if (s !== last) {
        console.log(`   status ${s} (${Math.round((Date.now() - started) / 1000)}s)`);
        last = s;
      }
      if (DECIDED.has(s)) return tx;
    } catch {
      // not indexed yet right after submission - keep polling
    }
    await sleep(5000);
  }
  throw new Error(`transaction ${hash} not decided after ${maxSeconds}s`);
}

export function safeJson(value: unknown, indent?: number): string {
  return JSON.stringify(value, (_k, v) => (typeof v === "bigint" ? v.toString() : v instanceof Map ? Object.fromEntries(v) : v), indent);
}

export async function write(c: any, address: string, functionName: string, args: unknown[]) {
  const hash = await c.writeContract({ address, functionName, args, fees: await fees(c) });
  console.log(`${functionName}(${safeJson(args)}) -> ${hash}`);
  const tx = await waitDecided(c, hash);
  const votes = tx.last_round?.validator_votes_name ?? [];
  console.log(`   ${tx.txExecutionResultName ?? tx.result_name} votes=${safeJson(votes)} ${EXPLORER}/tx/${hash}`);
  return { hash, tx };
}
