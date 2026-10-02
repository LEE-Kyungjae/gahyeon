# Character Life Runtime

The Character Life Runtime is the shared engine for long-lived characters such as Gahyeon and Diana.
It is deliberately separate from the renderer, conversation provider, and shared World State.

## Ownership boundaries

- World State owns rooms, positions, shared objects, and publicly observable events.
- Character Life State owns one character's mood, needs, attention, activity, goals, intentions, and initiative history.
- Memory owns past episodes, learned facts, relationships, working context, and prospective memories. Every record must carry a character ID.
- Cognition turns an admitted life decision into language or a plan. It does not own homeostasis.
- Expression Plan drives voice, face, gaze, gesture, and resumption of the interrupted activity from one intent.
- Desktop, Unreal, Looking Glass, and a possible stream are interchangeable embodiments.

## Decision loop

```text
shared world event / elapsed time / user interaction
                     |
                     v
          character-specific perception
                     |
                     v
         deterministic homeostasis update
                     |
                     v
             initiative admission
       /              |              \
  silence      internal/action      cognition
                                      |
                                      v
                              expression plan
                                      |
                                      v
                        character-scoped cognition
                         /                    \
                    silence              utterance
                                           |
                              voice + face + gaze + gesture
```

The default outcome is silence. A thought does not become speech unless it clears the character's initiative threshold and cooldown. Time-sensitive events may request cognition; other meaningful events become attention or nonverbal action.

## Multi-character isolation

Persistent state and autonomous memory are keyed by `(character_id, world_id)`. Gahyeon and Diana may observe the same world event but update separate needs, attention, memories, and relationships. A character definition is rejected when it is applied to another character's state. Autonomous cognition never reads the user conversation history keyed only by actor ID.

## Current vertical slice

- Persistent per-character needs and activity state
- Separate Gahyeon and Diana definitions
- Data-driven character catalog; additional personalities require configuration rather than runtime code
- One explicit primary character. Gahyeon is the primary character; all others are peers, guests, or supporting characters.
- Time-based homeostasis
- Silence, internal change, action, and cognition dispositions
- Initiative cooldown
- A shared expression contract for voice, face, gaze, gesture, and activity resumption
- Character-specific persona prompt resources selected from the data-driven catalog
- Desktop character selection is carried through the Electron IPC security boundary into the Core session
- Character-scoped interactive sessions exclude the legacy actor-wide conversation memory
- Completed interactive turns are written back to the selected character/world memory and advance its life state
- One speech sequence pins the selected character's voice profile across all streamed sentence segments
- Tool-free autonomous LLM cognition with strict JSON output
- Character/world-scoped reflection and utterance memory
- User-private memory is additionally scoped by actor subject; autonomous cognition sees global memory only
- Typed `working`, `episodic`, `semantic`, `relationship`, `prospective`, `reflection`, and `utterance` records
- Confidence, importance, emotional weight, expiry, access time, and namespace fingerprint metadata
- Stable topic `memoryKey` with confidence-aware supersession; superseded history remains auditable but not recallable
- Tool-free memory consolidation with confidence admission and idempotent deduplication
- Salience/decay recall so durable important memories outrank recent low-value chatter
- Consolidated prospective memory is promoted into Life State and consumed on user return
- Persistent relationship state per `(character, world, actor)` with familiarity, trust, affinity, and tension
- Accepted relationship memories update bounded relationship dimensions and condition the selected character's system context
- Explicit `speak=false` support; an admitted cognition may still choose silence
- `character.cognition.completed`, `skipped`, and `failed` world events
- Failure isolation so one provider error does not stop later life decisions
- Desktop inspection and stimulus endpoints
- A provider-neutral expressive speech contract carrying bounded style, continuous intensity,
  communicative intent, and character voice identity
- A fail-closed Qwen HTTP adapter that requires response attestation for voice profile, model ID,
  quantization, and bounded PCM WAV bytes
- Desktop autonomous-cognition admission: only the selected character may speak, and it stays
  silent during user capture, transcription, an active conversation, or another utterance

The cognition-completed event is the renderer/voice handoff. It includes `spoken`, optional `utterance`, `voiceProfile`, `expressionProfile`, and one `expressionPlan`; consumers must not infer speech from the original life decision alone. Desktop now consumes this handoff through the expressive endpoint. If the expressive worker is absent, the utterance is not silently flattened into neutral Piper/VoiceBox output.

## Expressive Qwen worker contract

The Core-side adapter is disabled by default. A worker is enabled only with all of:

```text
GAHYEON_QWEN_EXPRESSIVE_TTS_ENABLED=true
GAHYEON_QWEN_EXPRESSIVE_TTS_ENDPOINT=http://<worker>:18770/v1/speech
GAHYEON_QWEN_EXPRESSIVE_TTS_MODEL_ID=<exact checkpoint id>
GAHYEON_QWEN_EXPRESSIVE_TTS_QUANTIZATION=<exact runtime quantization>
```

The worker request contains `text`, `voiceProfile`, a vocabulary-bounded `style`, intensity in
`[0,1]`, `communicativeIntent`, exact `modelId`, exact `quantization`, and `responseFormat=wav`.
The response must be PCM WAV and repeat the exact identity in
`X-Gahyeon-Voice-Profile`, `X-Gahyeon-Model-Id`, and `X-Gahyeon-Quantization`.
Missing or mismatched attestation fails closed. This prevents an accidental model, speaker, or
neutral fallback from being presented as Gahyeon's expressive voice.

Qwen currently publishes 0.6B and 1.7B TTS backbones. The smaller model requested for the
architecture is therefore the Expression Planner, not a fictional sub-0.6B Qwen TTS checkpoint.
The voice backbone remains independently replaceable and must pass latency, identity, Korean and
English pronunciation, and blind expressive listening gates before activation.

Interactive turns now enter expiring working memory and an immutable factual episode; the consolidation worker may derive semantic, relationship, and prospective memories only above the confidence threshold. Semantic contradictions are merged by stable topic and relationship evidence updates a longitudinal actor edge. More nuanced relationship-event semantics, cross-topic belief consistency, the physical Qwen worker, Unreal autonomous-audio handoff, and synchronized body expression remain follow-up slices.
