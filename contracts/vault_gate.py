# v0.1.0
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# VaultGate - a minimal consumer of YieldClaim, proving a verdict can gate a
# treasury's allocation to a yield product on-chain. An allocation is only
# recorded if, in YieldClaim's own standing for the claim:
#   - the latest decided check is no older than the gate's max age,
#   - the verdict is MATCHES or UNDERSTATED (a page that overstates its yield,
#     or whose figure can't be compared, gets nothing),
#   - what the vault really paid, graded on the claim's own basis, is at least
#     the gate's floor (the gate acts on the verified yield, not the advertised
#     one), and
#   - the claim's running total stays within the gate's cap.
# Allocations are recorded by the gate's owner. Anything else reverts.
#
# GenVM v0.2.11 conventions (locally tested source of truth);
# contracts/vault_gate_studio_next.py is the deployed port.
# Header must end in a blank line (real GenVM v0.2.11 requirement).

from genlayer import *
import datetime

MAX_PAGE_LIMIT = 50
ALLOWED = ("MATCHES", "UNDERSTATED")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise gl.vm.UserError(message)


def _now() -> datetime.datetime:
    return datetime.datetime.fromisoformat(gl.message_raw['datetime'])


@allow_storage
class Allocation:
    claim_id: str
    vault: str       # what YieldClaim said the claim reads, so a look-alike claim is visible in the log
    page_url: str
    amount_raw: u256
    realised_bps: u32
    verdict: str
    allocated_by: Address
    allocated_at: datetime.datetime


class VaultGate(gl.Contract):
    owner: Address
    yieldclaim_address: Address
    max_age_seconds: u32
    min_realised_bps: u32
    cap_raw: u256
    allocations: DynArray[Allocation]
    totals: TreeMap[str, u256]

    def __init__(self, yieldclaim_address: str, max_age_seconds: u32, min_realised_bps: u32, cap_raw: u256) -> None:
        _require(max_age_seconds > 0, "max_age_seconds must be positive")
        _require(cap_raw > 0, "cap_raw must be positive")
        self.owner = gl.message.sender_address
        self.yieldclaim_address = Address(yieldclaim_address)
        self.max_age_seconds = max_age_seconds
        self.min_realised_bps = min_realised_bps
        self.cap_raw = cap_raw

    # Owner only: the gate demonstrates a consumer, it does not move funds.
    @gl.public.write
    def allocate(self, claim_id: str, amount_raw: u256) -> None:
        _require(gl.message.sender_address == self.owner, "only the owner can record allocations")
        _require(amount_raw > 0, "amount must be positive")
        standing = gl.get_contract_at(self.yieldclaim_address).view().get_standing(claim_id)
        _require(standing["exists"], f"{claim_id!r} refused: YieldClaim has no such claim")
        _require(standing["verdict"] != "NO_CHECK", f"{claim_id!r} refused: no decided check yet")
        age = standing["age_seconds"]
        _require(age is not None and 0 <= age <= int(self.max_age_seconds),
                 f"{claim_id!r} refused: its latest decided check is {age} seconds old; this gate wants at most {self.max_age_seconds}")
        _require(standing["verdict"] in ALLOWED,
                 f"{claim_id!r} refused: its page is {standing['verdict']} (this gate accepts {', '.join(ALLOWED)})")
        realised = standing["realised_bps"]
        _require(realised is not None and realised >= int(self.min_realised_bps),
                 f"{claim_id!r} refused: the vault paid {realised} basis points, below this gate's floor {self.min_realised_bps}")
        total = int(self.totals.get(claim_id, u256(0)))
        _require(total + int(amount_raw) <= int(self.cap_raw),
                 f"{claim_id!r} refused: this would take the total past the cap {self.cap_raw}")

        record = self.allocations.append_new_get()
        record.claim_id = claim_id
        record.vault = standing["vault"]
        record.page_url = standing["page_url"]
        record.amount_raw = amount_raw
        record.realised_bps = u32(realised)
        record.verdict = standing["verdict"]
        record.allocated_by = gl.message.sender_address
        record.allocated_at = _now()
        self.totals[claim_id] = u256(total + int(amount_raw))

    @gl.public.view
    def get_total(self, claim_id: str) -> dict:
        return {"claim_id": claim_id, "allocated_raw": str(self.totals.get(claim_id, u256(0))), "cap_raw": str(self.cap_raw)}

    @gl.public.view
    def get_allocations(self, offset: u32, limit: u32) -> list:
        limit = min(limit, MAX_PAGE_LIMIT)
        out = []
        i = len(self.allocations) - 1 - offset
        while i >= 0 and len(out) < limit:
            a = self.allocations[i]
            out.append({"claim_id": a.claim_id, "vault": a.vault, "page_url": a.page_url, "amount_raw": str(a.amount_raw),
                        "realised_bps": a.realised_bps, "verdict": a.verdict, "allocated_by": a.allocated_by.as_hex,
                        "allocated_at": a.allocated_at.isoformat()})
            i -= 1
        return out

    @gl.public.view
    def get_config(self) -> dict:
        return {"owner": self.owner.as_hex, "yieldclaim_address": self.yieldclaim_address.as_hex,
                "max_age_seconds": self.max_age_seconds, "min_realised_bps": self.min_realised_bps,
                "cap_raw": str(self.cap_raw), "allocation_count": len(self.allocations)}
