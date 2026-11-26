# SW 요구사항 사양서 — 전자식 차일드락 제어 SW

| 항목 | 내용 |
|---|---|
| 문서 ID | SWR-SPEC-001 |
| 베이스라인 | BL-SWR-1.0 (초안) |
| 상위 입력 | OEM-SWR-001 Rev 1.0 (BL-OEM-1.0) |
| A-SPICE | SWE.1 SW 요구사항 분석 |
| 상태 | 초안 — 사용자 검토 전, OEM 확인 필요 사항 미해결 |

## 1. 목적과 범위

OEM-SWR-001의 OEM 요구사항(SR 4건, FR 7건, NFR 2건)과 외부 인터페이스(IF-001~009)를 공급자 SW 요구사항(SWR)으로 분해한다. 범위는 PC/SIL 참조 구현과 Web 시뮬레이터이며, 도어 래치·구동기 HW, CAN/LIN 드라이버, HIL, 실차, HARA는 제외한다.

## 2. 용어와 공통 정의

| 용어 | 정의 |
|---|---|
| 평가 주기 | SW가 최신 입력 스냅샷 1개를 평가해 출력을 결정하는 1회 실행. 주기 T = 50 ms (가정 A-01) |
| 입력 스냅샷 | 한 평가 주기에 들어오는 차량 입력 묶음(IF-001~003, IF-007~009)과 선택적 운전자 명령(IF-004). 시각은 `timestamp_s` 하나로 표현 |
| 출력 | `lock_left`, `lock_right` ∈ {LOCK, RELEASE} (IF-005) |
| 직전 확정 출력 | 바로 앞 평가 주기에서 결정된 출력. 최초 기동 시 RELEASE/RELEASE |
| 상태 `state` | OFF, NORMAL, DEGRADED, FAULT 중 하나 |
| 이유 코드 `reason_code` | 해당 주기 출력을 결정한 규칙. 6절 목록 |
| 지연(stale) | 평가 시각 − `timestamp_s` > 0.200 s |

**ASIL 표기**: OEM SR(ASIL B 입력)에서 파생된 SWR은 ASIL B, 나머지는 QM. ASIL B 요구는 QM 요구에 의해 결과가 바뀌지 않아야 한다(SWR-019).

## 3. 가정 (OEM 확인 필요)

| ID | 가정 | 관련 질의 |
|---|---|---|
| A-01 | 평가 주기 T = 50 ms | Q-03 |
| A-02 | 출력 우선순위는 SWR-019 표를 따른다 | Q-01 |
| A-03 | 접근위험 중 재입력(override)은 이유 코드만 생성하고 출력은 LOCK 유지 | Q-02 |
| A-04 | crash_status = PENDING은 출력을 바꾸지 않고 이유 코드만 기록 | Q-04 |
| A-05 | DEGRADED·FAULT 상태에서는 직전 확정 출력을 유지하고, 원인이 사라진 첫 주기에 NORMAL로 복귀 | Q-07 |
| A-06 | `gear`는 형식·범위만 검증하고 제어 판단에 쓰지 않는다 | Q-08 |
| A-07 | 운전자 명령은 지원 경로 4개(physical_button, avn, voice, mobile_app)를 모두 처리 | Q-05 |

## 4. 기능 요구사항

### SWR-001 운전자 잠금·해제 명령 처리 (QM)
- **출처**: OEM-FR-001
- **요구**: SW는 운전자 명령의 `side`(left/right/all)와 `action`(lock/unlock)에 따라 선택된 쪽 출력에만 LOCK 또는 RELEASE를 적용해야 한다. 선택되지 않은 쪽 출력은 직전 확정 출력을 유지한다.
- **수용기준**: 차속 0.0 km/h, 다른 강제 조건이 없는 정상 입력에서 side 3종 × action 2종 = 6조합 각각에 대해, 같은 평가 주기 출력이 선택된 쪽에만 반영되고 이유 코드가 `DRIVER_COMMAND`이다.
- **검증**: 단위 시험, PC/SIL

