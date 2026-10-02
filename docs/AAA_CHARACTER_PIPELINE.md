# Gahyeon AAA hero character pipeline

Unreal runtime 구조와 단계별 PoC 순서는
[`unreal/ARCHITECTURE.md`](unreal/ARCHITECTURE.md) 및
[`unreal/VERTICAL_SLICE.md`](unreal/VERTICAL_SLICE.md)를 따른다.

## 목표와 범위

Gahyeon의 캐릭터 목표는 범용 아바타 생성기가 아니라 **가현 한 명의 hero
character**다. 품질 기준은 얼굴, 피부, 눈, 머리카락, 의상, 표정과 움직임이
근접 카메라에서도 설득력을 유지하는 실사 AAA 캐릭터다. SDXL LoRA나 VRM
파일 하나를 최종 결과로 간주하지 않는다.

현재 LoRA는 다음 용도로만 사용한다.

- 얼굴 정체성 탐색과 고정
- 정면/측면/전신 reference 생성
- 헤어와 의상 direction 탐색
- 3D 제작 단계의 승인 가능한 reference pack 생성

## 자산 계층

```text
Gahyeon Hero Master
├─ source sculpt / retopology / rig
├─ 8K authoring textures and bake sources
├─ facial rig and animation source
├─ strand groom source
├─ Hero Desktop package
│  ├─ LOD0/LOD1 body and face
│  ├─ strand groom
│  └─ full facial deformation
├─ Desktop Performance package
│  ├─ LOD1/LOD2
│  └─ groom cards
├─ Looking Glass package
│  ├─ stable card/mesh hair
│  └─ bounded material and animation cost
└─ VRM compatibility package
   └─ Core/animation integration fallback, not the quality master
```

모든 파생본은 동일한 `characterId`, skeleton semantic, expression semantic,
viseme semantic과 material naming을 공유한다. Core는 어떤 파생본이 렌더링되는지
알지 않는다.

Hero 자산 registry 계약은
[`contracts/gahyeon-hero-asset.schema.json`](contracts/gahyeon-hero-asset.schema.json)을
따른다. `qualityTier=hero-master`는 제작 목표일 뿐 승인 상태가 아니다. Manifest v2는
`draft → candidate → approved → retired` lifecycle과 현재 G1~G5 gate를 별도로 기록한다.
`approved`는 G5까지의 URI/SHA-256 증거, canonical identity/modeling manifest digest,
실제 package byte size와 명시적인 승인자·승인 시각이 모두 있어야 한다. 따라서 빈 예시나
G1 blockout을 Hero master로 로드할 수 없다.

Gate review에서 `draft`는 불완전 작업을 허용하지만 `candidate`는 검수 가능한 기술
완성본이다. 따라서 candidate도 해당 gate의 필수 evidence, artifact, checksum과 audit
임계값을 전부 만족해야 한다. `approved`는 완전한 candidate 위에 gate별 reviewer 승인과
unresolved blocking finding 0개를 추가한 상태다. 빈 candidate나 승인자만 채운 미완성
candidate는 schema와 verifier 양쪽에서 거부한다.

G1 acceptance evidence는 임의의 이미지나 메모 파일이 아니라
`gahyeon-g1-review.schema.json`을 만족하는 승인 JSON이어야 한다. Hero 검증기는
G1 review의 15개 시점, 모델 artifact, 3자 승인과 source manifest digest를 다시
검증하며, Hero와 G1이 서로 다른 원본 집합에 묶여 있으면 G5 승격을 거부한다.
G2 evidence도 승인된 `gahyeon-g2-review` JSON이어야 하며 Hero가 채택한 G1의
정확한 SHA-256에서 파생된 G2만 허용한다. 따라서 다른 얼굴 blockout에서 만든
고해상도 sculpt나 topology를 뒤늦게 섞어 넣을 수 없다.

## Review workspace 생성

정적 템플릿의 SHA-256을 손으로 복사하지 않는다. 각 단계 시작 시 같은 review
workspace 안에서 생성 CLI를 실행한다.

