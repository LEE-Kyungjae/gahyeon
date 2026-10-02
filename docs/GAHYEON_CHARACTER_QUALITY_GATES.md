# Gahyeon character quality gates

## LoRA checkpoint scorecard

체크포인트를 전체 평균 하나로 선택하지 않는다. 각 항목을 0~5로 기록하고
hard failure가 하나라도 있으면 3D reference로 승인하지 않는다.

| 항목 | 가중치 | Hard failure |
|---|---:|---|
| 정면 얼굴 정체성 | 20 | 서로 다른 사람으로 인식됨 |
| 3/4·측면 정체성 | 15 | 코선·턱선·눈매가 지속적으로 변경됨 |
| 시드 간 일관성 | 15 | 같은 프롬프트에서 정체성이 반복적으로 바뀜 |
| 표정 자유도 | 10 | 웃음/중립에서 얼굴 구조가 붕괴함 |
| 전신 얼굴 보존 | 10 | 2차 얼굴 보정 후에도 정체성이 복원되지 않음 |
| 의상 자유도 | 10 | 지정하지 않은 대표 의상이 강제됨 |
| 배경·소품 분리 | 5 | 학습 배경이나 귀걸이가 정체성처럼 반복됨 |
| 손·신체 건전성 | 5 | reference로 사용할 수 없는 anatomy 오류 |
| 원본 다양성 보존 | 5 | 특정 학습 이미지 구도를 복제함 |
| 기술 재현성 | 5 | 시드·모델·강도·체크섬을 재현할 수 없음 |

승인 조건:

- 가중 점수 80/100 이상
- 정면과 측면 정체성 각각 4/5 이상
- hard failure 0개
- 최소 3개 시드와 2개 LoRA strength에서 확인

## SDXL LoRA v1 checkpoint decision (2026-08-11)

고정 시드 4개 장면을 LoRA strength `0.8`로 비교한 현재 선택은 다음과 같다.

- 기본 생성 후보: total step `2,000`
- 정면 close-up 보조 후보: total step `2,800`
- 2,800을 범용 기본값으로 사용하지 않는다. 정면은 가장 좋았지만 측면과 전신의
  일반화가 2,000보다 나빠졌다.
- 측면 미소와 캐주얼 전신은 2,000이 가장 나았다.
- 검은 드레스 전신은 모든 체크포인트가 불합격이며, step 증가로 해결되지 않았다.
- 이 결정은 생성·콘셉트 탐색에 사용할 operational selection이다. 아직 위의 G0
  identity reference 승인이나 최종 3D hero 승인을 의미하지 않는다.
- 사용자 검수 결과 원본 29장이 LoRA 생성 샘플보다 명확히 우수했다. 따라서
  `artifacts/gahyeon-ch/identity-reference.json`의 원본만 identity authority이며,
  2,000/2,800 체크포인트에는 `heroReferenceAllowed=false`를 강제한다.
- LoRA 생성물이 원본과 충돌하면 항상 원본의 얼굴 구조·체형·헤어 실루엣을 따른다.

데이터셋, continuation 체크포인트 원장, 40개 개별 비교 결과와 PNG, 통합 summary,
operational selection 및 canonical identity의 auxiliary-model binding은 하나의 검증 계약으로
봉인한다.

```bash
python3 scripts/verify_gahyeon_sdxl_artifacts.py
```

검증기는 24장 train / 5장 validation 분리, 1,200~2,800의 5개 체크포인트 identity,
10개 variant × 4개 고정 scenario, 개별 결과와 로컬 PNG의 SHA-256, summary의 정확한 40-record
일치, 2,000/2,800 selection과 identity manifest의 digest·역할 일치를 모두 확인한다. LoRA를
G0 또는 Hero authority로 올리는 변경은 실패한다. 원격 완료 summary를 복원해야 할 때는
`--sync-summary-from`을 사용할 수 있지만, 그 파일이 40개 개별 결과와 완전히 같을 때만
원자적으로 교체된다.

다음 검증에서는 재학습 전에 2,000을 strength `0.55 / 0.65 / 0.75`, 2,800을
`0.45 / 0.55 / 0.65`로 비교한다. 전신 얼굴은 원본과 FaceDetailer 결과를 함께
평가한다. 이 범위에서도 검은 드레스와 전신 정체성이 회복되지 않으면 v2 데이터셋
보강으로 전환한다.

## 고정 생성 세트

기존 네 장면 외에 최종 후보에는 다음을 추가한다.

- 무표정 정면 close-up
- 웃는 좌우 3/4
- 좌우 측면
- 아래에서 본 각도와 위에서 본 각도
- 실내/실외 상반신
- 흰 티셔츠, 검은 드레스, 대표 재킷
- 앉기, 걷기, 손 흔들기
- 강한 측광과 부드러운 정면광

각 결과는 원본 전신과 얼굴 2차 보정본을 모두 보관한다. FaceDetailer 결과만
좋은 체크포인트와 원본부터 정체성이 좋은 체크포인트를 구분해서 기록한다.

## FaceDetailer 계약

FaceDetailer는 LoRA 품질을 숨기는 합격 도구가 아니라 작은 얼굴 픽셀을 복원하는
Presentation 후처리다.

- 입력 이미지, bbox, detector version, seed, prompt, denoise, LoRA checksum 기록
- 원본 얼굴과 보정 얼굴을 나란히 보관
- bbox 밖의 의상·포즈·배경은 변경하지 않음
- 얼굴 정체성 prompt는 checkpoint 비교와 동일하게 유지
- detector가 얼굴을 찾지 못하면 성공으로 간주하지 않음
- 과도한 denoise로 머리 모양이나 얼굴 방향이 바뀌면 실패

권장 초기 탐색 범위는 denoise `0.25 / 0.35 / 0.45`, LoRA strength
`0.65 / 0.75 / 0.85`다. 수치는 품질 비교 전 확정값이 아니다.

## 3D hero 승인 게이트

- G0: identity reference 승인
- G1: model sheet 비율과 orthographic 일관성 승인
- G2: high-poly, topology, 피부·눈·입 구조 승인
- G3: groom, 대표 의상, LOD 승인
- G4: 표정, 립싱크, body animation 승인
- G5: Desktop/Looking Glass 성능과 영상 품질 승인

어느 단계도 다음 단계의 자동 승인을 의미하지 않는다.

G1~G5의 실제 증거 계약과 실행 명령은
[`AAA_CHARACTER_PIPELINE.md`](AAA_CHARACTER_PIPELINE.md)에 기록한다. Hero G5 승인은
승인된 G1→G2→G3→G4→G5 checksum lineage가 끊기지 않은 경우에만 가능하다.
