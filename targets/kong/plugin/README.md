# ctier Kong plugin

Data-driven. Reads instance config and applies a disposition. It does not
classify, does not parse paths, and does not decide anything the generator
could have decided at deploy time.

**Tested in 08c** against Kong 3.9.3 DB-less. The live suite is opt-in:
`pytest --live`. See `engine/docs/findings/08c.md`.

No licence file is included here. See the task output; DECISIONS.md Q5 is
unresolved for a plugin distributed through a hub.
