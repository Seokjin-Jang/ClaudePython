# Use Case — 전자식 차일드락 제어 SW

| 항목 | 내용 |
|---|---|
| 문서 ID | SWR-UC-001 |
| 관련 문서 | SWR-SPEC-001 SW 요구사항 사양서 |

## 액터

| 액터 | 설명 |
|---|---|
| 운전자 | 물리 버튼, AVN, 음성, 모바일 앱으로 잠금·해제 명령 |
| 차량 | 차속, 기어, 충돌, 접근위험, 화재·과온·성인 탑승, ISOFIX, IGN, 센서 고장 신호 제공 |
| 표시 장치 / 시험자 | Web 시뮬레이터로 상태 조회, 시험 입력 주입 |

## UC-01 운전자가 정차 중 한쪽 차일드락을 해제한다
- **관련 SWR**: 001, 002, 004, 009
- **사전 조건**: IGN ON, 차속 0 km/h, 양쪽 LOCK, 강제 조건 없음
- **주 흐름**: 운전자가 AVN에서 left/unlock 선택 → SW가 왼쪽만 RELEASE → 상태 조회에 `DRIVER_COMMAND` 표시
- **대안 흐름**: 왼쪽 ISOFIX 연결 → 해제 거절, `DRIVER_REQUEST_REJECTED`

## UC-02 주행을 시작하면 자동으로 잠긴다
- **관련 SWR**: 003, 019
- **사전 조건**: IGN ON, 양쪽 RELEASE
- **주 흐름**: 차속이 3.0 km/h에 도달 → 같은 주기에 양쪽 LOCK, `AUTO_LOCK_SPEED`

## UC-03 하차 시 후측방 차량이 접근한다
- **관련 SWR**: 005, 006, 009, 019
- **사전 조건**: 정차, 오른쪽 접근위험 TRUE
- **주 흐름**: 운전자가 right/unlock → 거절(LOCK 유지), `APPROACH_RISK` 기록 → 10 s 안에 다시 right/unlock → `APPROACH_OVERRIDE_REQUESTED` 기록, 위험 TRUE 동안 LOCK 유지(가정 A-03)
- **종료**: 접근위험 FALSE 후 운전자 unlock → RELEASE

## UC-04 충돌이 확정된다
- **관련 SWR**: 007, 008, 019, 020
- **주 흐름**: crash_status PENDING → 출력 변화 없음, `CRASH_PENDING` 기록 → CONFIRMED → 300 ms 이내 양쪽 RELEASE(접근위험·ISOFIX·주행 중이어도) → 이후 계속 RELEASE
- **종료**: IGN OFF 후 다시 ON하면 래치 해제

## UC-05 화재·과온·성인 탑승으로 강제 해제된다
- **관련 SWR**: 017, 019
- **주 흐름**: 세 입력 중 하나 TRUE → 양쪽 RELEASE, 입력별 이유 코드

## UC-06 ISOFIX 카시트를 연결한다
- **관련 SWR**: 018, 009
- **주 흐름**: 왼쪽 ISOFIX TRUE → 왼쪽만 LOCK, 오른쪽 유지

## UC-07 입력이 끊기거나 잘못 들어온다
- **관련 SWR**: 013, 019
- **주 흐름**: 스냅샷이 0.2 s 넘게 갱신되지 않음 → DEGRADED, `INPUT_STALE`, 출력 유지 → 정상 입력 복귀 시 NORMAL
- **대안 흐름**: 범위 밖 차속(300.1) → 평가 전 거절, `INPUT_INVALID`

## UC-08 센서 고장이 발생한다
- **관련 SWR**: 021, 019
- **주 흐름**: sensor_fault TRUE → 직전 출력 유지, FAULT, `SENSOR_FAULT` → FALSE 복귀 시 NORMAL

## UC-09 시동을 끈다
- **관련 SWR**: 020
- **주 흐름**: ignition_on FALSE → 양쪽 RELEASE, OFF, `IGNITION_OFF`

## UC-10 시험자가 상태와 이력을 조회한다
- **관련 SWR**: 010, 011, 012, 014, 015, 016
- **주 흐름**: Web 시뮬레이터에서 입력 주입 → 상태 조회 → 최근 이벤트 100건 확인 → 같은 입력 시퀀스 재생 시 같은 결과
