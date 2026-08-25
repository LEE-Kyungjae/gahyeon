# OpenHuman-inspired knowledge and memory architecture

Gahyeon adopts the useful OpenHuman concepts without sharing identities or memories across users.

## Identity boundary

Linked accounts use `zezestudio:<immutable UUID>`. Known but unlinked accounts remain in
`principal:<internal ID>`. An explicitly uncertain speaker is `ephemeral` and is excluded from persistent
memory context. Pre-link memory can move only through a pending request, explicit user approval proof,
and approved execution.

## Retrieval boundary

Character memory requires an exact `(character, world, subject)` match. Generic knowledge requires an
exact service match; private sources additionally require an exact owner subject match. These filters run
in SQL before lexical or vector ranking. The agent receives only the already-authorized top evidence.

## Knowledge lifecycle

Ingestion normalizes and hashes a document, rejects duplicate content in the same authorization scope,
creates overlapping chunks, and records the embedding model identity when an embedding runtime is
available. Sources can be disabled or soft-deleted with their documents and chunks.

## Memory graph and character workspace

Graph nodes and edges carry character, world, and owner subject on every row. Cross-subject edges are
rejected. Identity/Soul content is immutable and versioned; only an explicitly activated revision enters
the prompt. Autonomous TODOs are claimed once, and heartbeat execution remains disabled unless both the
feature flag and a ready executor are present.

## Privacy deletion

Deletion verifies that the principal owns the subject, removes PostgreSQL and derived rows, calls every
configured vector/cache deletion port, and records per-layer completion. A partial layer failure leaves an
auditable failed job instead of reporting success.
