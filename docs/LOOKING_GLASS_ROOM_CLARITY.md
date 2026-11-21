# Looking Glass Go 방 배경 개선

v011은 v009 방의 깊이 간격을 35%로 줄인다. 가현의 머리 깊이를 기준으로 벽과 가구를 이동하고 카메라와의 거리 비율로 가로·세로 크기를 보정한다. 정면 구도를 최대한 유지하면서 배경의 시차를 줄이려는 변경이다. 물체 전체를 투영 변환하는 방식은 아니므로 회전된 소품은 실기기에서 확인해야 한다.

바닥과 러그는 원래 위치를 유지해 화면 하단의 빈 영역과 발 접지 변화를 막는다.

V005 출력기는 인접 시점의 색을 섞지 않는다. 기존 88% + 6% + 6% 혼합은 깊이에 따라 위치가 다른 물체를 겹쳐 보이게 할 수 있었다. 시점당 248×454, 66개 시점은 유지한다. 고해상도 출력은 원본 캡처 해상도와 전송 비용을 함께 비교한 뒤 변경한다.

## 실행

C++ 런타임 모듈을 변경한 소스로 다시 빌드해야 한다. 명령 실행 모드에서는 화면 전송을 초기화하지 않으며, 대기 동작의 캡처 구간을 재생 구간과 맞춘다.

기존 canonical manifest의 Unreal 설치와 가현 v006 맵·원본 캐릭터 에셋이 필요하다. 에셋과 로컬 캐시는 이 변경에 포함하지 않는다. 맵 생성기는 v009가 없으면 먼저 생성하고 v011을 별도로 저장한다. 기존 v011이 있으면 덮어쓰지 않고 중단한다.

```sh
python3 scripts/build_gahyeon_room_v011.py
python3 scripts/build_gahyeon_room_v011.py --validate
python3 scripts/launch_gahyeon_looking_glass_room_v011.py --serial LKG-E08611 --check
python3 scripts/launch_gahyeon_looking_glass_room_v011.py --serial LKG-E08611 --smooth
```

실행기는 canonical launcher를 사용한다. 4초의 대기 동작에서 120개 포즈를 만들고 각 포즈의 다중 시점을 LZ4로 저장한다. 재생 FPS는 캐시 재생 성능이며 실시간 대화 애니메이션의 렌더링 성능을 뜻하지 않는다. 최초 생성에는 시간이 걸린다. 기존 v009 맵과 캐시는 보존한다.

## 검증과 다음 비교

- 정면 원본 타일에서 얼굴·옷·발과 배경의 구도를 확인한다.
- 시간차를 둔 실제 디스플레이 캡처로 화면이 갱신되는지 확인한다.
- 캐시 재생 간격과 decode/upload 시간을 측정한다.
- 같은 관찰 위치에서 창틀·선반의 겹침과 얼굴 선명도를 확인한다. 화면 캡처만으로 광학적 선명도를 승인하지 않는다.

상태는 `candidate`이며 사람의 시각 검토를 자동 승인하지 않는다.

## 참고 구현

- [공식 광학 설명](https://lfdocs.lookingglassfactory.com/keyconcepts/how-it-works): 기준면에서 멀어질수록 시점 중첩으로 흐려진다. 배경 깊이 조정의 근거다.
- [Bridge SDK Samples](https://github.com/Looking-Glass/bridge-sdk-samples): 카메라 투영과 장치 출력 경로의 비교 기준이다.
- [HoloVCS 렌더러](https://github.com/SethRobinson/HoloVCS/blob/main/Plugins/LookingGlass/Source/LookingGlassRuntime/Private/Render/LookingGlassViewportClient.cpp): 단계별 성능 측정과 quilt 저장을 참고한다. 평면 레이어 전용 빠른 경로는 일반 3D 캐릭터에 그대로 적용할 수 없다.
- [공식 Unreal 플러그인](https://github.com/Looking-Glass/Looking-Glass-Unreal-Plugin): 조사한 v2.2.0-rc1의 모듈 플랫폼은 Win64이며 README는 실시간 생성을 목표로 하지 않는다고 명시한다. Mac용 직접 대체재로 간주하지 않는다.