### SWR-002 운전자 명령 경로 처리 (QM)
- **출처**: OEM-FR-001, OEM-IF-004
- **요구**: SW는 `source`가 physical_button, avn, voice, mobile_app인 명령을 같은 규칙으로 처리해야 한다. 그 밖의 값이나 누락은 명령을 거절하고 이유 코드 `DRIVER_REQUEST_INVALID`를 기록한다(차량 입력 평가는 계속).
- **수용기준**: 네 경로 각각의 lock/unlock 명령이 같은 결과를 내고, 미등록 source·누락 필드 명령은 출력에 반영되지 않는다.
- **검증**: 단위 시험, PC/SIL/Web

### SWR-003 주행 시 자동 잠금 (QM)
- **출처**: OEM-FR-002
- **요구**: 유효한 `vehicle_speed_kph`가 3.0 km/h 이상이면 SW는 같은 평가 주기에 양쪽 출력을 LOCK으로 해야 한다.
- **수용기준**: 차속 2.9 km/h에서는 자동 잠금이 없고, 3.0 km/h인 첫 평가 주기에 양쪽 LOCK, 이유 코드 `AUTO_LOCK_SPEED`.
- **검증**: 단위 시험, PC/SIL

### SWR-004 운전자 해제 허용 조건 (QM)
- **출처**: OEM-FR-001, OEM-FR-002
- **요구**: 운전자 unlock 명령은 해당 쪽에 대해 (a) 차속 < 3.0 km/h, (b) 해당 쪽 접근위험 FALSE, (c) 해당 쪽 ISOFIX FALSE일 때만 적용해야 한다. 조건을 만족하지 않으면 출력을 바꾸지 않고 이유 코드 `DRIVER_REQUEST_REJECTED`를 기록한다.
- **수용기준**: (a)~(c) 각각만 위반한 3개 상황에서 unlock이 적용되지 않고 거절 이유 코드가 기록된다. 모두 만족하면 적용된다.
- **검증**: 단위 시험, PC/SIL

### SWR-005 후측방 접근위험 시 잠금과 해제 억제 (ASIL B)
- **출처**: OEM-SR-002
- **요구**: `rear_left_approach_risk` 또는 `rear_right_approach_risk`가 TRUE인 쪽은 같은 평가 주기에 LOCK이어야 하며, 위험이 TRUE인 동안 그 쪽에 대한 운전자 unlock 명령을 적용하지 않아야 한다. 더 높은 순위의 해제 조건(IGN OFF, 충돌 확정, 화재·과온·성인 탑승)은 SWR-019에 따라 해제한다. 이유 코드 `APPROACH_RISK`를 기록한다.
- **수용기준**: 접근위험 TRUE가 된 첫 주기에 해당 출력 LOCK, 이후 unlock 명령에도 LOCK 유지, 이벤트 기록에 원인이 남는다.
- **검증**: 단위 시험, PC/SIL

### SWR-006 접근위험 억제 후 재입력 처리 (ASIL B)
- **출처**: OEM-SR-002, OEM-FR-003
- **요구**: SWR-005로 unlock이 억제된 뒤 같은 쪽 unlock 명령이 억제 시각부터 10.0 s 이하에 다시 들어오면, SW는 이를 명시적 override 요청으로 기록해야 한다(이유 코드 `APPROACH_OVERRIDE_REQUESTED`). 접근위험이 TRUE인 동안 출력은 LOCK을 유지한다(가정 A-03).
- **수용기준**: 억제 후 10.0 s 재입력은 override 이유 코드 생성, 10.05 s(다음 주기) 재입력은 일반 거절. 두 경우 모두 위험 TRUE 동안 출력 LOCK.
- **검증**: 단위 시험, PC/SIL/Web

### SWR-007 충돌 확정 시 긴급 해제 (ASIL B)
- **출처**: OEM-SR-001
- **요구**: 유효한 `crash_status`가 CONFIRMED이면 SW는 다른 모든 해제 억제·잠금 조건보다 우선해 양쪽 출력을 RELEASE로 해야 하며, 이후 주기에도 유지해야 한다(IGN OFF 제외). 이유 코드 `CRASH_CONFIRMED`.
- **수용기준**: CONFIRMED 입력 후 300 ms 이내(첫 평가 주기) 양쪽 RELEASE. 접근위험·ISOFIX·차속 조건이 함께 있어도 RELEASE. 이후 crash_status가 NONE으로 바뀌어도 IGN 재시작 전까지 RELEASE 유지.
- **검증**: 단위 시험, PC/SIL

