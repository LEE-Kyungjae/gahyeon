# Branch Protection Rules Setup Guide

GitHub Flow를 안전하게 운영하기 위한 브랜치 보호 규칙 설정 가이드입니다.

## 설정 방법

1. GitHub 저장소 페이지 접속
2. **Settings** → **Branches** 메뉴로 이동
3. **Add branch protection rule** 클릭

## main 브랜치 보호 규칙 (필수)

### Rule name
```
main
```

### 설정 항목

#### ✅ Require a pull request before merging
- PR을 통해서만 main에 머지 가능
- **Require approvals**: 1 (최소 1명의 승인 필요)
- ☑️ Dismiss stale pull request approvals when new commits are pushed

#### ✅ Require status checks to pass before merging
- CI 테스트 통과 필수
- **Status checks that are required**:
  - `Build & Test`

#### ✅ Require conversation resolution before merging
- PR 코멘트 해결 필수

#### ✅ Do not allow bypassing the above settings
- 관리자도 규칙 준수

#### ❌ Allow force pushes (체크 해제)
- Force push 금지

#### ❌ Allow deletions (체크 해제)
- 브랜치 삭제 금지

## develop 브랜치 보호 규칙 (권장)

### Rule name
```
develop
```

### 설정 항목

#### ✅ Require a pull request before merging (선택)
- PR을 통한 머지 권장
- **Require approvals**: 0 or 1

#### ✅ Require status checks to pass before merging
- CI 테스트 통과 필수
- **Status checks that are required**:
  - `Build & Test`

#### ❌ Allow force pushes (체크 해제)
- Force push 금지

## 빠른 설정 링크

GitHub 저장소에서 다음 URL로 직접 이동:
```
https://github.com/LEE-Kyungjae/gahyeonbot/settings/branch_protection_rules/new
```

## 설정 확인

설정 완료 후 다음 명령으로 확인:
```bash
gh api repos/LEE-Kyungjae/gahyeonbot/branches/main/protection
```

## 테스트

1. develop 브랜치에서 작업
2. develop에 푸시 → CI 테스트 실행 확인
3. develop → main PR 생성
4. CI 테스트 통과 확인
5. PR 승인 및 머지
6. 자동 배포 실행 확인

## 주의사항

- main 브랜치 보호 규칙은 **반드시** 설정
- develop 브랜치 보호 규칙은 팀 규모에 따라 선택
- 보호 규칙 설정 후 직접 푸시 불가능 (PR 필수)
