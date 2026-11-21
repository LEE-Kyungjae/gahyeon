# Looking Glass Go 배경 잔상 비교

v014는 v013 방과 캐릭터를 유지하고 캡처 카메라의 이동 폭을 줄인 후보 설정이다. `roomDepthScale`은 장면의 배치 깊이이고, 새 `captureDepthScale`은 66개 카메라 시점의 각도 범위를 조절한다. 둘은 별개다.

Looking Glass는 한 눈에 여러 시점이 들어온다. 영시차면에서 멀리 떨어진 물체는 시점마다 다른 위치에 나타나 윤곽이 겹칠 수 있다. [공식 광학 설명](https://lfdocs.lookingglassfactory.com/keyconcepts/how-it-works)의 현상과 현재 증상이 맞지만, 물리 화면의 원인을 이것만으로 확정하지는 않는다. 현재 실행기는 모션 블러와 시간 누적 AA를 끄고 FXAA를 사용한다.

## 변경

- `captureDepthScale`: 기존 0.45, v014 후보 0.12. 보정된 54도 시야각에서 캡처 각도 범위는 24.3도에서 6.48도로 줄어든다. 디스플레이의 광학 시야각 자체는 바꾸지 않는다.
- 66개 시점을 각각 렌더링하며 시점 복제나 인접 이미지 혼합을 추가하지 않는다.
- 캐시 키에 변경된 깊이 값을 포함해 기존 넓은 시점의 이미지를 재사용하지 않는다. 기본값의 기존 캐시 경로는 보존한다.
- 입력은 유한한 0.01~1.0 범위로 제한한다. 직접 엔진을 실행할 때 잘못된 환경변수 값은 경고 후 기존 0.45로 처리한다.

## 로컬 비교

동일한 pose-0 quilt에서 창틀의 고정 패치 `(28, 20, 32, 55)`를 기준으로 수평 이동을 정수 픽셀 단위로 비교했다. 타일 크기는 248×454이며 중앙 시점 33에 대해 시점 28과 38을 비교했다.

| 설정 | 시점 28 | 시점 38 | 두 시점의 간격 |
|---|---:|---:|---:|
| v013, 0.45 | +4 px | -3 px | 7 px |
| v014, 0.12 | +1 px | -1 px | 2 px |

이 값은 렌더링된 창틀의 시차 측정이며 물리 디스플레이 잔상이나 전체 장면의 화질 점수가 아니다. 중앙 시점에서 캐릭터 전신과 기존 구도가 유지되는 것을 확인했다. 입체 깊이가 얕아지는 절충이 있으므로 사용자 시각 확인 전까지 `humanApproved: false`를 유지한다.

Unreal macOS 모듈 빌드와 Looking Glass 관련 단위 검사 20개를 통과했다. 실행 증거는 로컬 `artifacts/looking-glass-room-v014/`에 기록한다. 이 화면은 4초 idle을 120개 자세로 캐싱한 미리보기이며 실시간 대화·날씨 통합 검증에 해당하지 않는다.

## 실행과 복원

실행 중인 해당 미리보기 실행기를 종료한 뒤 다음 명령을 사용한다.

```sh
python3 scripts/launch_gahyeon_looking_glass_room_v011.py \
  --serial LKG-E08611 --smooth \
  --room-config looking-glass-room-v014.json \
  --evidence-dir artifacts/looking-glass-room-v014
```

이전 모습은 `--room-config looking-glass-room-v013.json`으로 복원한다. 기본 실행 설정과 canonical manifest는 변경하지 않는다.
