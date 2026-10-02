# ADR-0011: Unreal Engine 5.8을 현재 제작 기준으로 고정한다

- 상태: Accepted
- 결정일: 2026-08-14

## 맥락

ADR-0007은 초기 Stage와 MetaHuman 통합 기준을 UE 5.6으로 고정했다. 현재 제작 장비와 QA
프로젝트는 UE 5.8.1을 사용하며, 캐릭터·렌더링·Dataflow·Chaos Cloth 개선을 포함한 5.8
도구 체계를 기준으로 파이프라인을 검증해야 한다. 문서, `.uproject`, gate가 서로 다른 엔진
버전을 요구하면 asset 호환 경고와 재현 불가능한 검증 결과가 발생한다.

## 결정

- 활성 Unreal 프로젝트와 자동화의 최소 기준은 UE 5.8이다.
- 현재 재현 가능한 검증 설치는 UE 5.8.1이며 보고서에는 patch 버전까지 기록한다.
- `.uproject`의 `EngineAssociation`은 `5.8`, 설치 경로 예시는 `UE_5.8`을 사용한다.
- UE binary asset은 하위 버전 호환을 가정하지 않는다. 5.8에서 저장한 asset을 5.6/5.7로
  다시 여는 경로는 지원하지 않는다.
- Looking Glass Go는 주요 배포 표면이다. UE 5.8 호환 plugin build와 실기 증거가 확보되기
  전까지 production release를 fail-closed로 유지하며, 일반 모니터는 개발·복구 fallback이다.
  과거 Plugin 2.1.1의 UE 5.6 지원을 5.8 지원으로 해석하지 않는다.
- 과거 iteration과 ADR은 감사 가능한 이력으로 보존한다.

## 결과

- 개발·CI·패키징 장비에는 UE 5.8 계열과 해당 버전에 맞는 MetaHuman plugin이 필요하다.
- 5.6 전용 evidence는 현재 release gate를 충족하지 않는다.
- 외부 plugin은 5.8에서 실제 compile/load한 증거가 없으면 지원 완료로 표시할 수 없다.

## 참고

- [Unreal Engine 5.8 release notes](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes)
- [ADR-0007: initial UE 5.6 baseline](0007-unreal-5-6-baseline.md)
- [ADR-0010: Looking Glass Go is the primary deployment surface](0010-looking-glass-is-an-optional-renderer.md)