### SWR-008 충돌 PENDING 처리 (ASIL B)
- **출처**: OEM-SR-001
- **요구**: `crash_status`가 PENDING이면 SW는 출력을 PENDING 때문에 바꾸지 않고(가정 A-04), 이유 코드 `CRASH_PENDING`을 이벤트로 기록해야 한다.
- **수용기준**: PENDING 입력 주기의 출력이 PENDING이 없는 같은 입력의 출력과 같고, 이벤트에 `CRASH_PENDING`이 남는다.
- **검증**: 단위 시험

### SWR-009 좌우 독립 제어 (ASIL B)
- **출처**: OEM-SR-002, OEM-FR-006
- **요구**: 한쪽에만 적용되는 조건(접근위험, ISOFIX, side=left/right 명령)은 반대쪽 출력에 영향을 주지 않아야 한다.
- **수용기준**: 왼쪽 조건만 TRUE인 상황에서 오른쪽 출력이 직전 확정 출력과 같다. 오른쪽도 대칭으로 확인.
- **검증**: 단위 시험, PC/SIL

### SWR-013 입력 유효성과 지연 감시 (ASIL B)
- **출처**: OEM-SR-003, OEM-IF-001~003, IF-007~009
- **요구**: SW는 평가 전에 모든 필수 차량 입력의 존재, 형식, 범위를 검사해야 한다. 하나라도 오류이면 해당 스냅샷을 평가하지 않고 `input_validity = INVALID`, 이유 코드 `INPUT_INVALID`, 상태 DEGRADED로 한다. 스냅샷이 지연(평가 시각 − timestamp_s > 0.200 s)되면 100 ms 이내에 상태 DEGRADED, 이유 코드 `INPUT_STALE`로 한다. DEGRADED에서는 직전 확정 출력을 유지한다(가정 A-05).
- **입력 범위**: vehicle_speed_kph 0.0~300.0 (실수), gear ∈ {P, N, D, R}, crash_status ∈ {NONE, PENDING, CONFIRMED}, 불리언 입력 8종은 bool 형식만 허용.
- **수용기준**: 지연 0.200 s는 정상, 0.250 s(다음 주기)에서 DEGRADED. 범위 밖(−0.1, 300.1), 형식 오류(문자열 차속), 누락 필드, 미정의 enum 각각 평가 전에 거절.
- **검증**: 단위 시험, PC/SIL

### SWR-014 상태 조회 응답 (QM)
- **출처**: OEM-FR-004, OEM-IF-006
- **요구**: SW는 상태 조회 요청에 `lock_left`, `lock_right`, `state`, `input_validity`, `reason_code`, `priority_reason`을 포함한 JSON 응답을 제공해야 한다. `priority_reason`은 `reason_code`와 같은 값으로 매핑한다. 직렬화에 실패하면 HTTP 500을 반환한다.
- **수용기준**: `GET /api/status` 응답에 6개 필드가 모두 있고 값이 마지막 평가 결과와 같다. 직렬화 실패 주입 시 500.
- **검증**: 통합 시험, Web

### SWR-015 Web 시뮬레이터 표시와 입력 (QM)
- **출처**: OEM-FR-004
- **요구**: Web 시뮬레이터는 입력 스냅샷·운전자 명령을 입력하고, SWR-014의 상태와 최근 이벤트를 표시해야 한다.
- **수용기준**: 브라우저에서 입력을 보내면 다음 응답의 상태 표시가 SWR-014 응답과 일치한다.
- **검증**: 통합 시험, Web

### SWR-017 화재·과온·성인 탑승 시 강제 해제 (QM)
- **출처**: OEM-FR-005, OEM-IF-007
- **요구**: 유효한 `fire_detected`, `overtemperature_detected`, `adult_present` 중 하나라도 TRUE이면 다음 평가 주기까지 양쪽 출력을 RELEASE로 하고, 입력별 이유 코드(`FIRE`, `OVERTEMPERATURE`, `ADULT_PRESENT`)를 기록해야 한다.
- **수용기준**: 세 입력을 각각 단독 주입했을 때 다음 평가 주기에 양쪽 RELEASE, 해당 이유 코드.
- **검증**: 단위 시험, PC/SIL/Web

