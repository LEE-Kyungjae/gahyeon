# Qwen expressive voice runtime

The Core-facing contract is `POST /v1/speech`. The worker is intentionally
separate from character cognition: a character selects a `voiceProfile`, while
the worker attests the exact model and quantization in its response headers.

## Current verified baseline

On 2026-08-19 the cached `Qwen3-TTS-12Hz-0.6B-Base` was verified on `land`
with the Gahyeon reference profile in
`config/qwen-voice-profiles-land-v001.json`.

- FP16 is rejected as the operating baseline. It produced non-finite sampling
  probabilities twice on the GTX 1660 Ti.
- FP32 generated all three bounded Korean/English benchmark cases.
- Peak allocated GPU memory: 5,457,595,904 bytes.
- Inference was 6.77-9.43 times slower than the generated audio duration.
- A real HTTP request returned a 24 kHz, 16-bit, mono PCM WAV and all three
  identity headers expected by `QwenExpressiveTtsAdapter`.
- This Base model is a voice-clone baseline, not an expressive model. The worker
  returns HTTP 422 for non-natural styles instead of silently ignoring them.

Evidence is stored under `artifacts/autonomy/qwen-land-v002/`.

## Multi-character profile contract

`QWEN_VOICE_PROFILES` points to a JSON object keyed by the stable Core voice
profile ID. Adding a character means adding a new profile; it must not reuse a
different character's reference audio merely because a model is available.

Supported execution modes are:

- `voice_clone`: preserves a supplied voice identity and currently cannot claim
  instruction-level expression control.
- `custom_voice`: uses a speaker shipped with a compatible Qwen model and may
  accept an expression instruction.
- `voice_design`: accepts an expression instruction but does not prove the
  identity of a cloned Gahyeon voice.

The runtime exposes `expressionProfiles` in `/health`. Core must only route
non-natural expression to profiles listed there.

## Land resource constraint

The verified FP32 baseline and ComfyUI cannot safely be treated as concurrent
GPU services on the 6 GiB card. The benchmark used an empty ComfyUI queue,
stopped only `zaeze-comfyui.service`, ran one bounded job, stopped the Qwen
worker, and restored ComfyUI. A persistent Qwen service must wait for a smaller
quantized runtime or move to a GPU with enough independently reserved VRAM.

## 0.6B C INT4 candidate

A second candidate was built from
`gabriele-mastrapasqua/qwen3-tts@328ab9cb241774572bb59917af199bdf64a17227`
against Ubuntu OpenBLAS on the `land` i7-7700. Its AVX2 INT4 kernel self-test
passed. The official `0.6B-CustomVoice` checkpoint was pinned at revision
`85e237c12c027371202489a0ec509ded67b5e4b5` and its model SHA-256 was verified.

This route is smaller and does not consume GPU memory. With a 4 KB Gahyeon
x-vector it measured RTF 2.28-2.36, TTFA 2.83-3.52 seconds and approximately
2.61 GiB maximum resident memory. Speaker-embedding cosine against the original
reference was 0.9766 for natural speech and 0.9544 for generic joy.

The pinned runtime's HTTP server originally called a 1.7B-only steering helper,
so 0.6B `emotion` requests were silently identical to natural speech. Gahyeon
now carries a revision-pinned patch at
`patches/qwen3-tts-c/328ab9c-http-emotion-06b.patch`. It applies the same generic
x-vector direction used by the CLI to a request-owned embedding copy, then
restores the original pointer after synthesis. This prevents style leakage and
avoids mutating the embedding shared by worker contexts. The patch also clamps
HTTP `emotion_strength` to the validated 0.15-0.35 range.

The patched runtime was rebuilt on `land`. A live Java Core test passed
`natural` plus four expression routes: `bright -> joy`,
`surprised -> surprise`, `annoyed -> anger`, and `sad -> sad`. It checked model,
quantization and voice-profile attestation and proved that each returned WAV
differs from natural. Unsupported styles such as `fake_cute` return HTTP 422
rather than being approximated by an unrelated emotion.

The five-style benchmark is stored under
`artifacts/autonomy/qwen-c-int4-land-v004/`. All files are 24 kHz, 16-bit mono
PCM. Speaker-embedding cosine to the original Gahyeon x-vector was 0.9830 for
natural and 0.9537-0.9605 for the four expressions. Request RTF was 3.56-3.73,
so this fixes transport correctness and provides a useful listening candidate,
but the i7-7700 path remains slower than real time and is not yet the production
expressive voice.

