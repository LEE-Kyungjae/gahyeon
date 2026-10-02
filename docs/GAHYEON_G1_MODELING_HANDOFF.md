# Gahyeon G1 modeling handoff

## Authority

`artifacts/gahyeon-ch/identity-reference.json`에 등록된 사용자 제공 원본만 얼굴과
체형의 canonical evidence다. SDXL LoRA는 포즈·의상 아이디어를 탐색하는 보조
도구이며 얼굴 비율, 코선, 턱선, 눈매를 결정하는 근거로 사용하지 않는다.

자동 검증:

```bash
python3 scripts/verify_gahyeon_identity_reference.py
python3 scripts/verify_gahyeon_modeling_input.py
python3 scripts/verify_gahyeon_g1_drafts.py
python3 scripts/verify_gahyeon_g1_authoring_work_order.py
python3 scripts/build_gahyeon_identity_board.py
python3 scripts/report_gahyeon_character_pipeline.py
```

진척 보고서의 `authoring.candidateModelArtifactCount`는 `.blend`, `.fbx`, `.glb`, `.gltf`,
`.usd`, `.usdz`, `.uasset`, `.ztl` 실물만 센다. 원본 이미지, 생성 turnaround, 작업지시서,
빈 review template은 모델 자산으로 계산하지 않는다. Candidate 파일이 존재해도 G1 evidence와
사람의 승인이 없으면 gate 상태는 올라가지 않는다.

모델링 장비로 전달할 때는 전체 `artifacts/` 디렉터리를 복사하지 않는다. 다음 명령은
원본 29장을 **18장 canonical geometry evidence + 11장 supporting evidence**로 명시적으로
분류한 결정적 ZIP 및 SHA-256 sidecar를 만든다. Supporting 자료는 표정·헤어·의상·손·동작
교차검증에는 사용할 수 있지만 neutral 얼굴이나 primary body geometry를 덮어쓸 수 없다.
LoRA 결과와 정체성 후보 이미지는 패키지에 들어가지 않는다. 별도 `g1-drafts/`에 포함되는
4개 turnaround는 `identityAuthority=false`가 checksum으로 봉인된 블록아웃 보조 자료이며,
canonical 원본을 대체할 수 없다. `g1-authoring-work-order.json`은 15개 제출 시점마다 사용할
원본 anchor와 반드시 artist-authored로 표시할 후면/정수리 영역을 지정한다.

사용자는 원화를 30장이라고 설명했지만 현재 디렉터리에서 확인되는 원본은 29장이다. 이 차이는
`sourceInventory.status=count-discrepancy`로 보존하며, 없는 1장을 임의로 추정하거나 생성해
canonical evidence로 채우지 않는다. 현재 29장은 모두 canonical 또는 supporting으로 분류되어 있다.

```bash
python3 scripts/package_gahyeon_g1_handoff.py
python3 scripts/verify_gahyeon_g1_handoff.py artifacts/gahyeon-g1-handoff.zip
```

ZIP 안의 원본 이미지는 Windows, Blender, Unreal에서 한글·공백 파일명이 깨지는 일을
막기 위해 `references/canonical/ref-003.png` 또는
`references/supporting/ref-019.png` 형태의 ASCII 별칭으로 저장한다. 원래 파일명,
원본 인덱스, 권위 분류, 크기와 SHA-256은 `package-manifest.json`의 `references`에
보존되므로 별칭이 원본 추적성을 잃게 만들지 않는다. 로컬의 사용자 제공 원본 파일은
이 과정에서 이름을 바꾸거나 수정하지 않는다. 모델러용 `README.md`와 Excel 등에서
바로 열 수 있는 UTF-8 `reference-map.csv`도 ZIP에 포함된다.

## Modeling anchors

- **중립 얼굴 마스터: 03**
- 3/4·깊이 보강: 06
- 좌우 측면 얼굴: 07, 08
- 상하 각도 교차 검증: 09, 10
- 표정 범위: 01, 04, 05, 11
- 헤어·스타일 참고만 사용: 24, 27
- 정면 전신 마스터: 16
- 측면/3/4 전신: 19, 20
- 동작·다른 의상 검증만 사용: 02, 28, 29
- 대표 헤어: 03, 24, 27
- 대표 의상: 16, 19, 20

