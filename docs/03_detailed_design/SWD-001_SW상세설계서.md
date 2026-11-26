# SW 상세 설계서 — 전자식 차일드락 제어 SW

| 항목 | 내용 |
|---|---|
| 문서 ID | SWD-001 |
| 베이스라인 | BL-SWD-1.0 (초안) |
| 상위 입력 | SWA-001 (BL-SWA-1.0 초안), SWR-SPEC-001 |
| A-SPICE | SWE.3 SW 상세 설계 |
| 상태 | 초안 — 사용자 검토 전 |

## 1. 공통 규칙

| ID | 규칙 | 이유 |
|---|---|---|
| D-01 | 시간 비교는 마이크로초 정수로 한다: `round((a - b) * 1_000_000)` | 부동소수 오차로 경계(0.200 s, 10.0 s)가 틀어지는 결함 방지 |
| D-02 | 모든 데이터 클래스는 `@dataclass(frozen=True)`, 열거형은 `Enum` | SWA P-04 |
| D-03 | 불리언 입력은 `type(x) is bool`로만 인정한다 (`1`, `"true"` 거절) | Python에서 `bool`이 `int`의 하위형이라 `isinstance`로는 1이 통과함 |
| D-04 | 수치 입력은 `int` 또는 `float`(단 `bool` 제외)이고 유한값이어야 한다 | NaN·inf가 범위 비교를 통과하는 결함 방지 |
| D-05 | 판단 함수는 예외를 던지지 않고 결과 객체로 실패를 표현한다 | 평가 주기 중단 방지 |
| D-06 | 상수는 모듈 상단 `CAPS_WITH_UNDER`로 정의하고 요구 ID를 주석으로 단다 | 추적성, 변경 지점 단일화 |

**상수**

| 상수 | 값 | 모듈 | SWR |
|---|---|---|---|
| `AUTO_LOCK_SPEED_KPH` | 3.0 | arbiter | 003, 004 |
| `STALE_LIMIT_US` | 200_000 | input_monitor | 013 |
| `OVERRIDE_WINDOW_US` | 10_000_000 | approach_guard | 006 |
| `SPEED_MIN_KPH`, `SPEED_MAX_KPH` | 0.0, 300.0 | validator | 013 |
| `EVENT_CAPACITY` | 100 | event_log | 010 |
| `CYCLE_S` | 0.05 | web.server (tick) | A-01 |

## 2. `types` (ASIL B)

**열거형** (값은 OEM IF 문자열 그대로)

| 이름 | 값 |
|---|---|
| `Lock` | `LOCK`, `RELEASE` |
| `State` | `OFF`, `NORMAL`, `DEGRADED`, `FAULT` |
| `InputValidity` | `VALID`, `INVALID`, `STALE` |
| `ReasonCode` | SWR-SPEC-001 6절의 17개 |
| `Side` | `left`, `right`, `all` |
| `Action` | `lock`, `unlock` |
| `Source` | `physical_button`, `avn`, `voice`, `mobile_app` |
| `CrashStatus` | `NONE`, `PENDING`, `CONFIRMED` |
| `Gear` | `P`, `N`, `D`, `R` |

**데이터 클래스**

| 이름 | 필드 |
|---|---|
| `VehicleSnapshot` | `timestamp_s: float`, `vehicle_speed_kph: float`, `gear: Gear`, `crash_status: CrashStatus`, `rear_left_approach_risk`, `rear_right_approach_risk`, `fire_detected`, `overtemperature_detected`, `adult_present`, `isofix_left`, `isofix_right`, `ignition_on`, `sensor_fault` (불리언 9개) |
| `DriverRequest` | `side: Side`, `action: Action`, `source: Source` |
| `InvalidRequest` | `reason: str` |
| `Rejection` | `field: str`, `reason: str` |
| `Outputs` | `left: Lock`, `right: Lock` / 메서드 `get(side) -> Lock` |
| `Decision` | `outputs: Outputs`, `state: State`, `reason_code: ReasonCode`, `input_validity: InputValidity`, `notices: tuple[ReasonCode, ...]` |

`notices`는 보조 이유 코드(SWR-010)를 발생 순서대로 담는다.

## 3. `validator` (ASIL B) — SWR-013

```
validate_vehicle(raw: object) -> VehicleSnapshot | Rejection
```

1. `raw`가 `dict`가 아니면 `Rejection("<root>", "not an object")`.
2. 필드 명세 표 `_FIELDS`(필드명, 검사 함수)를 순서대로 돈다. 첫 실패에서 `Rejection(필드명, 사유)`를 반환한다.
   - 누락 → `"missing"`
   - 불리언 9개 → D-03
   - `vehicle_speed_kph` → D-04, `SPEED_MIN_KPH ≤ v ≤ SPEED_MAX_KPH`
   - `timestamp_s` → D-04, `v ≥ 0`
   - `gear`, `crash_status` → 문자열이고 열거형 값 중 하나
