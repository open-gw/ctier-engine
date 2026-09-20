from ctier.classifier import Classifier, GovernanceConfig
from ctier.models import *

c = Classifier(GovernanceConfig(escalate_above=9))

def show(label, d):
    esc = f"  <- {d.escalation_reason.value}" if d.escalated else ""
    dec = f"{d.declared_tier.name if d.declared_tier else '--':<8}"
    print(f"{label:<38} declared={dec} applied=T{int(d.applied_tier)} {d.disposition.value:<10}{esc}")

def r(**k):
    base = dict(method="GET", path="/x", agent_id="agent-a", task_id="t1")
    base.update(k)
    return Request(**base)

show("balance query (T1)", c.classify(
    Operation(operation_id="getBalance", method="GET", path_template="/accounts/{id}/balance",
              declared_tier=Tier.LOW), r()))
show("preference update (T2)", c.classify(
    Operation(operation_id="updatePrefs", method="PATCH", path_template="/customers/{id}/preferences",
              declared_tier=Tier.MEDIUM), r(task_id="t2")))
show("profile update (T3)", c.classify(
    Operation(operation_id="updateProfile", method="PUT", path_template="/customers/{id}/profile",
              declared_tier=Tier.HIGH), r(task_id="t3")))
show("payment initiation (T4)", c.classify(
    Operation(operation_id="initiatePayment", method="POST", path_template="/payments",
              declared_tier=Tier.CRITICAL), r(task_id="t4")))
show("statements export (undeclared)", c.classify(None, r(task_id="t5")))
show("account closure (excluded)", c.classify(
    Operation(operation_id="closeAccount", method="POST", path_template="/accounts/{id}/closure",
              excluded=True), r(task_id="t6")))

print()
o = Operation(operation_id="listTransactions", method="GET",
              path_template="/accounts/{id}/transactions", declared_tier=Tier.LOW)
for i in range(1, 13):
    d = c.classify(o, r(task_id="laundering"))
    if i in (1, 9, 10, 12):
        show(f"  transactions read #{i}", d)
