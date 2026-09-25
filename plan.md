# 구현 계획 — SilentOrchestra 2.0

[요구사항](spec.md)을 구현하는 소스 구조·구현 정책·검증 전략을 관리합니다. 설치와 실행 명령은 [README](README.md), UI 규칙은 [디자인 기준](docs/design.md)을 따릅니다.

## 구현 구조

전체 구성은 [아키텍처](README.md#아키텍처), 의존성 규칙은 [아키텍처 계약](spec.md#아키텍처-계약)을 참고합니다.

### 코드 위치·구현 세부사항

아래 백엔드 경로는 `backend/src/silent_orchestra/` 기준입니다. 프론트엔드·스크립트·배포 진입점은 저장소 루트 기준으로 별도 표기합니다.

- 모듈 내부: `modules/<module>/domain/`, `application/`, `ports.py`, `api.py`, `adapters/`. 공통 계약은 `shared/`에 둡니다.
- HTTP 라우팅·검증: `routers/`, `schemas.py`.
- 영속성: `modules/<module>/adapters/repository.py`, 공통 트랜잭션 구현 `adapters/unit_of_work.py`, 기존 스키마의 ORM 매핑 `adapters/mapping.py`, `database.py`. 순수 엔티티에 외부에서 ORM 매핑을 적용하며 조회 결과는 리스트·엔티티로 반환합니다.
- OS 구현: `modules/agent/adapters/action_executor.py`, `modules/agent/adapters/input_observer.py`.
- 사용자 조회: `agent.ports.UserLookup`에 `identity.api.get_user`를 조립해 Agent가 Identity 엔티티를 직접 조회하지 않습니다.
- 실행·활성 창 조회의 타입 계약은 `agent.ports`에 두고, 영속성 어댑터에는 SQL만 둡니다. `bootstrap.build_agent_dependencies`가 저장소와 실행 포트를 묶은 요청별 애플리케이션 의존성을 만듭니다.
- 의존성 조립·설정: `bootstrap.py`, `main.py`, `config.py`.
- 대시보드 집계는 읽기 어댑터, 데모 초기화의 삭제 건수 집계는 전용 관리 포트가 담당합니다. 이 관리 어댑터는 기존 단일 DB의 공통 매핑을 사용해 삭제 전 종속 테이블을 집계합니다. 기존 Python import 경로는 호환 진입점으로 남기며 데이터 마이그레이션은 필요하지 않습니다.
- 저장소 루트 기준 카메라 진입점: `frontend/app.js`, `backend/scripts/webcam_gesture_client.py`.
- 배포 설정: `SO_DATABASE_URL`로 DB 연결을 지정하며 Vercel 진입점은 루트 `main.py`입니다.
- 컬럼·제약은 [schema.sql](backend/sql/schema.sql), API 스키마는 실행 서버의 `/docs`를 참고합니다.
- `space`·`device`는 메타데이터이며 `activity`가 학습 단위입니다. `speed`·`amplitude`는 함께 NULL이거나 함께 값이 있어야 합니다.

## 실행 설정

기본 설치·실행은 [README](README.md#시작하기)를 따릅니다.

- 선택 입력: [웹캠](README.md#웹캠).
- 실제 앱 제어: [OS 실행](README.md#os-실행).
- 환경 변수: [환경 설정](README.md#환경-설정).

## 검증 전략

자동 검증 명령은 [README 테스트](README.md#테스트)를 따릅니다.

| 대상 | 확인 항목 |
|---|---|
| 아키텍처 | 내부 계층의 프레임워크/어댑터 import 금지, 모듈 간 공개 API 경계, 순수 도메인·가짜 포트 검증 |
| API·SQL | 미정의 영상 필드 거부, `frame_stored=0`, 이미지/BLOB 컬럼 부재, 모션 특징 저장 계약 |
| 학습·실행 | 승인 전 실행 금지, 맥락 분기, 활성 창 차단, 요구사항의 임계값·피드백 규칙 |
| 초기화 | 7개 종속 테이블 삭제 건수, 다른 사용자 보존, 재생성·commit 실패 롤백, 초기화 후 3회 학습·재제안 |
| UI | 3초 갱신·요청 병합, 편집 보존, 오류 표시·복구, 외부 학습 진행률, 실행 결과·피드백, dialog 비차단, Reset 복구 |
| 카메라 | 방향·특징·payload·맥락·키 연결, 실패 시 자원 해제, 정지 제외, 손바닥 재무장, 완전한 원형 궤적 |

## 남은 과제

실제 장비에서 별도로 확인합니다.

- Python·브라우저 카메라의 네 몸짓 인식과 성공·오탐·미탐 기록.
- 브라우저 장치 전환, 중지·페이지 종료 시 MediaStream 해제.
- 네트워크 요청 캡처에서 이미지·원본 프레임 전송 0건 확인. 정책 API·UI 문구로 대체하지 않습니다.
- Windows 실제 키 관측 → 제안 → 승인 → 재인식 E2E.
- OS 실행을 사용할 PC의 권한·활성 창·키 매핑 확인.
