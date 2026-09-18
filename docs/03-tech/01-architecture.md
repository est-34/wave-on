# 기술 구조 및 설계 — SilentOrchestra 2.0

[요구사항](../01-func/01-requirements.md) · [디자인 기준](../02-uxui/01-design.md) · [테스트 명세](../04-test/01-verification.md) · [README](../../README.md)

## 아키텍처와 경계

흐름 그림은 [아키텍처](../../README.md#아키텍처)를 기준으로 한다.

- 단일 프로세스·단일 DB 모듈러 모놀리스로 `identity`(사용자), `agent`(관찰·학습·승인·실행·피드백), `demo`(데모 초기화) 모듈이 각자 공개 API·application·domain·ports·adapters를 소유한다.
- 도메인·유스케이스는 FastAPI·SQLAlchemy·OS 구현에 의존하지 않으며 저장소·트랜잭션·실행·활성 창·사용자 조회(`agent.ports.UserLookup` ← `identity.api.get_user`)를 포트로 주입받는다.
- HTTP 어댑터는 입력 검증·응답 변환만, 영속성 어댑터는 SQL만 담당하며 모듈 간 호출은 공개 API를 통한다.

## 소스 구조

### 저장소 구성

- `backend/`: 패키지(`src/silent_orchestra/`), 테스트(`tests/`), 스크립트(`scripts/`), SQL(`sql/`).
- `frontend/`: `index.html`, `js/`, `css/`, `assets/`, `tests/` (`/static`으로 제공).
- `docs/`: 명세(`01-func/`~`04-test/`)와 자산(`assets/`). `data/`: 로컬 DB(Git 제외). 루트: 로컬 실행(`run_demo.py`)·Vercel 배포 진입점(`main.py`, `requirements.txt`).

### 코드 위치·구현 세부사항

백엔드 경로는 `backend/src/silent_orchestra/` 기준이다.

- 모듈·공통: `modules/<module>/{domain,application,adapters}/`, `ports.py`, `api.py`, 공통 `shared/`, 라우팅 `routers/`, `schemas.py`.
- 영속성·조립: `modules/<module>/adapters/repository.py`, `adapters/{unit_of_work,mapping}.py`, `database.py`, `bootstrap.py`(`build_agent_dependencies`), `main.py`, `config.py`. 대시보드 집계는 읽기 어댑터, 데모 초기화 집계는 전용 관리 포트가 담당한다.
- OS·카메라: `modules/agent/adapters/{action_executor,input_observer}.py`, `backend/scripts/webcam_gesture_client.py`, `frontend/js/app.js`.
- 프론트엔드: `frontend/js/navigation.js`(hash·`hidden` 단일 페이지 전환, DOM·세션 유지, [플로팅 필 탭 바](../02-uxui/01-design.md#플로팅-필-탭-바)), `frontend/js/app.js`(활동 동기화·반복 입력·입력 잠금), `frontend/css/workbench.css`(반응형·터치 영역).
- 데이터 제약([schema.sql](../../backend/sql/schema.sql)): `activity`가 학습 단위(`space`·`device`는 메타데이터)이며 `speed`·`amplitude`는 동시 NULL 또는 동시 값이어야 한다.
- 실행·환경 설정: [시작하기](../../README.md#시작하기) · [환경 설정](../../README.md#환경-설정) · [웹캠](../../README.md#웹캠) · [OS 실행](../../README.md#os-실행)

## 남은 작업과 리스크

| 항목 | 대기 이유 | 재개 조건·작업 |
| --- | --- | --- |
| 카메라·개인정보 실측 | 실제 장비 인식률·자원 해제·네트워크 비전송 확인 필요 | 장비 준비 후 [실제 장비 검증](../04-test/01-verification.md#실제-장비-검증) 수행 |
| Windows 관측·OS 실행 | 대상 PC 권한·활성 창·키 매핑 E2E 확인 필요 | 대상 PC에서 [실제 장비 검증](../04-test/01-verification.md#실제-장비-검증) 수행 |

자동 검사 통과만으로 위 항목을 완료 처리하지 않는다.
