// Read-only: validates the Studio Next contract against the live runner's
// import conventions before spending a real deploy on it.
import * as fs from "fs";
import { client, safeJson } from "./lib";

async function main() {
  const file = process.argv[2] ?? "yield_claim_studio_next.py";
  const c = client();
  const code = fs.readFileSync(`../contracts/${file}`, "utf-8");
  try {
    const schema = await c.getContractSchemaForCode(code);
    console.log("Schema check PASSED:", safeJson(schema).slice(0, 1500));
  } catch (err: any) {
    console.log("Schema check FAILED:", err?.shortMessage || err?.message || String(err));
    process.exit(1);
  }
  process.exit(0);
}
main().catch((e) => {
  console.error(e);
  process.exit(1);
});
