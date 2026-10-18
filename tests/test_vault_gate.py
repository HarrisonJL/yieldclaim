"""
Direct Mode tests for VaultGate.

Direct Mode can't run a cross-contract call, so two things are separated here:

- everything that runs BEFORE the read of YieldClaim (who may call, the amount, the constructor's arguments) is
  tested exactly as written;
- everything that decides on what YieldClaim says (the claim exists, has a decided check, the check is fresh,
  the verdict, the verified yield against the floor, the cap) is tested against a stand-in for YieldClaim that
  returns the exact shape of get_standing(). A test pins that shape to the real contract's output keys, and
  CONTRACT.md shows the same refusals and the one allocation happening on Studio Next, against the real
  contract, with transaction hashes.
"""

import sys

import pytest

YC_ADDRESS = "0x" + "44" * 20      # never actually called in the pre-call tests
STANDING_KEYS = {"exists", "claim_id", "label", "vault", "page_url", "tolerance_bps", "check_count", "decided_count", "verdict",
                 "check_id", "checked_at", "age_seconds", "claim_bps", "basis_used", "period", "window_days", "realised_bps", "gap_bps"}


def _deploy(direct_vm, direct_deploy, owner, max_age=86400, floor=300, cap=1000):
    direct_vm.sender = owner
    return direct_deploy("contracts/vault_gate.py", YC_ADDRESS, max_age, floor, cap)


def standing(**kw):
    base = {"exists": True, "claim_id": "sky-susds", "label": "sUSDS", "vault": "0x" + "11" * 20, "page_url": "https://sky.money/susds",
            "tolerance_bps": 50, "check_count": 1, "decided_count": 1, "verdict": "MATCHES", "check_id": 0,
            "checked_at": "2026-10-18T18:00:00+00:00", "age_seconds": 3600, "claim_bps": 380, "basis_used": "APY", "period": "CURRENT",
            "window_days": 7, "realised_bps": 380, "gap_bps": 0}
    base.update(kw)
    assert set(base) == STANDING_KEYS
    return base


class _View:
    def __init__(self, answers):
        self.answers = answers

    def get_standing(self, claim_id):
        return self.answers[claim_id]


class _Proxy:
    def __init__(self, answers):
        self.answers = answers

    def view(self):
        return _View(self.answers)


@pytest.fixture
def gate(direct_vm, direct_deploy, direct_owner, monkeypatch):
    contract = _deploy(direct_vm, direct_deploy, direct_owner)
    mod = sys.modules["_contract_vault_gate"]
    answers = {}
    monkeypatch.setattr(mod.gl, "get_contract_at", lambda address: _Proxy(answers))
    contract.answers = answers
    return contract


# --- Before the read of YieldClaim ----------------------------------------------------


def test_config_and_empty_state(direct_vm, direct_deploy, direct_owner):
    g = _deploy(direct_vm, direct_deploy, direct_owner)
    cfg = g.get_config()
    assert cfg["yieldclaim_address"].lower() == YC_ADDRESS and cfg["max_age_seconds"] == 86400
    assert cfg["min_realised_bps"] == 300 and cfg["cap_raw"] == "1000" and cfg["allocation_count"] == 0
    assert g.get_total("any") == {"claim_id": "any", "allocated_raw": "0", "cap_raw": "1000"}
    assert g.get_allocations(0, 10) == []


@pytest.mark.parametrize("kw,message", [({"max_age": 0}, "max_age_seconds must be positive"), ({"cap": 0}, "cap_raw must be positive")])
def test_a_gate_needs_a_positive_age_and_cap(direct_vm, direct_deploy, direct_owner, kw, message):
    with pytest.raises(Exception, match=message):
        _deploy(direct_vm, direct_deploy, direct_owner, **kw)


def test_only_the_owner_can_record_an_allocation(direct_vm, direct_deploy, direct_owner, direct_alice):
    g = _deploy(direct_vm, direct_deploy, direct_owner)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="only the owner can record allocations"):
        g.allocate("sky-susds", 100)


def test_a_zero_amount_is_rejected_before_any_cross_contract_call(direct_vm, direct_deploy, direct_owner):
    g = _deploy(direct_vm, direct_deploy, direct_owner)
    with pytest.raises(Exception, match="amount must be positive"):
        g.allocate("sky-susds", 0)


# --- On what YieldClaim says (against a stand-in with get_standing's exact shape) ---------


