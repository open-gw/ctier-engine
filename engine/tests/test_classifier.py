"""Tests are written against the conformance requirements in docs/PRD.md."""
import pytest

from ctier.classifier import (
    Accumulator,
    Classifier,
    GovernanceConfig,
    compute_tier,
    derive_idempotency_key,
    exceeds_declared_bounds,
)
from ctier.models import (
    BlastRadius,
    ComplianceTrigger,
    Criteria,
    DelegationHop,
    Disposition,
    EscalationReason,
    Idempotency,
    Operation,
    Request,
    Reversibility,
    Sensitivity,
    Tier,
)


def req(**kw):
    base = dict(method="GET", path="/accounts/1/balance", agent_id="agent-a",
                task_id="task-1")
    base.update(kw)
    return Request(**base)


def op(**kw):
    base = dict(method="GET", path_template="/accounts/{id}/balance",
                operation_id="getBalance")
    base.update(kw)
    return Operation(**base)


# --- C2: undeclared fails closed -------------------------------------------

def test_undeclared_operation_is_tier_4():
    d = Classifier().classify(None, req())
    assert d.applied_tier is Tier.CRITICAL
    assert d.escalation_reason is EscalationReason.UNDECLARED
    assert d.disposition is Disposition.REFUSE_AND_SUSPEND


def test_operation_without_declared_tier_is_tier_4():
    d = Classifier().classify(op(declared_tier=None), req())
    assert d.applied_tier is Tier.CRITICAL


# --- C3: escalation is unidirectional --------------------------------------

def test_declared_tier_is_a_floor_not_a_determination():
    # criteria would compute Tier 1; declared says 3. The higher wins.
    c = Criteria(reversibility=Reversibility.NOT_APPLICABLE,
                 data_sensitivity=Sensitivity.PUBLIC)
    d = Classifier().classify(op(declared_tier=Tier.HIGH, criteria=c), req())
    assert d.applied_tier is Tier.HIGH


def test_computed_tier_may_raise_a_declared_tier():
    c = Criteria(reversibility=Reversibility.NONE)          # computes Tier 4
    d = Classifier().classify(op(declared_tier=Tier.LOW, criteria=c), req())
    assert d.applied_tier is Tier.CRITICAL
    assert d.escalation_reason is EscalationReason.COMPUTED_EXCEEDS_DECLARED


# --- three-state reversibility ---------------------------------------------

def test_undo_restores_effect_is_tier_2():
    assert compute_tier(Criteria(
        reversibility=Reversibility.RESTORES_EFFECT,
        data_sensitivity=Sensitivity.PERSONAL,
        blast_radius=BlastRadius.SINGLE_CUSTOMER)) is Tier.MEDIUM


def test_undo_restores_record_only_is_tier_3():
    # the price can be put back; the orders placed at the wrong price were still placed
    assert compute_tier(Criteria(
        reversibility=Reversibility.RESTORES_RECORD,
        data_sensitivity=Sensitivity.PERSONAL,
        blast_radius=BlastRadius.SINGLE_CUSTOMER)) is Tier.HIGH


def test_no_undo_is_tier_4():
    assert compute_tier(Criteria(reversibility=Reversibility.NONE)) is Tier.CRITICAL


def test_blast_radius_alone_carries_tier_4():
    # touches no personal data whatsoever and is still critical
    assert compute_tier(Criteria(
        reversibility=Reversibility.RESTORES_RECORD,
        blast_radius=BlastRadius.SYSTEM_WIDE,
        data_sensitivity=Sensitivity.INTERNAL,
        compliance_trigger=ComplianceTrigger.NONE)) is Tier.CRITICAL


# --- C7: derived idempotency keys ------------------------------------------

def test_same_operation_same_subject_derives_same_key():
    o, r = op(), req()
    k = b"key"
    assert derive_idempotency_key(o, r, k) == derive_idempotency_key(o, r, k)