번호와 실제 파일의 연결, 체크섬 및 세부 규칙은
`artifacts/gahyeon-ch/modeling-input.json`을 따른다.

Supporting evidence는 다음처럼 제한해 사용한다.

- 12, 13: 상반신 중립/3/4 의상 깊이와 헤어 겹침
- 14, 15: 미소와 팔 자세에 따른 표정·재킷 변형
- 17: 인사 표정과 한쪽 손바닥 참고
- 18, 23: 정면 전신 비율의 secondary cross-check
- 21, 22: 보행·contrapposto와 의상 변형
- 25: 다른 의상으로 가려진 상태에서의 체형 silhouette 교차검증
- 26: 다른 조명·후드 환경의 얼굴/헤어 cross-check

이 11장은 모두 `neutral-face-geometry`, `primary-body-geometry`,
`canonical-rear-evidence`에서 제외된다. 빠뜨리지는 않되 평균내어 정체성을 흐리지 않는다.

원본 역시 생성 이미지이므로 장마다 미세한 얼굴 차이가 있다. 모든 이미지를 같은
비중으로 평균내지 않는다. 03의 neutral landmark를 유지한 상태에서 06/07/08로
얼굴 깊이와 측면 실루엣을 제한한다. 01/04/05/11은 표정 변형 후에도 동일인인지
검증하는 자료이며 neutral mesh를 다시 정의하지 않는다.

## What can be authored now

1. MetaHuman 후보 얼굴을 고르고 neutral facial landmarks를 원본에 맞춘다.
2. 정면과 양측면을 동시에 비교하며 눈 간격, 코 폭/돌출, 입술, 턱과 광대 부피를
   맞춘다. 단일 정면 사진만 맞추지 않는다.
3. 기존 MetaHuman body preset은 전신 원본의 머리-신장 비율과 어깨·허리·골반
   silhouette에 맞춰 선택한다.
4. 대표 헤어의 앞머리, 가르마, 측면 clump를 먼저 blockout한다.
5. 대표 재킷은 styling reference로 분리하고 몸 mesh에 굽지 않는다.

## Evidence gaps

현재 자료에는 정사영 후면 전신, 헤어 후면/정수리, 중립 손 앞뒤 세트(17번에는 한쪽 손바닥만 있음), 가려지지 않은 귀,
구강 내부와 대표 의상 후면 구조가 없다. 이 영역은 임시 blockout은 가능하지만
G1 승인본으로 표시하면 안 된다. 추가 원화 또는 명시적인 artist-authored design
승인을 거쳐야 한다.

## G1 exit criteria

- neutral 얼굴이 정면·3/4·양측면에서 동일 인물로 유지된다.
- 정면·측면·후면 model sheet의 신체 비율이 일치한다.
- 헤어 실루엣과 대표 의상의 앞/옆/뒤 구조가 확정된다.
- 원본에서 관찰한 부분과 새로 설계한 부분이 구분되어 기록된다.
- G1 승인 전에는 Hero Asset manifest를 `hero-master` 승인 상태로 만들지 않는다.

실제 제출은 `artifacts/gahyeon-ch/g1-review-template.json`을 복제해 작성한다.
`scripts/verify_gahyeon_g1_review.py`는 얼굴 5시점, 몸 3시점, 헤어 4시점,
의상 3시점의 총 15개 증거와 모델 파일의 체크섬을 검증한다. 원본에 없는 후면 몸,
후면·정수리 헤어와 의상 후면은 `artist-authored-completion`으로 표시해야 하며
canonical 관측 자료로 위장할 수 없다. `approved` 상태에는 identity reviewer,
technical reviewer, operator의 독립적인 승인과 unresolved blocking finding 0개가 필요하다.

새 작업본은 템플릿을 수동 복사하기보다 현재 identity/modeling checksum을 자동으로
결합하는 다음 명령으로 만든다. 기존 파일은 안전을 위해 덮어쓰지 않는다.

```bash
python3 scripts/create_gahyeon_quality_review.py \
  --gate G1 \
  --identity artifacts/gahyeon-ch/identity-reference.json \
  --modeling artifacts/gahyeon-ch/modeling-input.json \
  --output artifacts/gahyeon-ch/g1-review.json
```