```bash
# G1 시작
python3 scripts/create_gahyeon_quality_review.py \
  --gate G1 \
  --identity artifacts/gahyeon-ch/identity-reference.json \
  --modeling artifacts/gahyeon-ch/modeling-input.json \
  --output artifacts/gahyeon-ch/g1-review.json

# G2 시작: 기본적으로 승인된 G1만 허용
python3 scripts/create_gahyeon_quality_review.py \
  --gate G2 \
  --previous artifacts/gahyeon-ch/g1-review.json \
  --output artifacts/gahyeon-ch/g2-review.json
```

G3~G5도 같은 방식으로 바로 이전 승인 JSON을 `--previous`에 준다. 출력 파일이 이미
있으면 덮어쓰지 않으며, predecessor와 출력이 다른 디렉터리에 있으면 거부한다.
`--allow-unapproved-predecessor`는 미리 workflow 형태만 검토하는 planning 용도이며
실제 gate 진입이나 Hero 승인에는 사용할 수 없다.

현재 상태는 템플릿 파일 수나 작업자의 메모가 아니라 실제 review 검증 결과로 보고한다.

```bash
python3 scripts/report_gahyeon_character_pipeline.py \
  --workspace artifacts/gahyeon-ch
```

리포터는 `*-review-template.json`을 작업 시작으로 계산하지 않는다. 실제
`g1-review.json`~`g5-review.json`만 읽어 `not-started`, `draft`, `candidate`,
`approved`, `rejected`, `invalid`를 구분하고 현재 active gate와 Hero package 준비
여부를 출력한다.

Evidence 파일은 같은 workspace 안에 둔 뒤
`scripts/record_gahyeon_quality_evidence.py`로 등록한다. 이 도구는 파일 SHA-256을
직접 계산하고 schema와 전체 review를 재검증한 후 원자적으로 교체한다. 중복 view,
잘못된 capture type, 외부 경로·symlink, 승인/거부 후 변경은 실패하며 기존 JSON은
그대로 보존된다.

Model/rig/groom/animation/build artifact는
`scripts/record_gahyeon_quality_artifact.py`로 봉인한다. G1 단일 model artifact와
G2~G5 역할별 artifact를 구분하고 byte size·SHA-256을 자동 기록하며, 같은 역할의
교체가 필요하면 기존 승인 계보를 조용히 덮지 않고 새 review revision을 만든다.

필수 artifact와 evidence가 모두 등록된 뒤에만 review를 `candidate`로 전환한다.
전환 도구는 대상 상태의 전체 schema와 gate verifier를 임시 파일에서 먼저 통과시킨 뒤
원본을 원자적으로 교체하므로, 미완성 draft가 candidate로 표시되거나 실패한 전환이
review를 훼손하지 않는다.

```bash
python3 scripts/transition_gahyeon_quality_review.py \
  --review artifacts/gahyeon-ch/g1-review.json \
  --to candidate
```

Candidate 승인도 JSON을 손으로 수정하지 않는다. Gate schema에 정의된 각 역할의 독립
승인을 기록한 뒤 `approved`로 전환한다. 같은 역할의 중복 승인, 빈 reviewer, draft에 대한
승인은 거부된다. 승인 전환 시 unresolved blocking finding이 하나라도 있으면 실패한다.

```bash
python3 scripts/record_gahyeon_quality_approval.py \
  --review artifacts/gahyeon-ch/g1-review.json \
  --role identity-reviewer \
  --reviewer gahyeon-identity-owner

python3 scripts/transition_gahyeon_quality_review.py \
  --review artifacts/gahyeon-ch/g1-review.json \
  --to approved
```

`draft` 또는 `candidate`는 finding을 최소 하나 기록한 경우에만 `rejected`로 전환할 수
있다. Approved/rejected review는 종결 상태이며 수정하거나 되돌리지 않는다. 수정본은 새
revision review로 시작해 이전 digest 계보를 보존한다.

Finding 역시 review JSON을 직접 편집하지 않고 전용 도구로 기록한다. ID를 생략하면 gate별
단조 증가 ID가 배정된다. Blocking finding은 반드시 실제로 해결해야 하며
`accepted-risk`로 우회할 수 없다. Major 이하의 잔여 타협만 명시적으로 risk acceptance할
수 있다.