### SWR-018 ISOFIX 연결 시 강제 잠금 (QM)
- **출처**: OEM-FR-006, OEM-IF-008
- **요구**: `isofix_left`/`isofix_right`가 TRUE인 쪽은 다음 평가 주기까지 LOCK이어야 하며, 반대쪽은 직전 확정 출력을 유지해야 한다. 이유 코드 `ISOFIX`.
- **수용기준**: 한쪽 ISOFIX만 TRUE일 때 그쪽만 LOCK, 반대쪽 유지.
- **검증**: 단위 시험, PC/SIL/Web

### SWR-019 출력 결정 우선순위 (ASIL B)
- **출처**: OEM-SR-001("다른 명령보다 우선"), OEM-SR-002, OEM-SR-004, OEM-FR-002, FR-005, FR-006, FR-007 — 상충 해소용으로 공급자가 추가(OEM 9절 추적표의 결번 SWR-019 사용)
- **요구**: 같은 평가 주기에 여러 규칙이 해당되면 아래 순서에서 가장 위의 규칙으로 각 쪽 출력을 결정해야 한다(가정 A-02).

  | 순위 | 조건 | 출력 | 이유 코드 |
  |---|---|---|---|
  | 1 | ignition_on = FALSE | 양쪽 RELEASE, state OFF | `IGNITION_OFF` |
  | 2 | crash_status = CONFIRMED (래치) | 양쪽 RELEASE | `CRASH_CONFIRMED` |
  | 3 | sensor_fault = TRUE | 직전 확정 출력 유지, state FAULT | `SENSOR_FAULT` |
  | 4 | 입력 무효 / 지연 | 직전 확정 출력 유지, state DEGRADED | `INPUT_INVALID` / `INPUT_STALE` |
  | 5 | 화재 / 과온 / 성인 탑승 | 양쪽 RELEASE | `FIRE` / `OVERTEMPERATURE` / `ADULT_PRESENT` |
  | 6 | 해당 쪽 접근위험 | 해당 쪽 LOCK | `APPROACH_RISK` |
  | 7 | 해당 쪽 ISOFIX | 해당 쪽 LOCK | `ISOFIX` |
  | 8 | 차속 ≥ 3.0 km/h | 양쪽 LOCK | `AUTO_LOCK_SPEED` |
  | 9 | 운전자 명령 | 선택 쪽 적용 | `DRIVER_COMMAND` |
  | 10 | 해당 없음 | 직전 확정 출력 유지 | `NO_CHANGE` |

- **수용기준**: 인접한 두 순위 조건을 동시에 준 9개 조합 각각에서 위 순위의 결과가 나온다.
- **검증**: 단위 시험, PC/SIL

### SWR-020 IGN OFF 시 초기 해제 (QM)
- **출처**: OEM-FR-007, OEM-IF-009
- **요구**: `ignition_on`이 FALSE인 첫 평가 주기에 양쪽 출력을 RELEASE, 상태 OFF, 이유 코드 `IGNITION_OFF`로 하고, 충돌 래치(SWR-007)를 해제해야 한다.
- **수용기준**: ignition_on=FALSE 첫 주기에 양쪽 RELEASE, state OFF. 다시 TRUE가 되면 NORMAL에서 시작.
- **검증**: 단위 시험, PC/SIL/Web

### SWR-021 센서 고장 시 출력 유지 (ASIL B)
- **출처**: OEM-SR-004, OEM-IF-009
- **요구**: `sensor_fault`가 TRUE이면 SW는 SWR-019 순위 4~10의 조건(입력 무효, 강제 해제·잠금, 자동 잠금, 운전자 명령)을 적용하지 않고 직전 확정 출력을 유지하며, 상태 FAULT와 경고 코드 `SENSOR_FAULT`를 제공해야 한다. sensor_fault가 FALSE가 된 첫 주기에 NORMAL로 복귀한다(가정 A-05).
- **수용기준**: sensor_fault=TRUE 첫 평가 주기에 좌우 출력이 직전 값과 같고 state FAULT. 같은 주기의 unlock 명령·ISOFIX·차속 조건이 반영되지 않는다.
- **검증**: 단위 시험, PC/SIL

