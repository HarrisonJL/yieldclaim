"""
The world the contract can reach, for Direct Mode: pages (GET) and JSON-RPC nodes (POST) answered from the
captured fixtures, and a stand-in for the validators' language model.

genlayer-test's web mocks match a URL only, but a JSON-RPC node is one URL answering many questions, so the
tests install a handler (Direct Mode's `_live_web_handler` / `_live_llm_handler` hooks) that reads the request
body like a node would. Everything it serves is real captured data (scripts/capture_fixtures.py); a scenario
that needs something the real world did not do edits one field of a real response and says so.
"""

import gzip
import json
import pathlib
import re

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
CHAIN = json.loads((FIXTURES / "chain.json").read_text())
NOW_BLOCK = CHAIN["now"]
BLOCKS = {int(k): v for k, v in CHAIN["blocks"].items()}
RPCS = tuple(CHAIN["rpcs"])

PAGE_FILES = {
    "https://sky.money/susds": "page_sky_susds.html",
    "https://sky.money/stusds": "page_sky_stusds.html",
    "https://sky.money/": "page_sky_home.html",
    "https://ethena.fi/": "page_ethena_home.html",
    "https://www.lido.fi/": "page_lido_home.html.gz",
}


def page_bytes(url: str) -> bytes:
    raw = (FIXTURES / PAGE_FILES[url]).read_bytes()
    return gzip.decompress(raw) if PAGE_FILES[url].endswith(".gz") else raw


# The real vaults whose share price was captured at the three pinned blocks.
VAULTS = {name: (c["vault"].lower(), c["calldata"]) for name, c in CHAIN["calls"].items()}
PRICES = {name: {int(b): v for b, v in c["values"].items()} for name, c in CHAIN["calls"].items()}


class Node:
    """One archive node. Real data by default; a field can be bent to make it fail or lie."""

    def __init__(self):
        self.head = NOW_BLOCK
        self.down = False            # connection refused
        self.status = 200            # HTTP status of every answer
        self.rpc_error = False       # answers every call with a JSON-RPC error
        self.junk = False            # answers with something that is not JSON
        self.also_error = False      # puts an error object beside every real result
        self.price_offset = {}       # block -> amount added to the price word (a node that disagrees)
        self.ts_offset = {}          # block -> seconds added to the block timestamp
        self.missing_blocks = set()  # blocks it claims not to have
        self.calls = 0


class World:
    def __init__(self):
        self.pages = {}              # url -> (status, bytes)
        self.page_down = set()       # urls whose connection fails
        self.nodes = {url: Node() for url in RPCS}
        self.reader = None           # callable(label, candidates, url) -> dict | str | None
        self.reader_calls = 0
        self.prompts = []
        self.vaults = dict(VAULTS)   # name -> (vault, calldata)

    # --- Pages ---------------------------------------------------------------

    def serve(self, url: str, body=None, status: int = 200):
        self.pages[url] = (status, page_bytes(url) if body is None else (body.encode() if isinstance(body, str) else body))

    # --- Nodes ---------------------------------------------------------------

    def _answer(self, node: Node, request: dict):
        method, params = request["method"], request["params"]
        if node.rpc_error:
            return {"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "historical state is not available"}}
        if method == "eth_getBlockByNumber":
            tag = params[0]
            number = node.head if tag == "finalized" else int(tag, 16)
            if tag != "finalized" and (number not in BLOCKS or number in node.missing_blocks):
                return {"jsonrpc": "2.0", "id": 1, "result": None}
            ts = BLOCKS.get(number, 1_792_000_000) + node.ts_offset.get(number, 0)
            return {"jsonrpc": "2.0", "id": 1, "result": {"number": hex(number), "timestamp": hex(ts), "hash": "0x" + "ab" * 32}}
        if method == "eth_call":
            call, tag = params[0], params[1]
            number = int(tag, 16)
            for name, (vault, data) in self.vaults.items():
                if call["to"].lower() == vault and call["data"].lower() == data.lower() and number in PRICES.get(name, {}):
                    word = int(PRICES[name][number], 16) + node.price_offset.get(number, 0)
                    return {"jsonrpc": "2.0", "id": 1, "result": "0x" + "%064x" % word}
            return {"jsonrpc": "2.0", "id": 1, "error": {"code": 3, "message": "execution reverted"}}
        return {"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "method not found"}}

    # --- The hooks Direct Mode calls ---------------------------------------------

    def handle(self, data: dict):
        url, method = data["url"], data.get("method", "GET")
        if method == "POST":
            node = self.nodes.get(url)
            if node is None:
                return {"ok": {"response": {"status": 404, "headers": {}, "body": b""}}}
            node.calls += 1
            if node.down:
                raise ConnectionError("connection refused")
            if node.junk:
                return {"ok": {"response": {"status": 200, "headers": {}, "body": b"<html>gateway error</html>"}}}
            body = data["body"]
            request = json.loads(body.decode() if isinstance(body, bytes) else body)
            answer = self._answer(node, request)
            if node.also_error:
                answer["error"] = {"code": -32000, "message": "an error beside a result"}
            return {"ok": {"response": {"status": node.status, "headers": {}, "body": json.dumps(answer).encode()}}}
        if url in self.page_down:
            raise ConnectionError("connection refused")
        status, body = self.pages.get(url, (404, b""))
        return {"ok": {"response": {"status": status, "headers": {}, "body": body}}}

    def llm(self, data: dict):
        prompt = data["prompt"]
        self.prompts.append(prompt)
        self.reader_calls += 1
        label = re.search(r'Product: "([^"]*)"', prompt).group(1)
        url = re.search(r"Page: (\S+)", prompt).group(1)
        listing = prompt.split("--- BEGIN UNTRUSTED PAGE TEXT ---\n")[1].split("\n--- END UNTRUSTED PAGE TEXT ---")[0]
        candidates = [re.sub(r"^\[\d+\] ", "", line) for line in listing.split("\n")]
        answer = self.reader(label, candidates, url) if self.reader else None
        return {"ok": answer}

    def install(self, direct_vm):
        direct_vm._live_web_handler = self.handle
        direct_vm._live_llm_handler = self.llm


def pick(candidates: list, number: str, near: str = "") -> int:
    """The index of the first candidate (as the reader is shown them) whose MARKED figure is `number`, optionally near some words."""
    for i, context in enumerate(candidates):
        if re.search("\u00ab" + re.escape(number) + "\\s?%\u00bb", context) and near in context:
            return i
    raise AssertionError(f"no candidate marked {number}% near {near!r} in {candidates}")


def reader_for(number, basis="APY", period="CURRENT", qualifier="NONE", near=""):
    """A reader that chooses the figure `number` and classifies it as given (index None = 'none of these')."""
    def read(label, candidates, url):
        if number is None:
            return {"index": None, "basis": basis, "period": period, "qualifier": qualifier}
        return {"index": pick(candidates, number, near), "basis": basis, "period": period, "qualifier": qualifier}
    return read
