# ADR-0010: Looking Glass Go는 주요 배포 표면이다

## Status

Accepted, production release gated

## Context

Gahyeon의 최종 주요 배포 표면은 Looking Glass Go다. 일반 모니터는 제작·진단과 장치 장애 시
복구를 위한 fallback이며, Looking Glass 실기기 합격 없이 제품 배포 완료를 주장할 수 없다.
공식 Unreal Plugin 2.1.1은 UE 5.6 지원 근거이며 UE 5.8
호환 근거는 아니다. 5.8용 plugin이 검증되기 전에는 Looking Glass 경로를 fail-closed로 둔다. 소스에는
`Realtime`, `RealtimeAdaptive`, `NonRealtime` 모드, standalone/game viewport, 매 프레임
quilt 생성과 Bridge texture 전송 경로가 실제 구현되어 있다. 다만 upstream README는 현재
플러그인을 실시간 콘텐츠 생성용으로 의도하지 않았다고 명시한다. 이는 실시간 기능 부재가
아니라 성능·제품 지원 수준의 제한으로 해석한다. Plugin descriptor의 Runtime/Editor module은
Win64만 허용한다. Bridge 2.5.1 이상과 전용 GPU가 필요하며 실제 device render 비용은 아직
측정하지 않았다.

## Decision

- `Gahyeon Core → semantic event/world state → renderer` 경계를 유지한다.
- Looking Glass Plugin은 `GahyeonStage`의 주요 Win64 출력 backend이며 production release gate다.
- Plugin, Bridge 또는 Go가 없어도 Core와 일반 monitor fallback은 제작·진단·복구 목적으로
  정상이어야 하지만 이 상태를 production-ready로 판정하지 않는다.
- Go용 별도 LLM, Memory, STT, TTS 또는 Session을 만들지 않는다.
- Plugin 2.1.1과 정확한 upstream commit은 lock contract에 기록하되 source/binary는 아직
  vendoring하거나 기본 활성화하지 않는다.
- UE 5.8 호환 plugin을 포팅하고 실제 Go와 목표 GPU에서 frame pacing 및 기존 Reflex/audio
  latency budget을 통과해야 production build를 승인한다.

## Consequences

공식 플러그인의 calibration, quilt/light-field 출력과 Bridge 연동을 재사용할 수 있다. 반면
현재 upstream이 실시간 제품 용도를 보증하지 않으므로 포팅·성능·장기 안정성 책임은 프로젝트가
진다. 구현된 실시간 모드를 prototype에서 직접 측정한다. 상호작용 성능이 충분하지
않으면 `RealtimeAdaptive`/낮은 quilt 설정, Unity 기반 보조 renderer, 또는 Bridge SDK 기반 별도
renderer를 비교할 수 있으며 Core 변경은 필요하지 않다. 어떤 구현을 택하든 Looking Glass Go
실기기 출력은 최종 release gate에서 제외할 수 없다.

## Sources

- [Looking Glass Unreal Plugin repository](https://github.com/Looking-Glass/Looking-Glass-Unreal-Plugin)
- [UE 5.6 support release 2.1.1](https://github.com/Looking-Glass/Looking-Glass-Unreal-Plugin/releases/tag/2.1.1)
- [Looking Glass Bridge](https://lookingglassfactory.com/software/looking-glass-bridge)