## 5. 비기능 요구사항

### SWR-010 결정 이벤트 기록 (QM)
- **출처**: OEM-NFR-002
- **요구**: SW는 평가 주기마다 결정 이벤트 1건을 일련번호 `event_id`(1부터 증가)와 함께 메모리에 기록하고, 최근 100건만 보존해야 한다.
- **수용기준**: 101건 입력 후 조회 결과가 event_id 2~101의 100건이며 순서가 유지된다.
- **검증**: 단위 시험, 통합 시험

### SWR-011 이벤트 허용 필드 (QM)
- **출처**: OEM-NFR-002
- **요구**: 이벤트는 `event_id`, `timestamp_s`, `lock_left`, `lock_right`, `state`, `reason_code`, `input_validity` 필드만 가져야 한다. 영상·음성 데이터, 개인 식별자, 운전자 명령 source 외 식별 정보는 저장하지 않는다.
- **수용기준**: 모든 이벤트의 키 집합이 위 7개와 정확히 같다.
- **검증**: 단위 시험

### SWR-012 이벤트 휘발성 (QM)
- **출처**: OEM-NFR-002
- **요구**: 이벤트 저장소는 파일·DB 등 영구 저장소에 쓰지 않아야 하며, 프로세스 재시작 후 비어 있어야 한다.
- **수용기준**: 이벤트 기록 후 프로세스를 다시 시작하면 조회 결과가 0건이고, 작업 폴더에 새 파일이 생기지 않는다.
- **검증**: 통합 시험

### SWR-016 결정론적 동작 (QM)
- **출처**: OEM-NFR-001
- **요구**: 같은 초기 상태와 같은 입력 순서(시각 포함)에 대해 SW는 항상 같은 출력·상태·이벤트를 생성해야 한다. 시스템 시계, 난수, 해시 순서 등 외부 비결정 요소에 의존하지 않는다.
- **수용기준**: 고정 시계로 같은 입력 벡터를 1,000회 재생했을 때 공개 결과(출력, 상태, 이벤트)의 SHA-256 해시가 모두 같다.
- **검증**: PC/SIL

## 6. 이유 코드 목록

`IGNITION_OFF`, `CRASH_CONFIRMED`, `CRASH_PENDING`, `SENSOR_FAULT`, `INPUT_INVALID`, `INPUT_STALE`, `FIRE`, `OVERTEMPERATURE`, `ADULT_PRESENT`, `APPROACH_RISK`, `APPROACH_OVERRIDE_REQUESTED`, `ISOFIX`, `AUTO_LOCK_SPEED`, `DRIVER_COMMAND`, `DRIVER_REQUEST_REJECTED`, `DRIVER_REQUEST_INVALID`, `NO_CHANGE`

## 7. 인터페이스 요구 요약

| IF | 방향 | 필드 | 형식·범위 | 관련 SWR |
|---|---|---|---|---|
| OEM-IF-001 | Vehicle→SW | vehicle_speed_kph, gear, source_timestamp_s | 0.0~300.0; P/N/D/R; s | 003, 004, 013 |
| OEM-IF-002 | Vehicle→SW | crash_status | NONE/PENDING/CONFIRMED | 007, 008, 013 |
| OEM-IF-003 | Vehicle→SW | rear_left/right_approach_risk | bool | 005, 006, 009, 013 |
| OEM-IF-004 | Driver→SW | side, action, source | left/right/all; lock/unlock; 4종 | 001, 002, 004 |
| OEM-IF-005 | SW→Actuator model | lock_left/right | LOCK/RELEASE | 001~009, 017~021 |
| OEM-IF-006 | SW→Display | state, priority_reason, reason_code, input_validity | enum/string | 014, 015 |
| OEM-IF-007 | Vehicle→SW | fire_detected, overtemperature_detected, adult_present | bool | 013, 017 |
| OEM-IF-008 | Vehicle→SW | isofix_left/right | bool | 013, 018 |
| OEM-IF-009 | Vehicle→SW | ignition_on, sensor_fault | bool | 013, 020, 021 |