def test_same_operation_different_subject_derives_different_key():
    o = op(operation_id="updateProfile", method="PUT",
           path_template="/customers/{id}/profile")
    a = req(method="PUT", path="/customers/1/profile", body='{"name":"A"}')
    b = req(method="PUT", path="/customers/2/profile", body='{"name":"A"}')
    assert derive_idempotency_key(o, a, b"k") != derive_idempotency_key(o, b, b"k")


def test_key_is_stable_across_body_key_ordering():
    o = op(operation_id="updateProfile", method="PUT")
    a = req(method="PUT", body='{"a":1,"b":2}')
    b = req(method="PUT", body='{"b":2,"a":1}')
    assert derive_idempotency_key(o, a, b"k") == derive_idempotency_key(o, b, b"k")


# --- delegation chain integrity --------------------------------------------

def test_child_exceeding_parent_scope_suspends_the_chain():
    chain = [
        DelegationHop(agent_id="orchestrator", scopes=["accounts:read"]),
        DelegationHop(agent_id="sub", scopes=["accounts:read", "payments:write"]),
    ]
    d = Classifier().classify(op(declared_tier=Tier.LOW),
                              req(delegation_chain=chain))
    assert d.applied_tier is Tier.CRITICAL
    assert d.escalation_reason is EscalationReason.DELEGATION_EXPANSION


def test_reduced_child_scope_is_permitted():
    chain = [
        DelegationHop(agent_id="orchestrator", scopes=["accounts:read", "payments:write"]),
        DelegationHop(agent_id="sub", scopes=["accounts:read"]),
    ]
    d = Classifier().classify(op(declared_tier=Tier.LOW),
                              req(delegation_chain=chain))
    assert d.applied_tier is Tier.LOW


def test_delegation_check_precedes_the_operation_itself():
    chain = [
        DelegationHop(agent_id="a", scopes=[], data_sensitivity=Sensitivity.PUBLIC),
        DelegationHop(agent_id="b", scopes=[], data_sensitivity=Sensitivity.REGULATED),
    ]
    d = Classifier().classify(op(declared_tier=Tier.LOW), req(delegation_chain=chain))
    assert d.applied_tier is Tier.CRITICAL


# --- session accumulation ---------------------------------------------------

def test_sequence_of_tier_1_reads_escalates_on_accumulation():
    """A high-consequence outcome assembled from low-consequence calls."""
    c = Classifier(GovernanceConfig(escalate_above=9))
    o = op(declared_tier=Tier.LOW)
    tiers = [c.classify(o, req()).applied_tier for _ in range(12)]
    assert tiers[0] is Tier.LOW
    assert Tier.MEDIUM in tiers, "accumulated consequence should raise the tier"


def test_accumulation_decays_so_long_sessions_are_not_punished():
    acc = Accumulator(decay_seconds=60)
    acc.add("task-1", 9, now=1000.0)
    assert acc.current("task-1", now=1030.0) == 9
    assert acc.current("task-1", now=1100.0) == 0


def test_accumulation_is_scoped_per_task():
    c = Classifier(GovernanceConfig(escalate_above=9))
    o = op(declared_tier=Tier.LOW)
    for _ in range(12):
        c.classify(o, req(task_id="task-1"))
    fresh = c.classify(o, req(task_id="task-2"))
    assert fresh.applied_tier is Tier.LOW


# --- payload exceeding declared bounds --------------------------------------

def test_request_exceeding_declared_bound_escalates():
    o = op(declared_tier=Tier.LOW, bound_parameter="limit", max_result_bound=100)
    d = Classifier().classify(o, req(query={"limit": "10000"}))
    assert d.applied_tier is Tier.MEDIUM
    assert d.escalation_reason is EscalationReason.PAYLOAD_EXCEEDS_BOUNDS


def test_request_within_declared_bound_does_not_escalate():
    o = op(declared_tier=Tier.LOW, bound_parameter="limit", max_result_bound=100)
    d = Classifier().classify(o, req(query={"limit": "50"}))
    assert d.applied_tier is Tier.LOW


