# 요구사항 — SilentOrchestra 2.0

제품 범위·요구사항·완료 기준을 관리합니다. 실행 절차는 [README](README.md), 구현·검증 방법은 [구현 계획](plan.md)을 참고합니다.

## 개요

반복 행동과 맥락에서 `user + gesture_key + context_scope → intent`를 학습하는 로컬 우선 Agent입니다. 흐름은 `Observation → Pattern → Suggestion → Memory → Execution → Feedback`입니다.

## 범위

- 활동: `presentation`, `music`
- UI/웹캠 몸짓: `swipe:right`, `swipe:left`, `open_palm:none`, `circle:clockwise`
- 선택 기능: 데모 초기화(FR-16), OpenCV 웹캠(FR-17)
- 제외: 공간 자동 인식, IoT, 얼굴·생체 인식, 영상 업로드, 자유 형식 LLM Intent, 인증·결제·동기화, 연속 문법
- Intent는 [action_catalog.py](backend/src/silent_orchestra/modules/agent/domain/action_catalog.py)의 맥락별 카탈로그로 제한합니다.

## 요구사항

### 입력·개인정보 (FR-01, 03, 14, 17)

- P-1: 원본 프레임을 저장·전송하지 않으며 `frame_stored=0`을 DB CHECK로 강제합니다.
- P-2: API는 미정의 필드를 거부하고 이미지 필드를 제공하지 않습니다.
- P-3: 저장 데이터는 모션·방향·시간·속도·진폭 embedding, 맥락, 행동입니다. 얼굴 특징·궤적·키 문자열은 저장하지 않습니다.
- P-4: 카메라 프레임은 메모리에서만 처리합니다.

### 맥락·학습 (FR-02, 04, 05, 07)

- L-1~2: `/teach`는 관찰과 허용된 사용자 행동을 1:1로 연결합니다. 중복·금지 행동은 400입니다.
- L-3: 같은 사용자·몸짓·활동의 최근 30일, 최대 20건을 `0.5^(경과일/반감기)`로 가중해 승자를 정합니다. count는 원시 건수, target은 최빈값(동률은 최신), embedding은 승자 관찰 평균입니다.
- L-4: `confidence = min(0.99, (0.35 + 0.10×min(승자횟수,5) + 0.22×승자횟수/전체횟수) × recency_factor)`. 기본 반감기는 10일입니다.
- L-5~6: 1·2위 가중합이 상대 오차 1e-6 이내이거나 승자가 바뀌면 기존 기억을 강등합니다. 승자 3회 이상·비동률·비활성일 때만 패턴당 `PENDING` 제안 하나를 만듭니다.
- L-7: `(user_id, gesture_key, context_scope, intent)`는 유일합니다.
- L-8: activity가 없으면 active app 또는 로컬 활성 창으로 판정합니다. 미지원·모호한 앱은 거부하며 명시 activity는 시뮬레이션 override입니다. space·device는 추론하지 않는 스냅샷입니다.
- L-9: Windows 관측 모드는 몸짓 후 5초 안의 같은 앱 첫 허용 키만 연결합니다. 합성·반복·만료 입력은 제외합니다.
- L-10: `open_palm:none`은 승인/정답, `circle:clockwise`는 거절/오답 확인 몸짓이며 학습 후보가 아닙니다.

### 승인·기억 (FR-08, 09)

- M-1: 승인 전 자동 실행하지 않습니다. `ACTIVE + auto_execute=true`만 실행 후보입니다.
- M-2~3: `PENDING`만 1회 응답할 수 있습니다. 수정 Intent는 필수·허용·비중복이어야 합니다.
- M-4: 승인 시 임계 confidence를 보장하고 같은 몸짓·맥락의 다른 활성 기억을 강등합니다.
- M-5: 거절 시 confidence를 0.20 낮추며, 같은 Intent는 새 증거 3건 전까지 재제안하지 않습니다.
- M-6: `/memories`는 임계값 이상의 활성 기억만 반환합니다.