def test_an_honest_fresh_claim_is_allocated_to_and_recorded(gate, direct_owner):
    gate.answers["sky-susds"] = standing()
    gate.allocate("sky-susds", 400)
    assert gate.get_total("sky-susds") == {"claim_id": "sky-susds", "allocated_raw": "400", "cap_raw": "1000"}
    (a,) = gate.get_allocations(0, 10)
    assert (a["claim_id"], a["amount_raw"], a["realised_bps"], a["verdict"]) == ("sky-susds", "400", 380, "MATCHES")
    # the log shows what the claim reads, so a look-alike claim registered against another page or vault is visible in it
    assert (a["vault"], a["page_url"]) == ("0x" + "11" * 20, "https://sky.money/susds")
    assert a["allocated_by"].lower() == "0x" + direct_owner.hex() and a["allocated_at"].count(":") >= 2
    assert gate.get_config()["allocation_count"] == 1


def test_a_page_that_undersold_its_yield_is_fine(gate):
    gate.answers["sky-susds"] = standing(verdict="UNDERSTATED", claim_bps=100, gap_bps=-280)
    gate.allocate("sky-susds", 1)
    assert gate.get_allocations(0, 1)[0]["verdict"] == "UNDERSTATED"


@pytest.mark.parametrize("verdict", ["OVERSTATED", "NOT_COMPARABLE", "UNDETERMINED", "something-new"])
def test_any_other_verdict_gets_nothing(gate, verdict):
    gate.answers["sky-susds"] = standing(verdict=verdict)
    with pytest.raises(Exception, match=f"its page is {verdict}"):
        gate.allocate("sky-susds", 1)
    assert gate.get_config()["allocation_count"] == 0


def test_a_claim_that_does_not_exist_or_was_never_checked_gets_nothing(gate):
    gate.answers["ghost"] = {"exists": False, "claim_id": "ghost"}
    with pytest.raises(Exception, match="YieldClaim has no such claim"):
        gate.allocate("ghost", 1)
    gate.answers["new"] = standing(verdict="NO_CHECK", check_id=None, checked_at=None, age_seconds=None, claim_bps=None, basis_used=None,
                                   period=None, window_days=None, realised_bps=None, gap_bps=None, check_count=0, decided_count=0)
    with pytest.raises(Exception, match="no decided check yet"):
        gate.allocate("new", 1)


@pytest.mark.parametrize("age,ok", [(0, True), (86400, True), (86401, False), (10 ** 9, False), (-1, False), (None, False)])
def test_the_check_must_be_fresh_but_not_from_the_future(gate, age, ok):
    gate.answers["sky-susds"] = standing(age_seconds=age)
    if ok:
        gate.allocate("sky-susds", 1)
    else:
        with pytest.raises(Exception, match="seconds old"):
            gate.allocate("sky-susds", 1)


@pytest.mark.parametrize("realised,ok", [(300, True), (301, True), (299, False), (0, False), (-50, False), (None, False)])
def test_the_gate_acts_on_the_verified_yield_not_the_advertised_one(gate, realised, ok):
    # the page's own figure is irrelevant: even a page claiming 9% is allocated to if it MATCHES and the vault really paid the floor
    gate.answers["sky-susds"] = standing(realised_bps=realised, claim_bps=900)
    if ok:
        gate.allocate("sky-susds", 1)
    else:
        with pytest.raises(Exception, match="below this gate's floor 300"):
            gate.allocate("sky-susds", 1)


def test_a_claims_allocations_are_capped_in_total(gate):
    gate.answers["sky-susds"] = standing()
    gate.answers["sky-stusds"] = standing(claim_id="sky-stusds")
    gate.allocate("sky-susds", 600)
    gate.allocate("sky-susds", 400)                      # exactly the cap
    with pytest.raises(Exception, match="past the cap 1000"):
        gate.allocate("sky-susds", 1)
    gate.allocate("sky-stusds", 1000)                    # another claim has its own room
    assert gate.get_total("sky-susds")["allocated_raw"] == "1000" and gate.get_total("sky-stusds")["allocated_raw"] == "1000"
    assert [a["amount_raw"] for a in gate.get_allocations(0, 10)] == ["1000", "400", "600"]      # newest first
    assert [a["amount_raw"] for a in gate.get_allocations(1, 1)] == ["400"]


def test_a_refusal_changes_nothing(gate):
    gate.answers["sky-susds"] = standing(verdict="OVERSTATED")
    with pytest.raises(Exception):
        gate.allocate("sky-susds", 5)
    assert gate.get_total("sky-susds")["allocated_raw"] == "0" and gate.get_allocations(0, 10) == []


def test_paging_is_capped_at_fifty(gate):
    gate.answers["sky-susds"] = standing()
    for _ in range(52):
        gate.allocate("sky-susds", 1)
    assert len(gate.get_allocations(0, 1000)) == 50 and gate.get_allocations(60, 5) == []
    assert len(gate.get_allocations(50, 10)) == 2