## Normal conversation routing

Desktop conversation speech now asks Core for a bounded expression prior before
opening the streamed speech sequence. The planner owns character identity and
the current persistent life state; the renderer does not invent an emotion.
For the calibrated Gahyeon profile it can select only `natural`, `bright`,
`surprised`, `annoyed`, or `sad`. A natural result keeps the low-latency default
voice, while a non-natural result opts the first streamed sentence into the
expressive worker. Planner failure falls back to natural speech and never blocks
the conversation request.

The deterministic prior remains the fallback layer. An optional small context
model can now refine it without changing Desktop, Unreal or the TTS worker. The
model receives only the current utterance, stable character/expression profile,
bounded life values, bounded relationship values and the deterministic fallback;
it never receives raw memories or full conversation history. The worker is
disabled by default, has a 180 ms default connect/read deadline, must attest the
configured model ID, and must return exactly `style`, `intensity`, and
`communicativeIntent`. Timeout, transport failure, unknown fields, invalid
styles, or invalid ranges restore the deterministic result. Relationship-tension
policy is applied after the model, so a model cannot force playful, sarcastic,
fake-cute, bright, or suppressed-laugh delivery through a high-tension state.

The initial planner target is `Qwen/Qwen3-0.6B`; this is a text classification
and control task, not the speech generator. Enable it only when its bounded
worker is available:

```text
GAHYEON_EXPRESSION_SMALL_MODEL_ENABLED=true
GAHYEON_EXPRESSION_SMALL_MODEL_ENDPOINT=http://<worker>:18772/v1/expression-plan
GAHYEON_EXPRESSION_SMALL_MODEL_ID=Qwen/Qwen3-0.6B
```

### Live Core-to-land acceptance

The complete Desktop-facing Core route was exercised on 2026-08-19 rather
than inferred from isolated adapter tests. A loopback-authenticated expression
request for character `gahyeon`, world `gahyeon-home`, and a resolved Desktop
actor returned `bright` in 196.96 ms. Core then sent that exact plan through
the attested `0.6B-CustomVoice` C INT4 worker on `land` and returned a valid
24 kHz, 16-bit mono PCM WAV.

The 3.76 second output required 20.61 seconds (RTF 5.48) in this live run. This
proves routing, authorization, character/relationship lookup, worker transport,
audio validation, and artifact delivery; it explicitly does not prove a
real-time production budget. Evidence and the playable WAV are stored in
`artifacts/autonomy/conversation-expression-live-v001/`.

Desktop now presents the same plan visually while speech is active. Voice
styles map to standard avatar expressions (`bright -> happy`,
`annoyed -> angry`, `sad -> sad`, `surprised -> surprised`, and
`calm -> relaxed`). VRM weights converge smoothly per frame and return to
neutral after the active response finishes. This is verified at the Desktop
contract layer; final MetaHuman Control Rig and physical Looking Glass
acceptance remain separate gates.

### Unreal speech-expression overlay

The Unreal wire decoder accepts the bounded `voiceProfile` and
`voiceExpression` fields emitted by Core. It rejects unknown styles instead of
inventing a facial meaning. RuntimeCore maps the supported voice styles to the
presentation profile's semantic curves (`bright -> happy`,
`annoyed -> angry`, `sad -> sad`, `surprised -> surprised`, and
`calm -> relaxed`).

Speech expression is not the character's persistent life emotion. The prepared
audio owns a validated, short-lived expression target, and the playback
coordinator starts its blend only after the audio device confirms
`PlaybackStarted`. Unreal composes that overlay with the persistent emotion by
taking the stronger value for each semantic curve. When the speech overlay
releases, the underlying life/world emotion remains visible instead of being
reset to neutral. This also prevents download or queue latency from consuming
the facial-expression window before sound begins.

RuntimeCore regression coverage proves that a persistent curiosity/amusement
state survives a bright spoken segment, that the happy overlay is absent before
playback, and that it releases without erasing the life state. The affected UE
5.8 translation, playback, protocol decoder, and runtime subsystem compile and
link successfully on macOS. The linked Editor passed all 18 `Gahyeon`
automation tests. A `-game` load of the dedicated v091 Desktop map mounted the
MetaHuman Character content plugin and resolved the configured v088 visual
Actor without the prior missing optional groom/material packages. Evidence is
stored under `artifacts/autonomy/unreal-expression-overlay-v001/`.

