// npx tsx call.ts <address> <function> '<json args array>'   (one write, printed with its decided status and revert text)
import { client, write, safeJson } from "./lib";
async function main() {
  const [address, fn, args] = [process.argv[2], process.argv[3], JSON.parse(process.argv[4] ?? "[]")];
  const { hash, tx } = await write(client(), address, fn, args);
  console.log("HASH", hash, "RESULT", tx.txExecutionResultName ?? tx.result_name);
  const text = safeJson(tx);
  const m = text.match(/(claim refused: [^"\\]*|[^"\\]*refused: [^"\\]*|[^"\\]*already[^"\\]*|only the owner[^"\\]*|unknown claim_id)/);
  if (m) console.log("REVERT", m[0]);
  process.exit(0);
}
main().catch((e) => { console.error(e?.shortMessage ?? e?.message ?? e); process.exit(1); });
