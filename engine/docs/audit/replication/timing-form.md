# Timing form — one sheet per sweep

No infrastructure. Copy this file (or paste the block below)
once per procedure run. Fill it during the run, not after from
memory. Times are local wall-clock; say the timezone once.

Use one form for Procedure A, one for B, one for C. Do not
merge sweeps onto one sheet.

```
================================================================
TIMING / RUN RECORD
================================================================
Runner name / handle:     ________________________________
Date (YYYY-MM-DD):        ________________________________
Timezone:                 ________________________________
Procedure:                A criteria / B identifier / C restatement
                          (circle one)

--- Candidate (normative) ---------------------------------------
Name:                     ________________________________
URL or repo:              ________________________________
Pin (tag/commit/version): ________________________________
Retrieval date/time:      ________________________________
Rough size (lines/bytes): ________________________________
Subject (one line):       ________________________________

--- Companion corpus (Procedure C only; else "none") ------------
Repo / paths:             ________________________________
Pin:                      ________________________________

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

--- Tooling used ------------------------------------------------
[ ] editor only
[ ] ripgrep / grep   patterns: _______________________________
[ ] git show / worktree
[ ] identifier-pass script at ../identifier-pass/ (B only)
[ ] other: ___________________________________________________

--- Questions the runner had to ask ------------------------------
(anyone: author, collaborator, search engine, prior findings,
 model with repo history — list each; "none" if truly none)

1. ____________________________________________________________
2. ____________________________________________________________
3. ____________________________________________________________

--- Blindness check ---------------------------------------------
Had you read this candidate before today?     yes / no
Had you read prior sweep findings on it?      yes / no / n/a
Used a coding agent with repo history?        yes / no
If yes to any: this run is NOT blind. Say so in the result
file. Still useful as a timed dry-run; do not label it blind.

--- Headline counts (from the procedure's counting rule) --------
(A) N=___ mechanisms=___ mixed=___ properties=___ unstated=___
(B) I=___ K=___ Missing=___ Retitled=___
(C) R=___ E=___ Invented=___ left_untouched=___

--- Disagreements / stalls --------------------------------------
Where two readings fought; where the procedure text was
ambiguous; where you stopped:

_______________________________________________________________
_______________________________________________________________

--- Pointer to full output --------------------------------------
Path to tables / inventory / conversion record:

_______________________________________________________________
================================================================
```

## Convention

- **Start** when the first corpus file is opened for the
  sweep, after the pin is frozen.
- **Stop** when the counting-rule totals are written, before
  any optional cleanup edits outside the procedure.
- **Questions** include "what does this procedure mean by
  *mixed*?" — if you had to ask, write it down. The point of
  the form is friction, not a clean score.
- File naming suggestion for deposited results:
  `results/<candidate-slug>-<A|B|C>-<YYYYMMDD>-<runner>.md`
  alongside a filled copy of this form.
