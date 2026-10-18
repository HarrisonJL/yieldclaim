// npx tsx read.ts <address> <function> '<json args array>'   (one view call, printed as JSON)
import { readClient, safeJson } from "./lib";
async function main() {
  const out = await readClient().readContract({ address: process.argv[2], functionName: process.argv[3], args: JSON.parse(process.argv[4] ?? "[]") });
  console.log(JSON.stringify(JSON.parse(safeJson(out)), null, 1));
  process.exit(0);
}
main().catch((e) => { console.error(e?.shortMessage ?? e?.message ?? e); process.exit(1); });