모델러 캡처 파일을 review JSON에 수동으로 붙이지 않는다. 캡처는 review workspace
안에 저장한 뒤 등록 CLI로 checksum과 semantic view를 원자적으로 기록한다.

```bash
python3 scripts/record_gahyeon_quality_evidence.py \
  --review artifacts/gahyeon-ch/g1-review.json \
  --view face-neutral-front \
  --capture-type viewport-render \
  --authority canonical-observed \
  --file artifacts/gahyeon-ch/g1-evidence/face-neutral-front.png
```

G1은 `canonical-observed` 또는 `artist-authored-completion`, G2는 해당 G2 authority를
명시한다. G3~G5는 authority 인자를 받지 않는다. 같은 semantic view를 두 번 넣거나
review workspace 밖의 파일·symlink를 넣을 수 없으며 approved/rejected review는
수정할 수 없다.

완성 모델 파일도 JSON에 직접 경로·크기를 적지 않고 같은 workspace 안에서 봉인한다.

```bash
python3 scripts/record_gahyeon_quality_artifact.py \
  --review artifacts/gahyeon-ch/g1-review.json \
  --format glb \
  --file artifacts/gahyeon-ch/models/gahyeon-g1.glb
```

G1은 단일 `modelArtifact`라 `--role`을 받지 않는다. G2~G5는 schema에 정의된
`--role`을 반드시 지정하며 같은 역할을 두 번 등록할 수 없다. 파일 byte size와
SHA-256은 도구가 계산하고, 검증 실패 시 기존 review를 바꾸지 않는다.

15개 시점과 모델 artifact가 모두 준비되면 기술 완성본으로 전환한다. `candidate`는 단순
표시가 아니라 필수 evidence, checksum과 audit 조건을 전부 통과했다는 뜻이다.

```bash
python3 scripts/transition_gahyeon_quality_review.py \
  --review artifacts/gahyeon-ch/g1-review.json \
  --to candidate

python3 scripts/record_gahyeon_quality_approval.py \
  --review artifacts/gahyeon-ch/g1-review.json \
  --role identity-reviewer \
  --reviewer gahyeon-identity-owner
python3 scripts/record_gahyeon_quality_approval.py \
  --review artifacts/gahyeon-ch/g1-review.json \
  --role technical-reviewer \
  --reviewer gahyeon-character-technical
python3 scripts/record_gahyeon_quality_approval.py \
  --review artifacts/gahyeon-ch/g1-review.json \
  --role operator \
  --reviewer gahyeon-release-operator

python3 scripts/transition_gahyeon_quality_review.py \
  --review artifacts/gahyeon-ch/g1-review.json \
  --to approved
```

승인은 candidate에서만 기록하며 역할 중복을 허용하지 않는다. `approved` 전환은 세 역할
승인과 unresolved blocking finding 0개를 다시 검증한다. 반려하려면 finding을 먼저 남기고
`--to rejected`를 사용하며, rejected review를 재활용하지 않고 새 revision을 만든다.

```bash
python3 scripts/record_gahyeon_quality_finding.py \
  --review artifacts/gahyeon-ch/g1-review.json \
  add --severity blocking --summary "정면과 측면의 눈·코·턱 비율 불일치"

# 교정 증거를 다시 등록하고 검수한 뒤에만 해결 처리
python3 scripts/record_gahyeon_quality_finding.py \
  --review artifacts/gahyeon-ch/g1-review.json \
  disposition --id G1-001 --status resolved
```

Blocking finding은 `accepted-risk` 처리할 수 없다. 얼굴 정체성이나 모델 무결성 문제를
승인 절차로 덮지 않고, 실제 교정 후 `resolved`로 종결해야 한다.

```bash
python3 scripts/verify_gahyeon_g1_review.py \
  artifacts/gahyeon-ch/g1-review-template.json

# 실제 완성본 승인 여부까지 검사할 때
python3 scripts/verify_gahyeon_g1_review.py path/to/g1-review.json --require-approved
```

Hero manifest v2에서 현재 단계는 `status=draft`, `gate=G1`이다. `qualityTier=hero-master`를
미리 기입할 수는 있지만 이는 목표 package tier일 뿐 승인을 뜻하지 않는다. 실제 package가
생기면 `identity-reference.json`과 `modeling-input.json`의 SHA-256을 `sourceManifests`에
결합하고, G1~G5 증거가 전부 생기기 전에는 `status=approved`로 바꾸지 않는다.

