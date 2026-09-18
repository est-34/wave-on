# REST API 명세 — SilentOrchestra 2.0

[기능 명세](../01-func/01-requirements.md) · [테스트 명세](../04-test/01-verification.md)

## HTTP 계약

- 정식 생성 경로는 `POST /observations`, `/teachings`, `/suggestions/{id}/responses`(201 반환, API 접두사 생략)이며, 구 `/observe`, `/teach`, `/suggestions/{id}/respond`는 폐기 예정 호환 경로로 유지한다.
- 사용자 생성 응답의 `Location` 헤더는 생성된 사용자 조회 경로를 가리킨다.

## 진입점과 원본

- 기본 경로: `/api/v1`(`SO_API_PREFIX`), Scalar: `/docs`, OpenAPI: `/openapi.json`, 헬스체크: `/health`(접두사 밖).
- 원본: [라우터](../../backend/src/silent_orchestra/routers) · [스키마](../../backend/src/silent_orchestra/schemas.py) · [앱 진입점](../../backend/src/silent_orchestra/main.py) · [설정](../../backend/src/silent_orchestra/config.py)

## 입력과 응답 경계

- 미정의 요청 필드를 거부하고 이미지 필드를 두지 않는다([개인정보 요구사항](../01-func/01-requirements.md#입력개인정보-fr-01-03-14-17)).
- 성공 응답은 별도 `data` 포장 없는 모델 객체·목록이며, 업무 오류는 `{detail: ...}`, 검증·HTTP 오류는 FastAPI 기본 형식을 따른다.
- 사용자 ID를 입력받는 데모 API로 별도 JWT·세션 인증은 없으며, OS 실행·승인·데모 초기화 제한은 [기능 요구사항](../01-func/01-requirements.md)을 따른다.