@pytest.mark.parametrize("raw,exceeds", [
    ("101", True),
    ("101.0", True),
    ("1.01e2", True),
    ("100", False),
    ("abc", False),
    (None, False),
])
def test_bound_comparison_is_decimal_numeric(raw, exceeds):
    """Spec 1.1.6: decimal parse. Integer parse is fail-open on 101.0."""
    o = op(declared_tier=Tier.LOW, bound_parameter="limit", max_result_bound=100)
    query = {} if raw is None else {"limit": raw}
    assert exceeds_declared_bounds(o, req(query=query)) is exceeds
    d = Classifier().classify(o, req(query=query))
    assert d.applied_tier is (Tier.MEDIUM if exceeds else Tier.LOW)


# --- exclusion is not a tier ------------------------------------------------

def test_excluded_operation_reached_is_a_provisioning_defect():
    d = Classifier().classify(op(excluded=True), req())
    assert d.disposition is Disposition.REFUSE_PROVISIONING
    assert "over-granted" in d.notes or "excluded" in d.notes


# --- dispositions -----------------------------------------------------------

@pytest.mark.parametrize("tier,expected", [
    (Tier.LOW, Disposition.EXECUTE),
    (Tier.MEDIUM, Disposition.EXECUTE),
    (Tier.HIGH, Disposition.WITHHOLD),
    (Tier.CRITICAL, Disposition.REFUSE_AND_SUSPEND),
])
def test_disposition_follows_tier(tier, expected):
    d = Classifier().classify(op(declared_tier=tier), req())
    assert d.disposition is expected


# --- C10: the record carries declared, applied and reason -------------------

def test_decision_distinguishes_declared_from_escalated():
    c = Classifier(GovernanceConfig(escalate_above=1))
    o = op(declared_tier=Tier.LOW)
    c.classify(o, req())
    second = c.classify(o, req())
    assert second.declared_tier is Tier.LOW
    assert second.applied_tier > Tier.LOW
    assert second.escalated is True


# --- population-scale reads are a delay, not a handover --------------------

def test_population_read_of_internal_data_is_tier_1():
    """Ordinary population-scale reads are not a handover."""
    assert compute_tier(Criteria(
        reversibility=Reversibility.NOT_APPLICABLE,
        blast_radius=BlastRadius.POPULATION,
        data_sensitivity=Sensitivity.INTERNAL,
        compliance_trigger=ComplianceTrigger.NONE)) is Tier.LOW


def test_system_wide_read_of_regulated_data_is_tier_3():
    """Disclosure at population scale cannot be undone, so it is withheld."""
    assert compute_tier(Criteria(
        reversibility=Reversibility.NOT_APPLICABLE,
        blast_radius=BlastRadius.SYSTEM_WIDE,
        data_sensitivity=Sensitivity.REGULATED,
        compliance_trigger=ComplianceTrigger.NONE)) is Tier.HIGH


def test_system_wide_regulated_read_with_direct_compliance_is_tier_4():
    """A direct compliance trigger still outranks the disclosure rule."""
    assert compute_tier(Criteria(
        reversibility=Reversibility.NOT_APPLICABLE,
        blast_radius=BlastRadius.SYSTEM_WIDE,
        data_sensitivity=Sensitivity.REGULATED,
        compliance_trigger=ComplianceTrigger.DIRECT)) is Tier.CRITICAL


def test_population_write_is_tier_4_regardless_of_sensitivity():
    """A population-scale write collapses reversibility: the affected set is unbounded."""
    assert compute_tier(Criteria(
        reversibility=Reversibility.RESTORES_EFFECT,
        blast_radius=BlastRadius.POPULATION,
        data_sensitivity=Sensitivity.PUBLIC,
        compliance_trigger=ComplianceTrigger.NONE)) is Tier.CRITICAL


# --- C3: an escalation stage may not lower the tier entering it ------------

def test_escalate_to_cannot_lower_a_tier_raised_by_bounds():
    """An escalation stage may not produce a tier lower than the one entering it."""
    o = op(declared_tier=Tier.LOW, bound_parameter="limit", max_result_bound=10,
           escalate_to=Tier.LOW)
    d = Classifier(GovernanceConfig(escalate_above=0)).classify(
        o, req(query={"limit": "999"}))
    assert d.applied_tier is Tier.MEDIUM


