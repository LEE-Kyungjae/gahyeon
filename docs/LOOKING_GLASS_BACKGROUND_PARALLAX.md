# 배경 시차를 분리한 v015 후보

v014에서 전체 캡처 각도를 줄인 뒤에도 사용자가 배경 잔상을 보고했다. v015는 가현의 캡처 깊이 설정 0.12를 유지하면서 배경에만 별도의 시차 보정을 적용한다.

## 적용 범위

- v013 방을 복제한 새 v015 맵을 사용한다. v014 설정은 복원용으로 남긴다.
- 방의 정적 메시 158개에 사용한 재질을 복제하고 World Position Offset을 연결한다. 가현의 모델과 네 개의 원본 재질은 수정하지 않는다.
- 카메라 및 모든 액터의 위치·회전·크기를 유지한다. 배경 정점은 각 시점의 렌더링 중에만 수평으로 보정한다.
- 배경의 수평 시차는 원래 값의 0.1배를 목표로 한다. 중앙 시점에서는 보정량이 0이고, 영시차면에 있는 점도 움직이지 않는다.

캡처 카메라의 기준 위치를 C, 전방 벡터를 F, 오른쪽 벡터를 R, 기준 초점 거리를 f라고 할 때 정점 P의 보정은 다음과 같다.

```text
d = dot(P - C, F)
lateral = dot(CurrentCamera - C, R)
P' = P + R * lateral * (1 - d / f) * (1 - backgroundParallaxScale)
```

이 식은 고정 회전·초점면의 off-axis 캡처를 전제로 한다. 자유 이동 카메라나 초점면이 달라지는 런타임에는 그대로 적용하지 않는다. 배경의 깊이 인상이 얕아지고 시점별 가림 관계·그림자에 변화가 생길 수 있으므로 실물 화면 검토가 필요하다. 2D 배경 이미지를 덮어씌우는 방식은 아니다.

새 방의 셰이더가 컴파일 중일 때는 첫 quilt 캡처를 보류한다. 초기 자세는 먼저 고정해 컴파일 대기로 애니메이션 시작점이 달라지지 않도록 한다.

## 생성과 검증

```sh
python3 scripts/build_gahyeon_room_v015.py
python3 scripts/build_gahyeon_room_v015.py --validate
python3 scripts/launch_gahyeon_looking_glass_room_v011.py \
  --serial LKG-E08611 --smooth \
  --room-config looking-glass-room-v015.json \
  --evidence-dir artifacts/looking-glass-room-v015
```

생성기는 기존 v015 맵을 덮어쓰지 않는다. 원본 v013 맵과 로컬 캐릭터 자산이 필요하며, 생성된 바이너리 자산과 캐시는 Git에 포함하지 않는다. 검증기는 원본과 저장된 후보를 다시 로드해 수치 변환값, 캐릭터 정체성·재질, 배경 재질의 보정 연결을 비교한다. 실행 증거는 로컬 `artifacts/looking-glass-room-v015/`에 기록한다.

맵 생성과 독립 검증은 오류 없이 종료됐으며 기존 ACL 압축 설정 경고 네 건이 남아 있다. Looking Glass 관련 검사 20개를 통과했다. 이 후보는 4초 idle의 120개 자세를 캐싱하는 미리보기이며 실시간 대화나 날씨 연동을 검증한 결과가 아니다. 사용자 시각 확인 전까지 `humanApproved: false`를 유지한다.
