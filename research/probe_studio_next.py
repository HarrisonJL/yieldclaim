# v0.3.0
# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }

# Throwaway connectivity probe (week of 2026-10-19) - not a submission. Records what a validator's
# fetcher receives for YieldClaim's and TokenOrigin's candidate sources: whether each page contains
# the strings those contracts would rely on, and what JSON-RPC nodes return for (historical) calls.

import genlayer as gl
from genlayer.types import *
from genlayer.storage import DynArray
import json
import hashlib


class Probe2(gl.contract.Contract):
    results: DynArray[str]

    def __init__(self) -> None:
        pass

    @gl.public.write
    def probe_get(self, items_json: str) -> None:
        items = json.loads(items_json)

        def leader_fn() -> str:
            out = []
            for it in items:
                url = it["url"]
                try:
                    ua = it.get("ua", "")
                    r = gl.nondet.web.get(url, headers={"user-agent": ua}) if ua else gl.nondet.web.get(url)
                    body = r.body or b""
                    text = body.decode("utf-8", "replace")
                    low = text.lower()
                    found = {}
                    for n in it.get("needles", []):
                        i = low.find(n.lower())
                        found[n] = None if i < 0 else text[max(0, i - 90):i + len(n) + 90]
                    out.append({"url": url, "status": r.status, "len": len(body),
                                "sha256": hashlib.sha256(body).hexdigest()[:16],
                                "ctype": str(r.headers.get("content-type", b""))[:50], "found": found})
                except Exception as e:
                    out.append({"url": url, "error": repr(e)[:300]})
            return json.dumps(out)

        def validator_fn(leaders_res) -> bool:
            return isinstance(leaders_res, gl.vm.Return)

        self.results.append(gl.vm.run_nondet(leader_fn, validator_fn))

    @gl.public.write
    def probe_rpc(self, calls_json: str) -> None:
        calls = json.loads(calls_json)

        def leader_fn() -> str:
            out = []
            for c in calls:
                try:
                    r = gl.nondet.web.post(c["url"], body=json.dumps(c["body"]), headers={"content-type": "application/json"})
                    b = (r.body or b"").decode("utf-8", "replace")
                    out.append({"url": c["url"], "status": r.status, "body": b[:600]})
                except Exception as e:
                    out.append({"url": c["url"], "error": repr(e)[:300]})
            return json.dumps(out)

        def validator_fn(leaders_res) -> bool:
            return isinstance(leaders_res, gl.vm.Return)

        self.results.append(gl.vm.run_nondet(leader_fn, validator_fn))

    @gl.public.view
    def get_results(self) -> list:
        return [r for r in self.results]
