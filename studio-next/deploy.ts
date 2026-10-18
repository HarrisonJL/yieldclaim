// npx tsx deploy.ts <contract file in ../contracts> [constructor args as JSON]
import * as fs from "fs";
import { client, fees, waitDecided, EXPLORER } from "./lib";

async function main() {
  const file = process.argv[2] ?? "yield_claim_studio_next.py";
  // Arguments are JSON; a string like "1000000n" is a BigInt (a u256 must be one when it reaches the contract).
  const args = process.argv[3] ? JSON.parse(process.argv[3], (_k, v) => (typeof v === "string" && /^\d+n$/.test(v) ? BigInt(v.slice(0, -1)) : v)) : [];
  const c = client();
  console.log(`Deploying ${file} ${JSON.stringify(args, (_k, v) => (typeof v === "bigint" ? v.toString() + "n" : v))} as ${c.account.address}`);
  const code = fs.readFileSync(`../contracts/${file}`, "utf-8");
  const hash = await c.deployContract({ code, args, fees: await fees(c) });
  console.log(`Deploy tx: ${hash}`);
  const tx = await waitDecided(c, hash);
  console.log(`Result: ${tx.txExecutionResultName ?? tx.result_name}`);
  console.log(`Contract address: ${tx.to_address ?? tx.recipient}`);
  console.log(`${EXPLORER}/tx/${hash}`);
  process.exit(0);
}
main().catch((e) => {
  console.error(e);
  process.exit(1);
});
