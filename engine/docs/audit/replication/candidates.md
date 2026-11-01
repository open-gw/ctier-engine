# Candidate documents for a blind run

**Do not audit these here.** This file records identity, rough
size, and fairness only. No findings. No identifier lists. No
mechanism/property verdicts. Size checks used HTTP download
byte/line counts of the cited artefact on 2026-11-01; they are
not a reading of normative content.

Reference scale for "comparable to ctier": the ctier normative
prose set (`spec/*.md` excluding huge dumps) is on the order of
**~3.7k lines / ~300 KiB** of markdown plus a small schemas
tree. Genre: RFCs-2119 / BCP-14 normative API or protocol
specification with stable named obligations.

Procedure C additionally needs a **companion corpus** (living
implementation or product documents). None is selected here;
the blind runner names one after the normative pick, or skips
Procedure C with `companion corpus: none` on the timing form.

---

## Shortlist

| # | Document | URL | Rough length | Why fair |
|---|---|---|---|---|
| 1 | OpenAPI Specification 3.1.1 | https://spec.openapis.org/oas/v3.1.1.html — source https://raw.githubusercontent.com/OAI/OpenAPI-Specification/main/versions/3.1.1.md | ~4.6k lines / ~208 KiB markdown | Same genre (HTTP API description, MUST language, schemas). Independent authors (OpenAPI Initiative). Size within ~25% of ctier prose. |
| 2 | AsyncAPI Specification (current `master` `spec/asyncapi.md`) | https://github.com/asyncapi/spec — https://raw.githubusercontent.com/asyncapi/spec/master/spec/asyncapi.md | ~2.8k lines / ~130 KiB | Same genre family as OpenAPI; independent AsyncAPI project; slightly smaller but still multi-thousand-line normative markdown. |
| 3 | JSON Schema 2020-12 core + validation | https://github.com/json-schema-org/json-schema-spec — `specs/jsonschema-core.md` + `specs/jsonschema-validation.md` | ~2.6k + ~0.9k lines (~156 KiB combined) | Normative vocabulary + validation keywords; two-file corpus similar to a small `spec/` tree; JSON Schema org, unconnected. |
| 4 | OAuth 2.0 Authorization Framework (RFC 6749) | https://www.rfc-editor.org/rfc/rfc6749 | ~HTML artefact ~200 KiB / ~4.2k lines as fetched | Classic IETF normative prose; independent of this project; comparable bulk; different genre stress (RFC structure vs markdown spec tree). |
| 5 | OpenID Connect Core 1.0 | https://openid.net/specs/openid-connect-core-1_0.html | ~HTML artefact ~430 KiB / ~10k lines as fetched | Larger than ctier; still a fair "can the method scale?" stress. OpenID Foundation authors; dense named requirements and identifiers. |

Not shortlisted (too small for a fair timed compare on size
alone, without judging content): CloudEvents core (~0.6k
lines), W3C Trace Context alone, single SPIFFE ID note.

---

## Pick first

**OpenAPI Specification 3.1.1 (#1).**

Reasons that do not depend on reading it for defects:

1. **Genre match** — API-description normative markdown with
   MUST/SHALL language and schema-shaped artefacts, closest to
   the original sweep's document kind.
2. **Size** — ~4.6k-line source is the closest single-file peer
   to ctier's prose bulk without jumping to a 10k-line HTML
   megaspec.
3. **Independence** — OAI authorship; no shared editors with
   this repository.
4. **Procedure C optionality** — companion corpora exist in the
   wild (tooling READMEs, gateway product docs) if a runner
   later declares one; the normative pick itself does not
   require that choice up front.

Runner instruction: pin the exact commit or published version
string on the timing form before opening Procedure A. Do not
"browse for interesting sections" before start time.
