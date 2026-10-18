"""
Captures the real inputs the tests run on, byte for byte, with a manifest of where each came from.

  pages   the product pages YieldClaim reads (fetched the way a validator fetches: plain GET, user-agent
          "reqwest"), stored as they were served. The 3 MB lido.fi page is stored gzip-compressed.
  chain   the on-chain index values YieldClaim compares (ERC-4626 convertToAssets, wstETH.stEthPerToken) at
          three pinned finalized-chain blocks - now, 7 and 30 days earlier - read from THREE independent
          keyless archive RPCs, which must agree. A pinned historical block never changes, so these
          values are the same whenever the tests run.

Usage:  python3 scripts/capture_fixtures.py [pages|chain|all]      (needs network; the tests do not)
"""
import gzip
import hashlib
import json
import pathlib
import sys
import urllib.request
from datetime import datetime, timezone

FIX = pathlib.Path(__file__).resolve().parent.parent / "tests" / "fixtures"
UA = "reqwest"
PAGES = {
    "sky_susds.html": "https://sky.money/susds",
    "sky_stusds.html": "https://sky.money/stusds",
    "sky_home.html": "https://sky.money/",
    "ethena_home.html": "https://ethena.fi/",
    "lido_home.html.gz": "https://www.lido.fi/",
}
RPCS = ["https://eth.drpc.org", "https://gateway.tenderly.co/public/mainnet", "https://eth-pokt.nodies.app"]
E18 = "%064x" % 10 ** 18
CONVERT = "0x07a2d13a" + E18                      # convertToAssets(1e18): what one whole share is worth
PRODUCTS = {
    "sUSDS": ("0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD", CONVERT),
    "stUSDS": ("0x99CD4Ec3f88A45940936F469E4bB72A2A701EEB9", CONVERT),
    "sUSDe": ("0x9D39A5DE30e57443BfF2A8307A4256c8797A3497", CONVERT),
    "wstETH": ("0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0", "0x035faf82"),   # stEthPerToken()
}
BLOCKS_PER_DAY = 7200


def rpc(url, method, params):
    req = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                                 headers={"content-type": "application/json", "user-agent": UA})
    return json.load(urllib.request.urlopen(req, timeout=40))["result"]


def pages():
    manifest = {}
    for name, url in PAGES.items():
        req = urllib.request.Request(url, headers={"user-agent": UA})
        resp = urllib.request.urlopen(req, timeout=60)
        raw = resp.read()
        if resp.headers.get("content-encoding") == "gzip":
            raw = gzip.decompress(raw)
        stored = gzip.compress(raw, 9, mtime=0) if name.endswith(".gz") else raw
        (FIX / ("page_" + name)).write_bytes(stored)
        manifest[name] = {"url": url, "status": resp.status, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                          "captured": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
        print(name, len(raw))
    return manifest


def chain():
    heads = [int(rpc(u, "eth_getBlockByNumber", ["finalized", False])["number"], 16) for u in RPCS]
    now = min(heads)
    blocks = [now, now - 7 * BLOCKS_PER_DAY, now - 30 * BLOCKS_PER_DAY]
    out = {"captured": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "rpcs": RPCS, "finalized": heads,
           "now": now, "blocks": {}, "calls": {}}
    for b in blocks:
        seen = {json.dumps(rpc(u, "eth_getBlockByNumber", [hex(b), False]), sort_keys=True) and int(rpc(u, "eth_getBlockByNumber", [hex(b), False])["timestamp"], 16) for u in RPCS}
        assert len(seen) == 1, f"RPCs disagree on block {b} timestamp: {seen}"
        out["blocks"][str(b)] = seen.pop()
    for name, (addr, data) in PRODUCTS.items():
        out["calls"][name] = {"vault": addr, "calldata": data, "values": {}}
        for b in blocks:
            vals = {rpc(u, "eth_call", [{"to": addr, "data": data}, hex(b)]) for u in RPCS}
            assert len(vals) == 1, f"RPCs disagree on {name} at {b}: {vals}"
            out["calls"][name]["values"][str(b)] = vals.pop()
    (FIX / "chain.json").write_text(json.dumps(out, indent=1) + "\n")
    print("chain: now", now, {n: [int(v, 16) for v in c["values"].values()] for n, c in out["calls"].items()})


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    manifest = json.loads((FIX / "manifest.json").read_text()) if (FIX / "manifest.json").exists() else {}
    if what in ("pages", "all"):
        manifest["pages"] = pages()
    if what in ("chain", "all"):
        chain()
    (FIX / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