```bash
python3 scripts/record_gahyeon_quality_finding.py \
  --review artifacts/gahyeon-ch/g1-review.json \
  add --severity blocking --summary "측면에서 턱선이 canonical profile과 다름"

python3 scripts/record_gahyeon_quality_finding.py \
  --review artifacts/gahyeon-ch/g1-review.json \
  disposition --id G1-001 --status resolved
```

`../zaeze`의 content factory는 관리자용 2D product media와 `mediaAssetId` lifecycle에
맞춰져 있으므로 `.uasset`, sculpt, groom의 source of truth로 재사용하지 않는다. 공유 가능한
부분은 `land` 생성 인프라와 provenance/승인 원칙뿐이다. Gahyeon의 대용량 3D binary는 Git
밖의 content-addressed artifact storage에 두고 Hero manifest가 immutable digest로 참조한다.
실제 storage provider와 무관한 경계는
[`adr/0008-content-addressed-hero-artifacts.md`](adr/0008-content-addressed-hero-artifacts.md)에
고정한다.

`hero-engine` package는 단일 `.uasset`이 아니라 `unreal-content-zip`이다. ZIP에는 캐릭터가
참조하는 mesh, skeleton, physics asset, material, texture, groom과 bulk payload를 포함한
`Content/GahyeonGenerated/**` 전체 dependency subtree가 들어가야 한다. 루트의
`hero-content-manifest.json`은 UE 5.8 버전, 고정 entry asset과 생성 Blueprint class, 모든
파일의 상대 경로·byte 수·SHA-256을 열거한다. 승인 검증은 외부 ZIP digest에 더해 내부
inventory의 누락/미등록 파일, 중복/경로 탈출/symlink/encryption, 비정상 압축률과 각 payload
digest를 확인한다. 따라서 승인된 ZIP을 바꿔치기하거나 의존성이 빠진 단일 asset을 배포할 수
없다. 내부 계약은
[`contracts/gahyeon-unreal-content-package.schema.json`](contracts/gahyeon-unreal-content-package.schema.json)에
고정한다.

내부 manifest v2는 파일 존재만 선언하지 않고 `runtimeContract`도 고정한다. Hero pawn은
`AGahyeonCharacterPawn`, body Anim Blueprint는 `UGahyeonCharacterAnimInstance`를 상속하고,
실제 body Skeletal Mesh와 유효한 `UGahyeonCharacterPresentationProfile`을 가져야 한다.
Python 검증기는 계약 자체의 누락·변경을 거부하고, UE Automation과 GameMode는 설치된 binary
asset을 reflection으로 열어 실제 연결까지 검사한다. 잘못 연결된 Hero는 개발 모드에서
diagnostic shell로 후퇴하며 `bRequireHeroAsset=True`인 승인 빌드에서는 시작을 실패한다.

Unreal에서 `Asset Actions → Migrate` 등으로 완결된 `Content/GahyeonGenerated` subtree를
내보낸 뒤 다음 명령으로 재현 가능한 package와 manifest 입력값을 만든다.

Hero Blueprint는 반드시 `AGahyeonCharacterPawn`을 부모로 사용한다. 그래야 MetaHuman의
face/body/groom 구성은 교체하면서도 VoiceInput, Presentation, WorldAction, Reflex/Behavior
연결은 그대로 유지된다. 런타임 경계는 아래 두 경로로 고정하며 다른 Blueprint를 임의로
entry point로 지정할 수 없다.

```text
/Game/GahyeonGenerated/Characters/Gahyeon.Gahyeon
/Game/GahyeonGenerated/Characters/Gahyeon.Gahyeon_C
```

```bash
python3 scripts/package_gahyeon_unreal_content.py \
  --source /export/Content/GahyeonGenerated \
  --output /artifact/gahyeon-unreal.zip \
  --engine-version 5.6 \
  --entry-asset /Game/GahyeonGenerated/Characters/Gahyeon.Gahyeon \
  --runtime-class /Game/GahyeonGenerated/Characters/Gahyeon.Gahyeon_C
```

패키저는 기존 출력 파일을 임시 파일로 완전히 검증한 뒤에만 원자적으로 교체한다. source의
symlink, 숨김/빈 파일, 잘못된 mount root는 승인 ZIP에 포함시키지 않는다.