def test_noop_accumulation_preserves_the_prior_escalation_reason():
    """SESSION_ACCUMULATION is recorded only when the tier actually moved."""
    o = op(declared_tier=Tier.LOW, bound_parameter="limit", max_result_bound=10,
           escalate_to=Tier.LOW)
    d = Classifier(GovernanceConfig(escalate_above=0)).classify(
        o, req(query={"limit": "999"}))
    assert d.escalation_reason is EscalationReason.PAYLOAD_EXCEEDS_BOUNDS


# --- declared zero weight and criteria-only resolution ---------------------

def test_declared_zero_weight_does_not_accumulate():
    """A contributes_weight of zero is a decision, not an absent value."""
    c = Classifier(GovernanceConfig(escalate_above=9))
    o = op(declared_tier=Tier.LOW, contributes_weight=0)
    last = None
    for _ in range(20):
        last = c.classify(o, req())
    assert last.applied_tier is Tier.LOW
    assert last.accumulated_weight == 0


def test_criteria_without_declared_tier_resolve_from_compute_tier():
    """A criteria block is a declaration; C2 fails closed only when both are absent."""
    criteria = Criteria(reversibility=Reversibility.NOT_APPLICABLE,
                        data_sensitivity=Sensitivity.PUBLIC)
    d = Classifier().classify(op(declared_tier=None, criteria=criteria), req())
    assert d.applied_tier is Tier.LOW
    assert d.escalation_reason is EscalationReason.NONE


def test_neither_tier_nor_criteria_fails_closed():
    """Absence of both a declared tier and criteria is undeclared."""
    d = Classifier().classify(op(declared_tier=None), req())
    assert d.applied_tier is Tier.CRITICAL
    assert d.escalation_reason is EscalationReason.UNDECLARED


# --- C11: classify is header-blind -----------------------------------------

def _decision_key(d):
    return (d.applied_tier, d.disposition, d.escalation_reason, d.declared_tier, d.notes)


_HEADER_SETS = (
    {},
    {"x-ctier-tier": "1"},
    {"x-ctier-tier": "2"},
    {"x-ctier-tier": "3"},
    {"x-ctier-tier": "4"},
    {"X-Ctier-Tier": "1"},
    {"x-ctier-exclude": "true"},
    {"x-ctier-criteria": "reversibility: not-applicable"},
    {"x-ctier-bounds": "limit=1"},
    {"x-ctier-composition": "sha256:deadbeef"},
    {"x-ctier-deployment": "sha256:deadbeef"},
    {"x-ctier-operation": "getBalance"},
    {"authorization": "Bearer attacker", "x-ctier-tier": "1"},
)


_OPERATIONS = (
    None,
    op(declared_tier=None),
    op(declared_tier=Tier.LOW),
    op(declared_tier=Tier.MEDIUM),
    op(declared_tier=Tier.HIGH),
    op(declared_tier=Tier.CRITICAL),
    op(excluded=True),
    op(declared_tier=Tier.LOW, bound_parameter="limit", max_result_bound=100),
)


@pytest.mark.parametrize("operation", _OPERATIONS, ids=[
    "undeclared-none",
    "undeclared-op",
    "tier-1",
    "tier-2",
    "tier-3",
    "tier-4",
    "excluded",
    "bounded-tier-1",
])
def test_classify_is_invariant_under_inbound_headers(operation):
    """Any inbound headers, including well-formed x-ctier-* asserting every
    tier, must not change the decision. Fresh classifier per call so
    accumulation cannot mask a header read."""
    baseline = Classifier().classify(operation, req())
    queries = ({}, {"limit": "999"})
    for headers in _HEADER_SETS:
        for query in queries:
            got = Classifier().classify(operation, req(headers=headers, query=query))
            expect = Classifier().classify(operation, req(query=query))
            assert _decision_key(got) == _decision_key(expect)
    assert _decision_key(Classifier().classify(operation, req())) == _decision_key(baseline)