## Current generated drafts

`artifacts/gahyeon-ch/g1-drafts/`에는 얼굴 4-view와 전신 3-view 초안이 있다.
생성 결과는 모델링 blockout과 MetaHuman 후보 비교에만 사용한다. 얼굴 v1은 03번보다
눈과 턱이 약간 미화되어 `needs-revision`이며, 이를 교정한 v2는 `candidate-review`다.

## Blender authoring bootstrap

실제 저작 시작 장면은 `artifacts/gahyeon-g1-authoring/`에 준비한다. 현재 bootstrap은
Blender 5.2 LTS에서 열리는 `.blend`, checksum-bound scene plan, 추출된 handoff를 함께
보관하며 canonical 18장과 supporting 11장을 서로 다른 컬렉션에 로드한다. 15개 G1
evidence camera도 미리 배치되어 있다. 180cm A-pose 초깃값의 대칭면·신체/얼굴 landmark는
`G1_GUIDES_NON_AUTHORITATIVE` 컬렉션에 분리되어 있으며 반드시 canonical 원본에 맞춰
조정해야 한다. Supporting 컬렉션은 헤어·의상·표정·포즈를
교차검증하는 용도이며 neutral geometry의 source anchor로 승격되지 않는다.

Bootstrap의 `ROOT_Gahyeon_G1`은 좌표계 루트일 뿐 캐릭터 mesh가 아니다. 따라서 이 파일은
G1 candidate model이나 진척률로 계산하지 않으며, 실제 얼굴·몸·눈/치아·헤어·의상 mesh를
저작하고 15개 evidence를 렌더링한 뒤에만 `artifacts/gahyeon-ch/models/`에 제출한다.

MetaHuman 또는 커스텀 FBX/GLB/glTF base가 준비되면 원본 bootstrap을 덮어쓰지 않고 다음처럼
새 작업본으로 가져온다. Import된 모든 object에는 source SHA-256과 `unreviewed-base` 상태가
기록되며 armature와 mesh가 각각 rig/body 컬렉션으로 분리된다. 이 상태 역시 G1 승인이 아니다.

```bash
blender artifacts/gahyeon-g1-authoring/gahyeon-g1-authoring-bootstrap.blend \
  --background --python scripts/blender_import_gahyeon_g1_base.py -- \
  --base path/to/metahuman-or-custom-base.glb \
  --output artifacts/gahyeon-g1-authoring/gahyeon-g1-base-imported.blend
```
전신 v2는 얼굴을 다시 보정했지만 전신 픽셀 밀도상 근접 얼굴 승인에는 사용할 수 없다.
전신 초안의 후면은 원본에 없는 `artist-authored-hypothesis`다. 정확한 checksum,
입력 anchor와 허용 용도는
`g1-drafts/drafts-manifest.json`에 기록한다. 이 초안은 canonical manifest에 추가하지 않는다.

실제 모델링 시작점은 초안 이미지 단독이 아니라
`artifacts/gahyeon-ch/g1-authoring-work-order.json`이다. 이 파일은 원본·modeling input·초안
manifest의 SHA-256을 묶고, G1의 15개 제출 시점을 정확히 한 번씩 요구한다. 정면/측면에서
관찰 가능한 항목은 `canonical-observed`, 원본에 없는 몸 후면·헤어 후면/정수리·의상 후면은
`artist-authored-completion`으로 고정된다. 전달 ZIP에는 이 작업 명세와 checksum이 검증된
4개 초안이 함께 들어가지만 초안의 `identityAuthority=false`는 유지된다.

## Blender authoring bootstrap

Blender는 G1부터 반드시 사용해야 하는 유일한 도구는 아니다. UE 5.8 MetaHuman에서 만든
후보를 그대로 검토할 수도 있다. 다만 커스텀 얼굴·체형, 헤어, 의상, UV와 export를 수정할
경우에는 동일한 G1 입력과 검수 카메라를 재현하도록 아래 bootstrap을 사용한다. 이 도구는
캐릭터 형상을 자동 생성하지 않으며, 사람의 조형 작업을 위한 빈 작업 구조만 만든다.