The production runtime profiles no longer enable the experimental Editor
Toolset or Model Context Protocol plugins. Authoring remains isolated in the
editor-only character QA project; this prevents their Python startup hooks from
throwing in `-game` mode. The microphone capture path also uses UE 5.8's current
`OpenAudioCaptureStream` API while preserving the existing float PCM STT/VAD
contract.

### Waveform-guided viseme fallback

The PCM fallback no longer spreads Korean vowel shapes uniformly over the
entire WAV duration. It parses the actual 16-bit PCM samples in 20 ms windows,
estimates a bounded adaptive noise floor, keeps the mouth closed through real
silence, and derives cue weight from observed RMS energy. Korean graphemes still
select the semantic mouth shape, so the source is explicitly reported as
`waveform-guided`, never as an exact provider.

The live Gahyeon bright sample produced 10 bounded cues over a 3.76 second WAV;
the first observed speech cue was at 480 ms and the last at 2,740 ms. Evidence
is stored under `artifacts/autonomy/waveform-guided-viseme-v001/`. This improves
fallback motion but does not satisfy the exact phoneme-alignment or visible
MetaHuman playback acceptance gates.

## Next acceptance target

A candidate is not the expressive production voice until it proves all of the
following with the same Gahyeon voice profile:

1. natural and at least four non-natural styles succeed;
2. speaker identity remains within the listening/embedding threshold;
3. Korean and English pronunciation pass listening review;
4. first-audio latency and real-time factor meet the interactive budget;
5. model ID, quantization, reference identity, VRAM and output hashes are
   recorded;
6. unsupported controls fail closed.

## 1.7B CUDA v115 result

The pinned C runtime was also built with the isolated CUDA 12.8.1 toolkit for
the `land` GTX 1660 Ti (`sm_75`). The 1.7B Base checkpoint uses the 2,048
dimension Gahyeon x-vector and mixed Q4 Talker/INT8 Code Predictor mode. A warm
HTTP request produced 9.20 seconds of audio in 7.70 seconds (RTF 0.84). The raw
streaming route delivered its first PCM audio at 1.643 seconds and produced
4.08 seconds of audio in 3.309 seconds (RTF 0.811).

The native server is patched to bind `127.0.0.1`, not `INADDR_ANY`. Its
systemd unit and the identity-attesting FastAPI bridge are installed on `land`
but deliberately disabled. Starting the candidate still requires an explicit
GPU-resource handoff from ComfyUI on this 6 GiB card; it is not promoted as an
always-on service yet.

A live acceptance exercised the real Java adapter through an authenticated
SSH-forwarded bridge, synthesized Gahyeon's `fake_cute` expression, and passed
the returned PCM WAV into `DefaultUnrealSpeechPreparationService`. Core emitted
one `speech.prepared` event with the exact expression, attested voice/model/
quantization, 22 waveform-guided visemes, and a cached 5.717 second WAV. The
full Core-side operation took 4.795 seconds (RTF 0.839). Evidence is in
`artifacts/qwen-expressive-1.7b-land-v115/`.

This clears the machine-speed and transport gates. Production promotion remains
blocked on human Korean/English listening approval, a GPU resource arbiter,
service soak/recovery testing, and visible MetaHuman playback acceptance.

The v115 bridge now also exposes authenticated `POST /v1/speech/stream`. It
validates the same voice, model, quantization and expression contract before
proxying raw 24 kHz mono s16le PCM. The separate Java streaming adapter verifies
all attestation and format headers before publishing its first chunk, preserves
PCM frame boundaries across arbitrary HTTP packet splits, bounds total bytes,
and closes immediately on generation cancellation. A live `fake_cute` request
delivered its first Core-visible PCM at 0.788 seconds and completed 4.96 seconds
of audio in 3.307 seconds (RTF 0.667). The legacy complete-WAV adapter remains
unchanged. The next gate is feeding these chunks into Unreal's existing
`USoundWaveProcedural` queue without weakening generation cancellation or the
current prepared-WAV fallback.