### 추론·실행 (FR-06, 10, 11)

- I-1~3: 같은 사용자·맥락의 활성 기억을 `confidence × (0.20×키 일치 + 0.80×max(코사인 유사도,0))`로 평가합니다. 유사도 0.85 미만, 상위 다른 Intent 점수 차 0.08 미만, 최종 점수 0.60 미만이면 실행하지 않습니다. 6차원 시뮬레이션과 11차원 실측 embedding은 서로 매칭하지 않습니다.
- I-3a: 볼륨·줌 Intent만 `1 + min(int(amplitude),4)`회 실행합니다. 나머지는 1회입니다.
- I-4~7: 모든 실행은 실제 반복 횟수와 `SIMULATED`·`SUCCEEDED`·`FAILED` 결과를 기록합니다. 기본은 `DRY_RUN`; OS 실행은 명시적으로 켜며 활성 창 불일치·미매핑·전송 실패를 `FAILED`로 기록합니다.

### 피드백 (FR-12, 13)

- F-1: 실행당 피드백은 한 건입니다.
- F-2: confidence 변화는 `CORRECT +0.03`, `WRONG_ACTION -0.15`, `IGNORE -0.05`이며 0~0.99로 제한합니다. `ACCIDENTAL_GESTURE`는 confidence를 바꾸지 않고 같은 맥락에서 유사도 0.95 이상인 모션을 5분간 억제합니다.
- F-3~4: 잘못된 행동은 허용된 Intent로 교정할 수 있습니다. confidence가 임계값 아래면 기억을 강등합니다.

### 데모·UI (FR-15, 16)

- D-1~3: `/demo/reset`은 demo-user만 단일 트랜잭션으로 초기화하고 Context·Observation·Action·Pattern·Suggestion·Execution·Feedback 삭제 건수를 반환합니다. 다른 사용자는 보존하고 실패는 롤백하며 데모 모드가 아니면 403입니다.
- U-1: 카메라는 사용자가 시작하고 중지·페이지 종료 시 해제합니다.
- U-2~3: UI는 학습된 기억과 confidence를 우선 표시하고 실행 실패 사유를 구분합니다.
- U-4: UI는 불투명한 밝은 표면을 사용하고 포커스·오류·선택 상태를 명확히 구분합니다. 곡률·그림자·타이포그래피 등 표현 규칙은 [디자인 기준](docs/design.md)을 따릅니다.

## 아키텍처 계약

모듈 구성과 실행 흐름은 [아키텍처](README.md#아키텍처)를 기준으로 합니다.

- 단일 프로세스·단일 배포·단일 DB의 모듈러 모놀리스로 구성하며 `identity`(사용자), `agent`(관찰·학습·승인·실행·피드백), `demo`(데모 관리)를 업무 경계로 둡니다. 각 모듈은 공개 API, application, domain(필요 시), 출력 ports, adapters를 소유합니다.
- 도메인과 유스케이스는 FastAPI, SQLAlchemy, OS 구현에 의존하지 않습니다. 저장소·트랜잭션·실행·활성 창 조회는 포트로 주입합니다.
- Agent의 사용자 존재 확인은 Identity 공개 API를 연결한 조회 포트를 사용하며 다른 모듈의 엔티티를 저장소로 직접 조회하지 않습니다.
- HTTP 어댑터는 입력 검증과 응답 변환을 담당하고 SQL은 영속성 어댑터에 둡니다. 모듈 간 호출은 공개 API를 통합니다.
- 기존 API·DB 테이블·제약·학습 결과·실행 안전장치를 보존하고 의존성 경계를 자동 검증합니다.

## 완료 기준

아래 항목은 수용 기준이며 검증 완료 기록이 아닙니다. 검증 범위는 [구현 계획](plan.md#검증-전략), 실행 명령은 [README](README.md#테스트)를 따릅니다.

- 개인정보, 승인 전 실행 금지, 활성 창 차단, 맥락 분기, 초기화·재학습 계약 통과
- 백엔드·프런트·SQL 검증 통과