G5 승인 manifest가 생긴 뒤에는 다음처럼 Stage에 설치한다. 기존
`Content/GahyeonGenerated`가 다른 digest라면 기본 동작은 중단하며, 의도적인 교체에만
`--replace`를 사용한다. 교체 전 디렉터리는 `Saved/GahyeonHeroInstall/backups/`로 이동되어
복구할 수 있다.

```bash
python3 scripts/install_gahyeon_unreal_content.py \
  /artifact/gahyeon-hero.json \
  --project unreal/GahyeonStage

# 승인된 새 후보로 의도적으로 교체할 때만
python3 scripts/install_gahyeon_unreal_content.py \
  /artifact/gahyeon-hero.json \
  --project unreal/GahyeonStage \
  --replace
```

설치기는 staging에서 payload 전체를 재검증한 뒤 `Content/GahyeonGenerated`를 교체하고
receipt를 남긴다. 동일 digest의 재실행은 no-op이다. 수동 변경, 누락 또는 미등록 파일은
아래 Engine gate의 `--check-only` 단계에서 compile 전에 실패한다.

Unreal Editor build에서 실제 Hero 자산을 포함할 때는 다음처럼 manifest를 명시한다.

```bash
GAHYEON_HERO_MANIFEST=/absolute/path/to/gahyeon-hero.json \
  ./scripts/run_unreal_engine_gate.sh
```

이 환경변수가 있으면 UE 탐색이나 compile 전에 `hero-engine` package가 G5 승인본인지 검사하고,
identity/modeling source manifest, G1~G5 evidence, Unreal ZIP과 내부 payload의 실제 byte 수와
SHA-256을 모두 재검증하고, 설치된 `Content/GahyeonGenerated`가 그 inventory와 정확히
일치하는지도 확인한다. Draft나 파일이 바뀐 승인본은 Editor build에 들어갈 수 없다. 자산이 없는
source-only runtime 검증에서는 환경변수를 생략해 기존 진단 Pawn을 사용한다.

Stage는 위 generated class를 soft-load하고, 해당 자산이 없거나
`AGahyeonCharacterPawn`의 하위 클래스가 아니면 source shell로 안전하게 내려간다. 패키징은
`/Game/GahyeonGenerated` 전체를 always-cook 대상으로 둔다. 승인 배포에서는
`GahyeonHeroRuntimeSettings.bRequireHeroAsset=True`로 설정해 누락된 Hero를 진단 shell로
조용히 숨기지 않고 시작 단계에서 실패시키며, 개발/source-only 기본값만 `False`다.

## 제작 단계와 승인 게이트

### G0 — Identity reference

- LoRA 체크포인트 800~2,800을 고정 시드로 비교한다.
- 정면, 좌우 3/4, 좌우 측면, 위/아래 각도와 서로 다른 표정을 포함한다.
- 전신 얼굴은 원본 생성과 얼굴 2차 보정 결과를 함께 보관한다.
- 특정 재킷, 배경, 귀걸이가 프롬프트 없이 반복되면 정체성 통과로 보지 않는다.

산출물: 승인된 얼굴 12장 이상, 전신 6장 이상, 단일 색상표와 얼굴 특징 설명.

현재 canonical 원본 선택과 G1 전달 규칙은
[`GAHYEON_G1_MODELING_HANDOFF.md`](GAHYEON_G1_MODELING_HANDOFF.md) 및
`artifacts/gahyeon-ch/modeling-input.json`에 고정한다.

### G1 — Model sheet

- neutral 정면/측면/후면 전신은 같은 신체 비율과 대표 의상을 사용한다.
- 얼굴 orthographic reference는 표정과 렌즈 왜곡을 최소화한다.
- 머리카락은 hairline, parting, silhouette, front/side/back clump를 분리한다.
- 눈, 치아, 혀, 손, 신발과 의상 closure를 별도 상세 시트로 만든다.

산출물: 모델러가 임의 해석 없이 작업할 수 있는 승인 model sheet.

### G2 — High-resolution master

