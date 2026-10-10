Adopt reviewed model 1.0.2 with recorded handover and historical What-if dispatch

The existing backend was still executing model 1.0.1 while B's reviewed detector
handoff and numeric hardening used 1.0.2. This change adopts the exact reviewed
computation and quality validators together, blocks implicit model transitions,
and adds an admin model-only handover for streams without detector policies.
Existing state/results, incident acknowledgements/tasks and What-if references
retain their original identity; historical forecasts execute the retained 1.0.1
implementation through server version dispatch.

Stacked on A's registry branch at 2e934c85098453db7342ea6ade570759ef4b9161,
including the existing What-if and D genuine-task integration. Target main; the
registry dependency must land or be reviewed with this stack. Review the focused
incremental diff against feature/persona-incident-registry to isolate adoption.
Executable B source: f668a21dcf88605d7fcff4996282185bc796740c (PR24 includes PR17
lineage); B's documentation/alignment head: d86b210a5ee3a0a62b926b134d1119abeb3ff1fd.

Validation: isolated PostgreSQL backend/contract suite, independent 192-test B
suite, real stored-result planner compatibility, old/new model handover and
historical forecast tests, actual loopback HTTP requests and existing React
chart consumption. Exact final counts/commands/source hashes are in
`docs/person-a-model-102-verification.json`. All 14 original hashes, adapted
module function/class ASTs and unchanged historical files were checked. D006
remains the single migration head; this adoption adds no DDL/data migration.

No development service restart, application-database migration, parameter tuning,
deployment or teammate messages. Synthetic/analytical verification is not measured
physical calibration. Human review, CI and explicit stream/operator rollout
remain required; this PR is draft and must not be automatically merged.
