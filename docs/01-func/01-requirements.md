# 요구사항 — SilentOrchestra 2.0

[README](../../README.md) · [기술 구조](../03-tech/01-architecture.md) · [REST API](../03-tech/api.md) · [테스트 명세](../04-test/01-verification.md)

## 개요

반복 행동과 맥락에서 `user + gesture_key + context_scope → intent`를 학습하는 로컬 우선 Agent(`Observation → Pattern → Suggestion → Memory → Execution → Feedback`).

## 범위

- 활동: `presentation`, `music` / 몸짓: `swipe:right`, `swipe:left`, `open_palm:none`, `circle:clockwise`
- 선택: 데모 초기화(FR-16), OpenCV 웹캠(FR-17) / Intent: [action_catalog.py](../../backend/src/silent_orchestra/modules/agent/domain/action_catalog.py) 카탈로그로 제한
- 제외: 공간 자동 인식, IoT, 얼굴·생체 인식, 영상 업로드, 자유 형식 LLM Intent, 인증·결제·동기화, 연속 문법

## 요구사항

### 입력·개인정보 (FR-01, 03, 14, 17)

- P-1~2: 원본 프레임 비저장·비전송(`frame_stored=0` DB CHECK 강제), API 미정의 필드 거부 및 이미지 필드 미제공.
- P-3~4: 카메라 프레임은 메모리에서만 처리하고 모션·방향·시간·속도·진폭 embedding, 맥락, 행동만 저장(얼굴 특징·궤적·키 문자열 제외).

### 맥락·학습 (FR-02, 04, 05, 07)

- L-1~2: `/teachings`는 관찰과 허용 행동을 1:1 연결(중복·금지 행동은 400).
- L-3~4: 같은 사용자·몸짓·활동의 최근 30일·최대 20건을 `0.5^(경과일/반감기)`(기본 반감기 10일)로 가중해 승자 산출. `count`=원시 건수, `target`=최빈값(동률 시 최신), `embedding`=승자 평균, `confidence = min(0.99, (0.35 + 0.10×min(승자횟수,5) + 0.22×승자횟수/전체횟수) × recency_factor)`.
- L-5~7: 1·2위 가중합 상대 오차 1e-6 이내 또는 승자 변경 시 기존 기억 강등. 승자 3회 이상·비동률·비활성일 때만 패턴당 `PENDING` 제안 1건 생성. `(user_id, gesture_key, context_scope, intent)` 유일.
- L-8~10: `activity` 미지정 시 active app/로컬 활성 창으로 판정(미지원·모호 앱 거부, 명시 값은 시뮬레이션 override, `space`·`device`는 스냅샷). Windows 관측은 몸짓 후 5초 내 같은 앱 첫 허용 키만 연결(합성·반복·만료 제외). `open_palm:none`(승인/정답)·`circle:clockwise`(거절/오답)는 확인 전용이며 학습 후보 제외.

### 승인·기억 (FR-08, 09)

- M-1~3: 승인 전 자동 실행 금지(`ACTIVE + auto_execute=true`만 실행 후보). `PENDING`만 1회 응답 가능하며 수정 Intent는 필수·허용·비중복.
- M-4~6: 승인 시 임계 confidence 보장 및 동일 몸짓·맥락의 타 활성 기억 강등. 거절 시 confidence `-0.20` 및 새 증거 3건 전까지 재제안 보류. `/memories`는 임계값 이상 활성 기억만 반환.

### 추론·실행 (FR-06, 10, 11)

- I-1~3a: 활성 기억을 `confidence × (0.20×키 일치 + 0.80×max(코사인 유사도,0))`로 평가. 유사도 `<0.85`, 타 Intent와 점수 차 `<0.08`, 최종 점수 `<0.60`, 또는 차원 불일치(6차원 시뮬레이션 vs 11차원 실측)면 미실행. 볼륨·줌만 `1 + min(int(amplitude),4)`회, 나머지는 1회 실행.
- I-4~7: 반복 횟수와 `SIMULATED`·`SUCCEEDED`·`FAILED`를 기록. 기본 `DRY_RUN`; OS 실행 시 활성 창 불일치·미매핑·전송 실패는 `FAILED`로 기록.

### 피드백 (FR-12, 13)

- F-1~4: 실행당 피드백 1건. confidence 변화는 `CORRECT +0.03`, `WRONG_ACTION -0.15`, `IGNORE -0.05`(0~0.99 제한, 임계값 미만 시 강등)이며 잘못된 행동은 허용 Intent로 교정 가능. `ACCIDENTAL_GESTURE`는 confidence 유지 후 동일 맥락의 유사도 `≥0.95` 모션을 5분간 억제.

### 데모·UI (FR-15, 16)

- D-1~3: `/demo/reset`은 데모 모드에서만(비데모 403) `demo-user`의 7개 종속 테이블(Context·Observation·Action·Pattern·Suggestion·Execution·Feedback)을 단일 트랜잭션으로 삭제하고 건수를 반환(타 사용자 보존, 실패 시 롤백).
- U-1~4: 카메라는 사용자 시작·중지/종료 시 해제. UI([디자인 기준](../02-uxui/01-design.md))는 불투명 밝은 표면에서 학습 기억·confidence·실패 사유와 포커스·오류·선택 상태를 구분.
- U-5~6: 플로팅 필 메뉴로 작업·맥락·기억 단일 페이지를 전환(상태 유지, 직접 링크·히스토리 지원). 작업 화면은 활동 선택 → 몸짓 → 행동 연결 → 반복 → 제안 승인 순으로 진행하며 학습/확인 몸짓 구분, 요청 중 입력 잠금, 시뮬레이션 안내·닫기 수단을 제공.
- U-7~8: 모바일(320px·가로 화면 포함) 본문 14px+, 보조 12px+, select 16px+ 유지. 현재 단계 카드만 노출하고 카메라는 접힌 보조 입력으로 제공하며, 빈 맥락·기억에는 학습 링크를, 제안 응답 후에는 다음 행동을 안내.

## 완료 기준

수용 기준이며 검증 완료를 뜻하지 않는다([검증 범위](../04-test/01-verification.md#검증-전략) · [실행 명령](../../README.md#테스트)).

- 개인정보·승인 전 실행 금지·활성 창 차단·맥락 분기·초기화·재학습 계약 및 백엔드·프런트·SQL 검증 통과

[분류 기준](../../README.md#문서-분류-기준) · [기술 명세](../03-tech/README.md) · [테스트 명세](../04-test/01-verification.md)
