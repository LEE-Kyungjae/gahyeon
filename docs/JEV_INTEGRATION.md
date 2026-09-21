# Jev decisions in Gahyeon

Jev `jev-1.13.0` supplements bounded semantic decisions. It does not generate replies,
authorize tools, modify identity verification, synthesize audio, or operate the Unreal runtime.

## Runtime connections

- `JevExpressionModel` supplies the existing `ConversationExpressionModel` port. The
  application service still applies relationship tension and intensity restrictions.
- Discord `VoiceAssistantExpressionPolicy` also uses Jev when available, with its
  original keyword policy as fallback. No Discord identifiers are sent.
- `AgentPromptProvider` ranks up to 24 authorized, unexpired memories through
  `JevMemoryReranker`, then keeps 16. Only character-scoped sessions with a current
  query qualify. Ordinary Discord sessions without character scope do not use this path.
  The existing memory store filters subject/character/world before the external call.
  The adapter rejects mixed scopes and sends text with request-local ordinals only.

## Credentials and switches

The application optionally imports `~/.config/gahyeonbot/jev.properties`. The local
credential file is outside the repository, mode `0600`, in a `0700` directory. Never
copy it into an image, artifact, test fixture, or commit. This machine is configured
with the supplied credential; deployment machines need their own secret injection.

Environment configuration for other runtimes:

```text
GAHYEON_JEV_ENABLED=true
TYPESAFE_API_KEY=<secret injected by the runtime>
GAHYEON_JEV_EXPRESSION_ENABLED=true
GAHYEON_JEV_MEMORY_ENABLED=true
```

Disable both adapters with `GAHYEON_JEV_ENABLED=false`. Disable individual uses with
the corresponding feature flag. Local file values may also set `gahyeon.jev.enabled`;
runtime environment properties override the file. Test profile disables Jev.

Default deadlines are 450 ms for expression and 800 ms for memory, including the HTTP
response body. There are at most two in-flight calls, no retries, a five-second failure
cooldown, bounded request/response bodies, and no redirect following. A busy provider,
timeout, malformed response, changed model identity, or uncertain decision retains
the original rule or memory ordering. There is no cross-user cache.

Choice requires confidence >= 0.6 and selected probability >= 0.7. Memory scores
require confidence >= 0.5 for every candidate; otherwise the whole batch retains its
original order. These are conservative initial thresholds, not calibrated Korean
accuracy guarantees. The first cold TLS call can exceed the expression deadline.

Only aggregate `gahyeonbot.jev.decisions`, `gahyeonbot.jev.fallback`, and
`gahyeonbot.jev.latency` metrics are emitted. No raw text, API response, key, user ID,
or memory ID is logged by the adapter. Conversation/memory text is sent to TypeSafe
when a feature is enabled; excluding IDs is not full anonymization of text content.

## Verification and operational boundary

Focused deterministic coverage includes unknown choices, wrong model identity,
missing answer batches, oversized responses, provider errors, deadlines, disabled
credentials, uncertain predictions, Spring bean selection, scope/expiry filtering,
Discord fallback, and final memory limits.

Run focused tests without credentials:

```bash
./gradlew test --tests 'com.gahyeonbot.adapters.jev.*' \
  --tests 'com.gahyeonbot.services.ai.agent.AgentPromptJevRerankingTest' \
  --tests 'com.gahyeonbot.adapters.discord.voice.VoiceAssistant*Expression*Test'
```

Opt-in live evaluation (synthetic Korean text only, consumes a small number of API calls):

```bash
GAHYEON_JEV_LIVE_SMOKE=true ./gradlew test \
  --tests 'com.gahyeonbot.adapters.jev.JevLiveSmokeTest' --rerun-tasks
```

The live report is `artifacts/autonomy/jev-integration/live-smoke.json`. Its diagnostic
deadline is 1500 ms to measure cold/warm behavior, explicitly different from runtime
deadlines. The final nine-case run selected appropriate expressions in seven cases,
retained the correct baseline for one uncertain case, and reranked one memory pair
correctly. Warm measured decisions took 209–288 ms; the cold call took 690 ms. This
small, hand-authored smoke set is not a blind TTS comparison or production validation.

No production deployment or service restart is part of this change. Before production
promotion, use the autonomy contract and canary evaluator, record the deployed commit,
artifact digest and revision, and collect qualifying traffic over at least 30 minutes.
Disable Jev on incorrect semantic decisions, subject-scope exposure, or p95 latency
regression above 300 ms; production rollback requires the repository's release authority.
No production incident was discovered in this work, so no incident was added to the
production regression catalog.

References: https://docs.typesafe.ai/concepts/use-case-map and
https://docs.typesafe.ai/introduction/quickstart.
