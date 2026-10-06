# 온톨로지 기반 RAG v1

## 구현 범위

구조화된 개체·관계 입력을 원문 청크에 연결하고, 질문에서 개체 이름/별칭을 찾아 관계를 최대 3단계 탐색한다. 기존 키워드·벡터 검색과 관계 검색을 결합한 결과를 캐릭터 대화의 지식 프롬프트에 공급한다. 일반 `KnowledgeBaseService`의 저장·검색 동작은 수정하지 않았다.

이 구현은 관계와 근거를 활용하는 RAG다. OWL/RDF 논리 추론기, 자유 문장에서 관계를 자동으로 추출하는 모델, 모든 기존 자료의 자동 재색인은 포함하지 않는다. 원문 인용의 존재와 관계 타입은 기계 검증하지만, 원문의 부정·조건·시점까지 관계 주장이 올바르게 해석했는지는 작성/검토 단계에서 확인해야 한다. 관계 경로를 새로운 사실로 단정하지 않도록 프롬프트에 표시한다.

## 활성화

- Flyway `V42__Add_evidence_backed_ontology.sql`이 적용된 DB가 필요하다. 이번 작업에서는 로컬 H2 테스트에 V41/V42를 적용했으며 운영 DB를 변경하지 않았다.
- `GAHYEON_ONTOLOGY_ENABLED=true`로 관계 검색 및 관리 API를 활성화한다. 기본값은 false다.
- 관리 API는 기존 `gahyeon.admin` 활성화와 32자 이상의 관리 토큰도 필요하다. `X-Gahyeon-Admin-Token` 헤더로 인증한다.
- 기능을 끄면 기존 지식 검색 결과를 그대로 사용하며 온톨로지 테이블을 조회하지 않는다.
- 캐릭터와 사용자 범위가 있는 기존 대화 경로에서 지식 검색에 적용한다. 다른 대화 경로를 새로 전역 검색에 연결하지 않았다.

## 데이터 모델

개체 유형: PERSON, ORGANIZATION, PROJECT, TASK, DOCUMENT, TOPIC.

허용 관계와 방향:

| 관계 | 시작 유형 | 도착 유형 |
| --- | --- | --- |
| MEMBER_OF | PERSON | ORGANIZATION |
| RESPONSIBLE_FOR | PERSON | PROJECT 또는 TASK |
| PART_OF | TASK | PROJECT |
| PART_OF | PROJECT | ORGANIZATION |
| DEPENDS_ON | PROJECT / TASK | 같은 유형 |
| USES | PROJECT | TOPIC |
| ABOUT | DOCUMENT | PROJECT 또는 TOPIC |

스키마 버전은 1이다. 각 주장은 두 개체의 key/type/label/aliases, 관계 유형, evidenceQuote를 포함한다. 이름이 같다고 개체를 합치지 않는다. 검토된 type+key가 같은 개체만 같은 서비스 안에서 연결한다. key는 수집 파이프라인에서 안정적으로 부여해야 한다. 한 서비스에 같은 key를 재사용하면 같은 개체라는 의도적인 선언으로 취급한다.

`knowledge_ontology_claims`의 각 행은 원문 청크를 참조한다. 별도 전역 개체 사전에 비공개 이름을 복제하지 않는다. 개인정보 소유권은 원문 source/document/chunk에서 읽으므로 기존 소유권 이전에도 따라간다.

## 저장과 재색인

`POST /api/admin/gahyeon/ontology/ingest`

요청은 `document`(기존 KnowledgeBaseService 입력)와 `ontology`(schemaVersion과 claims)로 구성한다. 원문·청크 저장과 관계 색인을 같은 트랜잭션에서 처리한다. 문서 중복 판정 후 접근 범위가 다르면 거부한다. 관계 검증 실패 시 새 문서도 롤백한다.

`POST /api/admin/gahyeon/ontology/documents/{documentId}`

기존 문서에 `serviceId`, `ownerSubjectId`, `ontology`를 지정해 관계를 붙이거나 교체한다. 문서의 정확한 소유자·서비스·활성 상태를 검사하고 문서 행을 잠근다. 모든 새 주장을 검증한 다음 해당 문서의 기존 주장만 교체한다. 같은 입력을 재색인해도 관계가 중복되지 않는다.

인용은 8~600자이며 원문 청크 하나 안에 정확히 존재해야 한다. 두 개체의 이름 또는 별칭도 인용에 있어야 한다. 여러 청크에 걸쳐 인용이 잘리면 거부하므로 적절한 문장 단위 근거를 제공한다. 별칭은 검토된 매핑이며 모델이 임의로 추가하는 권한이 아니다.

## 검색과 근거

