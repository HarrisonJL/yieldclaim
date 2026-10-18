import { client, write } from "../studio-next/lib";
const P = "0xe68c541d584C72E4Cd9Aa747b88c72091db2cf5e";
const SYM = "0x95d89b41";
const call = (to: string, data: string, block = "latest") => ({ jsonrpc: "2.0", id: 1, method: "eth_call", params: [{ to, data }, block] });
const C2A = "0x07a2d13a0000000000000000000000000000000000000000000000000de0b6b3a7640000";
const SUSDS = "0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD";
const yieldPages = [
  { url: "https://spark.fi", needles: ['"ssr":"', "ssr30DaysAvg"] },
  { url: "https://sky.money", needles: ["stUSDS", "% APY", "Sky Savings Rate"] },
  { url: "https://ethena.fi", needles: ["Avg sUSDe APY", "12% APY"] },
  { url: "https://ethena.fi/api/yields/protocol-and-staking-yield", needles: ["avg30dSusdeYield", "avgSusdeYieldFromInception"] },
  { url: "https://lido.fi", needles: ["APR"] },
];
const tokenPages = [
  { url: "https://developers.circle.com/stablecoins/usdc-contract-addresses", needles: ["0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "not issued or backed by Circle", "Testnet tokens"] },
  { url: "https://tether.to/en/supported-protocols/", needles: ["0xdAC17F958D2ee523a2206206994597C13D831ec7", "Deprecated Asset Protocols"] },
  { url: "https://docs.paxos.com/guides/stablecoin/pyusd/mainnet", needles: ["0x6c3ea9036406852006290770BEdFcAbA0e23A0e8"] },
  { url: "https://api.coingecko.com/api/v3/coins/usd-coin?localization=false&tickers=false&market_data=false&community_data=false&developer_data=false", needles: ['"base":"0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"', '"platforms"'] },
];
const rpc = [
  { url: "https://eth.drpc.org", body: [call(SUSDS, C2A, "0x18f5020"), { jsonrpc: "2.0", id: 2, method: "eth_getBlockByNumber", params: ["finalized", false] }] },
  { url: "https://eth.blockscout.com/api/eth-rpc", body: call(SUSDS, C2A, "0x18f5020") },
  { url: "https://ethereum-rpc.publicnode.com", body: call("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", SYM) },
  { url: "https://arbitrum.drpc.org", body: call("0xaf88d065e77c8cC2239327C5EDb3A432268e5831", SYM) },
  { url: "https://arbitrum-one-rpc.publicnode.com", body: call("0xaf88d065e77c8cC2239327C5EDb3A432268e5831", SYM) },
  { url: "https://base.drpc.org", body: call("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", SYM) },
  { url: "https://base-rpc.publicnode.com", body: call("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", SYM) },
];
(async () => {
  const c = client();
  const which = process.argv[2];
  if (which === "yield") await write(c, P, "probe_get", [JSON.stringify(yieldPages)]);
  if (which === "token") await write(c, P, "probe_get", [JSON.stringify(tokenPages)]);
  if (which === "rpc") await write(c, P, "probe_rpc", [JSON.stringify(rpc)]);
  process.exit(0);
})();