- 얼굴/몸 high-poly sculpt와 animation topology를 분리해서 검수한다.
- 눈은 sclera, iris, pupil, cornea, tear line을 분리한다.
- 입 안에는 치아, 잇몸, 혀와 내부 차폐 geometry가 있어야 한다.
- 피부는 albedo에 조명을 굽지 않고 normal/displacement/roughness를 분리한다.
- 얼굴 rig는 눈꺼풀과 안구 접촉, 입술 밀폐, 턱 회전, 볼 부피를 보존한다.

G2 제출은 `artifacts/gahyeon-ch/g2-review-template.json`에서 시작한다. 승인본은
승인된 G1 review에 결합되며 다음을 모두 증명한다.

- 얼굴 sculpt 5시점과 몸 sculpt 앞/옆/뒤
- 얼굴·눈꺼풀·입·몸 topology wireframe
- 각막/홍채/공막/tear line을 확인할 수 있는 eye assembly
- 치아·잇몸·혀·내부 차폐가 보이는 mouth interior
- 조명이 구워지지 않은 albedo와 별도 normal/displacement/roughness 채널
- eyelid contact, lip seal, jaw rotation, cheek volume deformation test
- high-poly master와 animation mesh 원본 artifact
- non-manifold edge 0, 실제 mesh 통계와 open-boundary 정책

```bash
python3 scripts/verify_gahyeon_g2_review.py \
  artifacts/gahyeon-ch/g2-review-template.json

python3 scripts/verify_gahyeon_g2_review.py path/to/g2-review.json --require-approved
```

### G3 — Hair and clothing

- 마스터 헤어는 DCC에서 strand groom으로 제작한다.
- groom은 scalp, brows, lashes, flyaways 등 의미 있는 그룹을 유지한다.
- 런타임 LOD는 strands에서 cards/mesh로 전환할 수 있어야 한다.
- 의상은 몸 관통, 어깨/골반 변형, 앉기 자세와 극단 포즈를 검증한다.

Unreal의 Groom Asset은 imported Alembic groom과 binding을 사용하며 strands,
cards, meshes를 LOD별로 관리할 수 있다. Unreal 자체를 헤어 조형 도구로
간주하지 않는다.

G3 제출은 `artifacts/gahyeon-ch/g3-review-template.json`에서 시작하며 승인된
G2 review checksum에 결합한다. 필수 증거에는 scalp/brows/lashes/flyaways 그룹,
헤어 앞·옆·뒤·정수리·hairline, groom motion, strands와 cards/mesh fallback LOD,
LOD 전환 비교, 의상 앞·옆·뒤, 어깨·골반 변형, 앉기·극단 포즈, body penetration,
closure와 footwear가 포함된다. 승인된 고정 포즈에서 관통은 0건이어야 한다.

```bash
python3 scripts/verify_gahyeon_g3_review.py \
  artifacts/gahyeon-ch/g3-review-template.json

python3 scripts/verify_gahyeon_g3_review.py path/to/g3-review.json --require-approved
```

### G4 — Facial and body performance

- neutral pose에서 모든 blendshape가 0일 때 원본 얼굴이 보존되어야 한다.
- 표정은 FACS 계열 action unit 또는 동등한 의미 단위로 조합 가능해야 한다.
- 한국어 립싱크는 최소 `sil`, `aa`, `ih`, `ou`, `ee`, `oh`, `fv`, `l`,
  `mbp`, `wq` semantic을 제공한다.
- blink, saccade, breathing, head stabilization은 LLM이 아니라 Presentation이
  담당한다.
- Idle/Walk/Sit/Talk의 root motion과 발 미끄러짐을 검수한다.

G4 제출은 `artifacts/gahyeon-ch/g4-review-template.json`에서 시작하며 승인된 G3에
결합한다. neutral control 오차, 표정 조합, 한국어 10-viseme, 정면·측면 립싱크,
blink/saccade/breathing/micro motion, Eye/Head LookAt, Listening/Thinking/Speaking,
Idle/Walk/Sit/Talk과 foot slide를 모두 증거로 남긴다. 초기 고정 합격선은 A/V 최대
절대 오프셋 `80 ms`, 발 미끄러짐 `2 cm`, neutral control 최대 절대값 `0.001`이다.
수정이 필요하면 결과에 맞춰 임의 완화하지 않고 schema version과 근거를 함께 갱신한다.