```bash
mkdir -p /path/to/gahyeon-g1-handoff
unzip artifacts/gahyeon-g1-handoff.zip -d /path/to/gahyeon-g1-handoff
cd /path/to/gahyeon-g1-handoff

python3 tools/build-g1-scene-plan.py \
  --handoff-dir . \
  --output work/gahyeon-g1-scene-plan.json

blender --background --factory-startup \
  --python tools/blender-bootstrap-g1.py -- \
  --plan work/gahyeon-g1-scene-plan.json \
  --handoff-dir . \
  --output work/gahyeon-g1-blockout.blend
```

두 Python 도구는 ZIP 내부에 포함되므로 제작 머신에서 이 저장소를 별도로 clone할 필요가 없다.
Windows에서는 같은 인자를 `py`와 Blender 실행 파일 경로에 전달하면 된다. ZIP 자체를 작업
디렉터리처럼 수정하지 말고 압축을 푼 디렉터리의 `work/` 아래에 새 결과물을 생성한다.

부트스트랩은 카메라 이름만 만드는 것이 아니라 얼굴 정면·양 3/4·양측면, 몸 정면·측면·후면,
헤어 앞·옆·뒤·정수리, 의상 앞·옆·뒤의 위치·target·orthographic scale을 centimeter 단위로
봉인한다. 모델링 후 아래 명령으로 정확히 15개 1024x1024 투명 PNG를 렌더한다.

```bash
blender work/gahyeon-g1-blockout.blend --background \
  --python tools/blender-render-g1-evidence.py -- \
  --plan work/gahyeon-g1-scene-plan.json \
  --output-dir work/evidence
```

렌더러는 scene-plan checksum이 다른 `.blend`, 모델 mesh가 하나도 없는 scene, 변경되거나
누락된 evidence camera, 비어 있지 않은 출력 디렉터리를 거부한다. 레퍼런스 이미지와 카메라
오브젝트는 render에서 숨기며 15개가 모두 성공한 뒤에만 최종 파일명으로 승격한다. 생성된
파일명은 제출 도구가 요구하는 semantic view와 정확히 일치한다.

## G1 candidate return package

모델러는 임의의 링크나 캡처 목록을 전달하지 않는다. 작업지시서의 semantic view 이름과
정확히 같은 15개 PNG를 `work/evidence/`에 저장하고, ZIP에 포함된 제출 도구로 모델과 함께
봉인한다. 누락된 시점, 64x64 미만 또는 PNG가 아닌 캡처, 확장자와 format이 다른 모델,
변조된 handoff 입력, 기존 출력 덮어쓰기는 모두 거부된다.

```bash
python3 tools/package-g1-submission.py \
  --handoff-dir . \
  --model work/gahyeon-g1.blend \
  --format blend \
  --evidence-dir work/evidence \
  --output work/gahyeon-g1-submission.zip
```

반환된 ZIP은 프로젝트에서 다음 명령으로 검증한다.

```bash
python3 scripts/verify_gahyeon_g1_submission.py \
  /path/to/gahyeon-g1-submission.zip
```

제출 도구는 기술적으로 완전한 `candidate` review를 생성하지만 사람의 승인이나 품질 합격을
꾸며내지 않는다. `approvals`는 빈 배열로 유지되며 identity reviewer, technical reviewer,
operator의 실제 검토 이후에만 기존 승인 도구로 G1을 `approved`로 전환한다.

계획 생성기는 ZIP에서 봉인된 파일 크기와 SHA-256을 다시 검사하며, supporting 이미지를
neutral geometry anchor로 승격한 작업지시서를 거부한다. Blender 단계는 centimeter 단위,
몸·얼굴·눈/치아·헤어·의상·rig 분리 collection, 15개 evidence camera, 사용된 canonical
reference와 원본 checksum을 씬에 기록한다. 기존 `.blend` 파일은 덮어쓰지 않는다.

2026-08-12 현재 개발 Mac에는 Blender 5.2.0 LTS를 설치했고, 실제 headless 실행으로
bootstrap `.blend` 생성, 임시 smoke mesh의 15개 PNG 렌더, candidate ZIP 생성과 독립 검증까지
통과했다. 이 임시 mesh는 G1 모델이나 품질 증거가 아니며 매 실행 후 삭제된다. 동일한 물리
도구체인 검사는 다음 명령으로 재현한다.

```bash
bash scripts/test_blender_g1_pipeline.sh
```