- `GET /api/admin/gahyeon/ontology/schema`: 스키마 버전과 허용 관계 목록.
- `POST /api/admin/gahyeon/ontology/graph/search`: serviceId, subjectId, query, limit, maxHops를 받아 원문·출처·개별 주장으로 구성된 경로 반환.
- `POST /api/admin/gahyeon/ontology/search`: 기존 SearchRequest(serviceId, subjectId, query, limit)를 받아 통합 검색 결과와 graphEnabled/graphTruncated 반환.

관계 탐색 전에 서비스와 원문 접근권한을 SQL에서 필터링한다. PRIVATE는 source/document/chunk 모두 요청자의 정확한 소유자여야 한다. PUBLIC/SERVICE도 지정된 서비스 밖으로 넘어가지 않는다. 비공개 이름이나 별칭을 검색 시작점으로 먼저 사용한 뒤 결과에서 숨기는 방식이 아니다.

검색은 관계의 양쪽에서 탐색할 수 있지만 반환하는 주장의 방향은 원래 방향을 유지한다. 순환 경로는 방문 집합과 깊이 제한으로 제어한다. 기본 RAG는 2단계, 직접 그래프 검색은 최대 3단계다. 한 번에 허용된 주장 최대 2,000개, 시작 개체 최대 8개, 결과 최대 20개를 처리한다. 한도 때문에 제외한 자료는 truncated로 알린다. 이는 소규모 첫 구현이며 큰 자료 집합의 모든 관계를 찾는다고 보장하지 않는다. 다음 확장은 DB에서 시작 개체를 먼저 조회하고 인접 관계를 단계별로 가져오는 인덱스 검색이다.

기존 검색과 그래프 검색은 reciprocal rank fusion으로 합친다. 같은 청크를 중복 반환하지 않고 관계가 포함된 근거를 우선 보존한다. 점수는 순위 결합 값이며 사실의 확률이나 신뢰도가 아니다. 대화 프롬프트에는 경로마다 원문의 source ID와 chunk ID, 인용을 넣는다. 자료의 지시는 실행 지시로 취급하지 않는다. 검색 범위가 잘렸으면 관계가 없다고 단정하지 않도록 제한 상태도 전달한다.

## 재현용 입력

`ontology-examples/project.json`, `owner.json`, `query.json`은 개인정보가 없는 합성 예제다. 테스트용 사용자 식별자를 실제 권한 있는 식별자로 교체한 뒤 사용할 수 있다.

1. project.json을 ingest에 보내면 ‘출시 검증 PART_OF 오로라’가 저장된다.
2. owner.json을 ingest에 보내면 ‘민지 RESPONSIBLE_FOR 출시 검증’이 저장된다.
3. query.json의 ‘새벽 담당자는 누구야’를 search에 보낸다. ‘새벽’은 ‘오로라’의 별칭이다.
4. 결과는 오로라와 출시 검증의 관계, 민지와 출시 검증의 관계를 서로 다른 원문 출처와 함께 포함한다. 이것만으로 민지가 프로젝트 전체의 책임자라는 새로운 사실을 만들어서는 안 된다.

## 삭제와 검증

원문이 비활성화되거나 soft delete되면 관계 검색에서 즉시 제외한다. 청크가 물리적으로 삭제되면 FK ON DELETE CASCADE로 인용·별칭 등 파생 관계도 삭제된다. 원문 검색의 기존 삭제 API를 그대로 사용한다.

테스트는 실제 Spring 트랜잭션·JDBC·마이그레이션을 사용한다. 원문 저장 → 관계 색인 → 별칭/다단계 검색 → 대화 프롬프트까지 검증하며, 실제 LLM 답변 품질과 운영 PostgreSQL 성능은 검증하지 않았다.

검증 명령:

```sh
./gradlew test --tests 'com.gahyeonbot.application.knowledge.*' --tests 'com.gahyeonbot.services.ai.agent.*' --tests 'com.gahyeonbot.adapters.admin.OntologyAdminControllerTest' --tests 'com.gahyeonbot.database.KnowledgeMemoryMigrationTest'
bash scripts/run_ai_quality_gate.sh
```

## 운영 관찰 계약

기능 추가 작업이며 확인된 운영 사고는 없다. 로컬 합성 자료로 검증했다. 배포 시 소스 커밋·이미지 digest·배포 revision·설정 식별자를 별도로 기록해야 한다.

기대 불변 조건은 사용자/서비스 격리, 활성 원문만 검색, 근거 없는 주장 거부, 실패 시 저장 롤백, 삭제 후 파생 정보 미노출이다. 배포 후 최소 30분과 관련 요청 30건 이상을 관찰한다. 개인정보를 포함하지 않는 조회 건수·지연·truncated 비율·오류율을 관찰 신호로 사용하고, 다른 사용자 자료 노출이나 삭제된 자료 재등장은 즉시 기능 중단 검토 사유로 삼는다. 실제 되돌림은 명시적 권한이 있을 때 수행한다. 이번에는 배포하지 않았으며 운영 요청 수를 측정하지 않았다.