가장 중요한 hard failure는 Backend가 없을 때 Idle이 멈추거나 Cognition을 기다리는 동안
Reflex가 멈추는 경우다. 이 둘은 그래픽 품질과 관계없이 G4 불합격이다.

```bash
python3 scripts/verify_gahyeon_g4_review.py \
  artifacts/gahyeon-ch/g4-review-template.json

python3 scripts/verify_gahyeon_g4_review.py path/to/g4-review.json --require-approved
```

### G5 — Runtime acceptance

각 renderer package는 같은 고정 장면에서 캡처한다.

- 얼굴 close-up
- 허리 위 대화 카메라
- 전신 이동
- 강한 측광과 역광
- 대표 표정과 립싱크
- 머리카락 운동과 의상 관통

품질 검수와 별개로 frame time, peak VRAM, load time, package size를 기록한다.
1660 Ti는 성능 하한 검수 장비이지 hero source 제작 장비가 아니다.

G5 제출은 `artifacts/gahyeon-ch/g5-review-template.json`에서 시작하며 승인된 G4에
결합한다. Desktop은 Looking Glass가 없어도 완전히 동작해야 하고, Go 연결 해제는
공유 World State를 초기화해서는 안 된다. Go light-field 캡처 자체는 장치가 준비된
후 추가할 수 있지만 두 독립성/복원력 조건은 Desktop 승인에도 필수다.

GTX 1660 Ti 6 GiB, 1920×1080, Unreal 5.6 Development build에서 사용하는 초기
하한은 다음과 같다. 실제 측정 없이 수치를 채우거나 더 빠른 GPU 결과로 대체하지 않는다.

| 항목 | G5 합격선 |
|---|---:|
| frame time p95 / p99 | `≤33.34 / ≤50 ms` |
| peak VRAM | `≤6144 MiB` |
| load time | `≤30 s` |
| microphone reflex p95 | `≤100 ms` |
| STT first partial p95 | `≤600 ms` |
| behavior transition p95 | `≤500 ms` |
| TTS first audio p95 | `≤2000 ms` |
| barge-in cancel p95 | `≤250 ms` |

고정 장면 캡처 외에 Backend-off Idle, Cognition 중 Reflex, World State 재시작 복원,
Desktop 단독 구동, Go disconnect fault injection과 원본 telemetry를 함께 봉인한다.

```bash
python3 scripts/verify_gahyeon_g5_review.py \
  artifacts/gahyeon-ch/g5-review-template.json

python3 scripts/verify_gahyeon_g5_review.py path/to/g5-review.json --require-approved
```

## Renderer 경계

```text
Gahyeon Core semantic events
              │
              ▼
       Presentation Bridge
       ├─ Hero Engine Renderer
       ├─ Three/VRM Renderer
       └─ Looking Glass Renderer
```

Core 이벤트는 `avatar.expression`, `avatar.speech.*`, `character.moved`,
`behavior.activity.changed`처럼 의미만 전달한다. Hero Renderer는 이 의미를
고품질 rig control, groom, material과 animation graph에 매핑한다. VRM은 같은
의미를 더 작은 blendshape와 humanoid rig에 매핑한다.

## 첫 번째 hero 자산 범위

- 얼굴/몸 1개
- 대표 헤어 1개
- 대표 의상 1개
- 신발 1개
- neutral + 표정 세트
- 한국어 viseme 세트
- Idle/Walk/Sit/Talk
- Hero, performance, Looking Glass, VRM 파생본

추가 의상, 헤어, 월드 상호작용은 이 hero asset이 G5를 통과한 뒤 확장한다.

## 공식 기술 근거

- [Epic Groom components and assets](https://dev.epicgames.com/documentation/unreal-engine/groom-components-and-assets-in-unreal-engine?lang=en-US)
- [Epic Groom LOD setup](https://dev.epicgames.com/documentation/unreal-engine/setting-up-level-of-detail-for-grooms-in-unreal-engine?lang=en-US)
- [Epic cards and meshes for grooms](https://dev.epicgames.com/documentation/en-us/unreal-engine/setting-up-cards-and-meshes-for-grooms-in-unreal-engine)
