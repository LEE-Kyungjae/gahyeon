# Contributing to Gahyeonbot

## Git Workflow (GitHub Flow)

우리는 GitHub Flow 브랜치 전략을 사용합니다.

### 브랜치 구조

- `main` - 프로덕션 브랜치 (항상 배포 가능한 상태)
- `develop` - 개발 브랜치 (다음 릴리스 준비)
- `feature/*` - 기능 개발 브랜치
- `fix/*` - 버그 수정 브랜치
- `hotfix/*` - 긴급 수정 브랜치

### 개발 워크플로우

#### 1. 새로운 기능 개발

```bash
# develop 브랜치에서 시작
git checkout develop
git pull origin develop

# 기능 브랜치 생성
git checkout -b feature/your-feature-name

# 작업 후 커밋
git add .
git commit -m "feat: add new feature"

# develop에 PR 생성
git push origin feature/your-feature-name
```

#### 2. 버그 수정

```bash
# develop 브랜치에서 시작
git checkout develop
git pull origin develop

# 수정 브랜치 생성
git checkout -b fix/bug-description

# 작업 후 커밋
git add .
git commit -m "fix: resolve bug description"

# develop에 PR 생성
git push origin fix/bug-description
```

#### 3. 긴급 수정 (Hotfix)

```bash
# main 브랜치에서 바로 시작
git checkout main
git pull origin main

# hotfix 브랜치 생성
git checkout -b hotfix/critical-issue

# 수정 후 커밋
git add .
git commit -m "fix: critical issue description"

# main과 develop 모두에 PR 생성
git push origin hotfix/critical-issue
```

#### 4. 프로덕션 배포

```bash
# develop에서 main으로 PR 생성
# PR 승인 및 머지 → 자동 배포 실행
```

### Commit Message Convention

Semantic Versioning을 위해 다음 컨벤션을 따릅니다:

- `feat:` - 새로운 기능 (MINOR 버전 증가)
- `fix:` - 버그 수정 (PATCH 버전 증가)
- `docs:` - 문서 변경
- `style:` - 코드 포맷팅
- `refactor:` - 리팩토링
- `test:` - 테스트 추가/수정
- `chore:` - 빌드/설정 변경

### CI/CD Pipeline

#### develop 브랜치
- ✅ 빌드 및 테스트 실행
- ❌ Docker 이미지 빌드 안 함
- ❌ 프로덕션 배포 안 함

#### main 브랜치
- ✅ 빌드 및 테스트 실행
- ✅ 버전 태그 자동 생성
- ✅ Docker 이미지 빌드 및 푸시
- ✅ Blue-Green 프로덕션 배포

#### Pull Request
- ✅ 모든 PR에서 테스트 실행
- ✅ 테스트 통과 필수

### Branch Protection Rules

#### main 브랜치
- PR을 통해서만 머지 가능
- 최소 1명의 리뷰 승인 필요 (권장)
- CI 테스트 통과 필수
- Force push 금지

#### develop 브랜치
- PR을 통해서만 머지 가능 (권장)
- CI 테스트 통과 필수

### 배포 프로세스

1. **개발 작업**: feature 브랜치 → develop PR
2. **테스트**: develop 브랜치에서 통합 테스트
3. **릴리스**: develop → main PR (릴리스 준비 완료 시)
4. **자동 배포**: main 머지 → CI/CD 자동 실행 → 프로덕션 배포
5. **모니터링**: 배포 후 애플리케이션 상태 확인

### 버전 관리

- Semantic Versioning (MAJOR.MINOR.PATCH)
- main 브랜치 푸시 시 자동으로 버전 태그 생성
- `feat:` 커밋 → MINOR 버전 증가 (예: 0.3.0 → 0.4.0)
- `fix:` 커밋 → PATCH 버전 증가 (예: 0.3.0 → 0.3.1)

### Questions?

워크플로우나 기여 방법에 대한 질문이 있으면 이슈를 생성해주세요.