3. 모두 통과하면 `VehicleSnapshot` 생성.
4. 명세에 없는 추가 필드는 무시한다 (OEM 계약에 정의 없음 — 상위 시스템 확장 허용).

**복잡도**: 표 순회 + 검사 함수 분리로 함수당 복잡도 4 이하.

**단위 시험 설계**: 필드별 누락, 경계값(−0.1 / 0.0 / 300.0 / 300.1), 형식 오류(`"10"`, `True`를 차속으로, `1`을 불리언으로), NaN·inf, 미정의 enum(`"X"`, 소문자 `"confirmed"`), 정상 입력.

## 4. `input_monitor` (ASIL B) — SWR-013

```
is_stale(snapshot_ts: float, now_s: float) -> bool
    return round((now_s - snapshot_ts) * 1_000_000) > STALE_LIMIT_US
```

- 미래 시각(`now_s < snapshot_ts`)은 지연이 아니다(음수). 시계 역행 감지는 범위 밖.
- **시험**: 0.200 s → False, 0.200001 s → True, 0.250 s → True, 음수 → False, 부동소수 경계 `now=1.3, ts=1.1`.

## 5. `driver_request` (QM) — SWR-002

```
parse_command(raw: object) -> DriverRequest | InvalidRequest
```

- `raw`가 `dict`이고 `side`, `action`, `source`가 각각 해당 열거형 값(정확히 일치하는 문자열)이면 `DriverRequest`.
- 아니면 `InvalidRequest(사유)`. 추가 필드는 무시.

## 6. `approach_guard` (ASIL B) — SWR-005, 006

```
GuardState(frozen): first_suppressed_us: dict 대신 (left: int | None, right: int | None)
GuardResult(frozen): rejected: frozenset[Side], override: frozenset[Side]

apply(state, snapshot, request) -> tuple[GuardState, GuardResult]
```

시각은 `snapshot.timestamp_s`를 마이크로초로 바꿔 쓴다(OEM IF-004: 요청 시각 = 스냅샷 시각).

쪽(left, right)마다:

1. 해당 쪽 접근위험이 FALSE → 그 쪽 기록을 `None`으로 지우고 끝.
2. 요청이 그 쪽에 대한 `unlock`이 아니면(`side`가 그 쪽 또는 `all`이 아니거나 `action`이 `lock`) → 기록 유지, 끝.
3. 기록이 있고 `now_us − 기록 ≤ OVERRIDE_WINDOW_US` → `override`에 추가, 기록을 `None`으로 지움.
4. 그 밖(기록 없음 또는 10 s 초과) → `rejected`에 추가, 기록 = `now_us`.

**시험**: 첫 억제, 10.000 s 재입력 → override, 10.05 s 재입력 → 거절(새 억제 시작), 위험 해제 후 기록 초기화, `side=all`이 양쪽에 적용, 반대쪽 무영향(SWR-009), `lock` 요청은 무시.

## 7. `arbiter` (ASIL B) — SWR-001, 003, 004, 007, 008, 009, 017~021

### 7.1 입력

```
Context(frozen):
    snapshot: VehicleSnapshot | None   # VALID일 때만 값, 아니면 None
    validity: InputValidity
    previous: Outputs
    crash_latched: bool
    request: DriverRequest | InvalidRequest | None
    guard: GuardResult
```

### 7.2 규칙 표

```
Rule(frozen): rank: int, code: ReasonCode, scope: "both" | "side",
              applies: Callable[[Context, Side], bool],
              output: Callable[[Context, Side], Lock | None]   # None = 직전 유지
RULES: tuple[Rule, ...]  # rank 순 정렬
```

| rank | code | scope | applies | output |
|---|---|---|---|---|
| 1 | IGNITION_OFF | both | snapshot 있음 and not ignition_on | RELEASE |
| 2 | CRASH_CONFIRMED | both | crash_latched | RELEASE |
| 3 | SENSOR_FAULT | both | snapshot 있음 and sensor_fault | None |
| 4 | INPUT_INVALID / INPUT_STALE | both | validity ≠ VALID | None |
| 5 | FIRE / OVERTEMPERATURE / ADULT_PRESENT | both | 해당 불리언 TRUE (코드는 이 순서로 첫 TRUE) | RELEASE |
| 6 | APPROACH_RISK | side | 해당 쪽 접근위험 | LOCK |
| 7 | ISOFIX | side | 해당 쪽 isofix | LOCK |
| 8 | AUTO_LOCK_SPEED | both | speed ≥ 3.0 | LOCK |
| 9 | DRIVER_COMMAND | side | 유효 요청이 그 쪽 대상, 그리고 (lock이거나 SWR-004 해제 조건 충족) | 요청 action에 따라 LOCK/RELEASE |
| 10 | NO_CHANGE | both | 항상 | None |

