# Timing form — second-analyst coverage pass

No infrastructure. Fill this during the run, not after from
memory. Times are local wall-clock; say the timezone once.

```
================================================================
TIMING / RUN RECORD — SECOND ANALYST
================================================================
Runner name / handle:     ________________________________
Date (YYYY-MM-DD):        ________________________________
Timezone:                 ________________________________
Pack path:                engine/docs/audit/second-analyst/
Corpus pin (from PIN.txt): ________________________________

--- Clock -------------------------------------------------------
Start (HH:MM):            ________________________________
Stop  (HH:MM):            ________________________________
Elapsed (hours):          ________________________________
Breaks excluded? (y/n):   ________________________________

--- What was read (every file; add rows) ------------------------
Path                                              approx. lines
_______________________________________________   _____________
_______________________________________________   _____________
_______________________________________________   _____________
_______________________________________________   _____________
_______________________________________________   _____________

--- Tooling used ------------------------------------------------
[ ] editor only
[ ] ripgrep / grep   patterns: _______________________________
[ ] search within corpus/ only
[ ] other: ___________________________________________________

--- Questions the runner had to ask ------------------------------
(anyone: author, collaborator, search engine, prior findings,
 model with repo history — list each; "none" if truly none.
 Include questions about what a rule means.)

1. ____________________________________________________________
2. ____________________________________________________________
3. ____________________________________________________________
4. ____________________________________________________________

--- Anything else they had to ask about --------------------------
(procedure gaps, missing assumed knowledge, corpus confusion,
 class-owes doubt, OpenAPI / RFC 2119 / conformance wording)

_______________________________________________________________
_______________________________________________________________
_______________________________________________________________

--- Blindness check ---------------------------------------------
Had you read this candidate / corpus before today?  yes / no
Had you read prior sweep findings on it?            yes / no
Used a coding agent with this repo's history?       yes / no
Opened SEALED-KEY/ before finishing the sheet?      yes / no
If yes to any: this run is NOT blind. Say so here:

_______________________________________________________________

--- Disagreements / stalls --------------------------------------
Where two readings fought; where the rules ran out; where you
stopped:

_______________________________________________________________
_______________________________________________________________
_______________________________________________________________

--- Pointer to filled recording sheet ---------------------------
Path:

_______________________________________________________________
================================================================
```

## Convention

- **Start** when the first corpus file is opened for judgment,
  after reading the brief and coverage rules.
- **Stop** when the recording sheet has a decision in every
  Covered? cell (including `undecidable`), before any
  comparison to a sealed key.
- **Questions** and **anything they had to ask about** are the
  point of this form. Friction is data.
