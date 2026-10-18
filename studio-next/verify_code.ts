// Confirms the code deployed at <address> is byte-identical to a source file
// in ../contracts (same SHA-256), fetched straight from the chain.
//
//   npx tsx verify_code.ts <address> [yield_claim_studio_next.py]
import * as crypto from "crypto";
import * as fs from "fs";
import { readClient } from "./lib";

async function main() {
  const address = process.argv[2];
  const file = process.argv[3] ?? "yield_claim_studio_next.py";
  if (!address) throw new Error("usage: verify_code.ts <address> [file]");
  let onchain: any = await readClient().getContractCode(address);
  if (typeof onchain !== "string") onchain = Buffer.from(onchain).toString("utf-8");
  const local = fs.readFileSync(`../contracts/${file}`, "utf-8");
  const sha = (s: string) => crypto.createHash("sha256").update(s).digest("hex");
  console.log(`on-chain  sha256 ${sha(onchain)} (${onchain.length} chars)`);
  console.log(`${file} sha256 ${sha(local)} (${local.length} chars)`);
  console.log(onchain === local ? "IDENTICAL" : "DIFFERENT");
  process.exit(onchain === local ? 0 : 1);
}
main().catch((e) => {
  console.error(e?.shortMessage ?? e?.message ?? e);
  process.exit(1);
});