- rank 4는 snapshot이 없으므로 rank 1·3을 평가할 수 없다. rank 2(래치)는 snapshot 없이도 적용된다.
- rank 4의 코드는 validity가 INVALID면 `INPUT_INVALID`, STALE면 `INPUT_STALE`.
- rank 5는 세 입력을 하나의 규칙으로 묶어 코드만 다르게 낸다(복잡도 분산).

### 7.3 판정

```
decide(ctx) -> Decision
    per_side = {side: _first_rule(ctx, side) for side in (LEFT, RIGHT)}
    outputs  = 각 쪽: rule.output(ctx, side) 또는 None이면 ctx.previous.get(side)
    primary  = rank가 가장 작은 규칙 (양쪽 중)
    state    = _state_for(primary.rank, ctx)     # 1→OFF, 3→FAULT, 4→DEGRADED, 그 외 NORMAL
    notices  = _notices(ctx, per_side)
    return Decision(outputs, state, primary.code, ctx.validity, notices)
```

**보조 코드 `_notices`** (발생 순):
1. snapshot의 crash_status가 PENDING → `CRASH_PENDING` (SWR-008)
2. `guard.override`가 비어 있지 않음 → `APPROACH_OVERRIDE_REQUESTED` (SWR-006)
3. 유효 unlock 요청이 있었는데 그 쪽이 rank 9로 적용되지 않음, 또는 `guard.rejected` → `DRIVER_REQUEST_REJECTED` (SWR-004, 005)
4. `request`가 `InvalidRequest` → `DRIVER_REQUEST_INVALID` (SWR-002)

SWR-021 확인: sensor_fault면 rank 3이 양쪽에 먼저 적용되므로 rank 4~10(명령·강제 조건)은 출력에 영향 없음.

**복잡도**: `decide` 3, `_first_rule` 3, 각 `applies`/`output` 1~4. 모두 10 이하.

**시험**: 규칙별 단독 적용, 인접 순위 쌍 9개(SWR-019 수용기준), 좌우 독립, 보조 코드 4종, 3.0 / 2.9 km/h 경계.

## 8. `controller` (ASIL B) — SWR-007, 013, 016, 020, 021

```
class ChildLockController:
    __init__(record: Callable[[Decision, float], None] | None = None)
    evaluate(now_s: float, vehicle_raw: object = None,
             request: DriverRequest | InvalidRequest | None = None) -> Decision
    last_decision: Decision | None   (읽기 전용 속성)
```

**내부 상태** (외부 공개 안 함): `_snapshot: VehicleSnapshot | None`, `_outputs: Outputs` (초기 RELEASE/RELEASE), `_crash_latched: bool`, `_guard: GuardState`, `_last: Decision | None`.

**`evaluate` 순서**

1. `vehicle_raw`가 있으면 `validate_vehicle`. 성공 시 `_snapshot` 갱신, 실패 시 이번 주기 `rejected = True` (`_snapshot`은 유지).
2. validity: rejected → INVALID; `_snapshot` 없음 → STALE; `is_stale(_snapshot.timestamp_s, now_s)` → STALE; 그 외 VALID.
3. VALID면:
   - `ignition_on`이 FALSE → `_crash_latched = False`, `_guard` 초기화 (SWR-020)
   - `crash_status`가 CONFIRMED → `_crash_latched = True` (SWR-007)
   - `_guard, guard_result = approach_guard.apply(_guard, snapshot, request)`
   
   아니면 `guard_result = 빈 결과`.
4. `decision = arbiter.decide(Context(...))`.
5. `_outputs = decision.outputs`, `_last = decision`.
6. `record`가 있으면 `record(decision, now_s)` — 판정·상태 갱신 뒤에 호출 (SWA 5절).
7. `decision` 반환.

**함수 분해**: `_validity(now_s, rejected)`, `_update_latches(snapshot)` 로 나눠 `evaluate`의 복잡도 5 이하, 순수 코드 30줄 이하.

**시험**: 초기 상태, 래치 설정·유지·IGN OFF 해제, 무효 입력 시 직전 스냅샷 유지, 지연, 기록 콜백 호출 순서(판정 후), 콜백 없음.

