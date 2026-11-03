# Pins and windows

| Role | Spec version | Commit |
|---|---|---|
| **Package corpus pin** (identifier pass / coverage) | 1.16.0 | `0a997321234e5f6f6184b7449a241c3d30a19520` |
| **Criteria-audit sweep window opens** | 1.8.0 | `b074475b4fedd35c527c4d8ba089053e5fbe8d04` |
| **Criteria-audit sweep window closes** | 1.15.0 | `bde94022e16493b28f595c693c7ac66d49835682` |
| **Tip the companion paper reports against** (living tree at package build) | 1.25.0 | `66c509f3625fced9f30f029f458b186547b06d47` |

The vendored tree under [`corpus/`](corpus/) is the **1.16.0 package pin** only.
Criteria-audit and restatement procedures that need the 1.8.0→1.15.0 window
must freeze those commits from the public `open-gw/ctier` history; they are
not re-vendored here.
