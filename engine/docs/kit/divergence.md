# Permitted divergence

A difference on this list is permitted.
A difference that is not on this list is
a failure. The list is closed for
`conformance-kit/1.1`.

---

## 1. The compiled artefact

Kong, APISIX, and Apigee configuration
differ by construction. Plugin names,
priorities, slot brackets, and JS
callout order are not compared.
[`same.md`](same.md).

## 2. Strip, bounded per target

Requirement 3. An implementation
guarantees strip-before-read for a
stated class of coexisting
configuration, and names what the class
excludes (16c). A reader outside that
class may see an inbound reserved
header. That is not a kit failure.
The kit does not contain a precedence
case. C16 is the clean-path property:
the reserved prefix is absent at the
backend when nothing else sits in
front.

## 3. An unassigned path claimed later

C12. A path the composition did not
contain is refused undetermined, when
the running estate has routed it and
has not claimed it with an assignment.
A more specific route added after
generation can still escape (41).
Against a **routed** `/estate/unknown`
with no later claim, both live targets
must refuse.

A path that matches no route at all is
outside the letter. Kong answers that
with `404` and writes nothing. That is
not a C12 fail and not a C12 pass. The
kit reports **inconclusive**: it cannot
tell an unrouted path from a C12 miss.
The operator must provision a routed-
but-ungoverned path before the row can
pass or fail. A later claim that wins
is this bound, not a C12 pass.

## 4. Where the record is written

C10. The runner asks whether a record
was written, through the URL the
operator pointed at. It does not ask
which file. Gateway log at Levels 1
and 2, custody when persist is
deployed, both, or a collector in
front of either — permitted (45, 50).
Absence of a record, when the runner
was given a place to look, is a
failure.

## 5. A target without a shared mechanism

Apigee has no local runtime in this
repository. `print()` is the Trace
tool, not a retrievable sink. The
Apigee package compiles an optional
`SC-RecordDecision` hop to a collector
URL the kit can GET, and ships
`observer/` + `collector/` processes.
Level 4 has no live column. Fragment
merge does not inherit another
target's precedence result. Those
absences are permitted as skips when
the operator does not provide a
records URL, an observer URL, or an
approval URL. A skip is not a pass.
The reason is `requires a capability
this target lacks`. Pointing the
runner at an empty sink is a failure.

## 6. Disposition by deployment level

C3 and C5. Class 3 is `202` where a
persist path exists and `403`
`provisioning_defect` where it does
not. That is the level, not the
target. Both live targets at the same
level must agree.

---

## Not on this list

These were found while writing the map
and the cases. They are failures, not
divergences.

- Header absent on a named `202` or
  named `423` mechanism. Pairing is
  the case, not a divergence.

## Composed-undeclared must record (65)

The undeclared default is a decision.
Kong records it (global plugin, route
in `governed-set`, tier 4). APISIX's
catchall C2 branch once returned `423`
with no sink line — not on this list,
fixed in 65. Kit `1.1` adds
`c10-undeclared-has-a-decision` so that
path cannot go silent again while the
classified C10 rows stay green.

## C7 at Level 2

Not a failure on this list, and not a
divergence. Level 2 has no custody, so
there is nowhere to store a derived
key. The adoption ladder says Level 2
does not satisfy C7. The observability
map marks C7 not satisfiable below
Level 3. The case is Level 3 only. At
Level 2 the row skips with `not
applicable at this level`. Both live
engines strip and emit none at Level 2
— that shared result is the design,
not an unwired bug to clear here.