## 9. `event_log` (QM) — SWR-010, 011, 012

```
class EventLog:
    __init__(capacity: int = EVENT_CAPACITY)
    record(decision: Decision, now_s: float) -> None
    items() -> list[dict]     # 오래된 순, 복사본
```

- 내부 저장소 `collections.deque(maxlen=capacity)`. 파일·DB 사용 안 함 (SWR-012).
- `record`는 결정 이벤트 1건 + `decision.notices` 코드마다 1건을 추가한다. 각 이벤트는 정확히 7개 키: `event_id`, `timestamp_s`(= now_s), `lock_left`, `lock_right`, `state`, `reason_code`, `input_validity` (값은 열거형의 문자열). 보조 이벤트는 같은 출력·상태에 `reason_code`만 보조 코드.
- `event_id`는 1부터 증가하며 저장소가 넘쳐도 계속 증가한다.

**시험**: 101건 후 2~101, 키 집합 정확히 7개, 보조 이벤트 순서, 복사본 반환(외부 수정이 내부에 영향 없음).

## 10. `status` (QM) — SWR-014

```
to_status(decision: Decision | None) -> dict
```

- 6개 키: `lock_left`, `lock_right`, `state`, `input_validity`, `reason_code`, `priority_reason`(= reason_code). 값은 문자열.
- `decision`이 None(아직 평가 없음)이면 RELEASE/RELEASE, OFF, STALE, NO_CHANGE.

## 11. `web.server` (QM) — SWR-014, 015

- `http.server.ThreadingHTTPServer` + `BaseHTTPRequestHandler`. 컨트롤러 접근은 `threading.Lock`으로 직렬화한다.
- 엔드포인트

  | 메서드·경로 | 동작 | 응답 |
  |---|---|---|
  | `GET /` | 시뮬레이터 HTML (`web/static/index.html`) | 200 text/html |
  | `GET /api/status` | `to_status(last_decision)` | 200 JSON / 직렬화 실패 500 |
  | `GET /api/events` | `event_log.items()` | 200 JSON |
  | `POST /api/step` | 본문 `{now_s?, vehicle?, command?}` → `parse_command` → `evaluate` | 200 상태 JSON / 본문 JSON 오류 400 |
  | 그 밖 | — | 404 |

- `now_s` 생략 시 서버 시계(`time.monotonic() − 시작 시각`)를 쓴다.
- `--tick` 옵션: 별도 스레드가 `CYCLE_S`마다 `evaluate(서버 시계)` 호출. 기본 꺼짐 (AD-04).
- 실행: `python -m child_lock.web.server --port 8000 [--tick]`

## 12. `replay` (QM) — SWR-016

```
run(vectors: list[dict]) -> list[dict]       # 새 컨트롤러·EventLog로 재생, 주기별 상태 JSON
digest(vectors: list[dict]) -> str           # run 결과 + 최종 이벤트를 정렬 키 JSON으로 직렬화한 SHA-256
```

- 벡터 형식: `{"now_s": float, "vehicle": {...}?, "command": {...}?}`
- 실행: `python -m child_lock.replay vectors.json [--repeat 1000]` → 모든 반복의 해시가 같으면 종료 코드 0.

## 13. 추적: SWR → 상세 설계 요소

| SWR | 설계 요소 |
|---|---|
| 001 | arbiter rank 9 |
| 002 | driver_request.parse_command, arbiter 보조 코드 4 |
| 003 | arbiter rank 8, `AUTO_LOCK_SPEED_KPH` |
| 004 | arbiter rank 9 조건, 보조 코드 3 |
| 005 | approach_guard.apply 4단계, arbiter rank 6 |
| 006 | approach_guard.apply 3단계, `OVERRIDE_WINDOW_US`, 보조 코드 2 |
| 007 | controller 래치, arbiter rank 2 |
| 008 | arbiter 보조 코드 1 |
| 009 | arbiter scope "side" 규칙, approach_guard 쪽별 처리 |
| 010 | event_log.record, `EVENT_CAPACITY` |
| 011 | event_log 이벤트 7키 |
| 012 | event_log deque (메모리 전용) |
| 013 | validator, input_monitor, controller._validity, arbiter rank 4 |
| 014 | status.to_status, web.server `/api/status` |
| 015 | web.server, `web/static/index.html` |
| 016 | D-01, controller(시계 주입), replay |
| 017 | arbiter rank 5 |
| 018 | arbiter rank 7 |
| 019 | arbiter RULES 순서 |
| 020 | arbiter rank 1, controller 래치·가드 초기화 |
| 021 | arbiter rank 3 |

**커버리지**: SWR 21/21.
