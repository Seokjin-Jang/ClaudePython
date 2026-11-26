# 시트 히터 제어 SW 요구사항 사양서 (SRS) v1.2

## 1. 인터페이스

| 신호 | 방향 | 범위 / 값 | 해상도 | 비고 |
|---|---|---|---|---|
| IGN_Status | 입력 (CAN) | OFF, ACC, ON, START | - | |
| SeatHeaterSw | 입력 (CAN) | OFF, LOW, MID, HIGH | - | 운전석 스위치 |
| BatteryVoltage | 입력 (ADC) | 0.0 ~ 20.0 V | 0.1 V | |
| SeatTemp | 입력 (ADC) | -40.0 ~ 125.0 ℃ | 0.1 ℃ | NTC 센서, 범위 밖 = 고장 |
| AmbientTemp | 입력 (CAN) | -40 ~ 85 ℃ | 1 ℃ | 0xFF = 무효 |
| RemoteStart | 입력 (CAN) | Inactive, Active | - | |
| SeatOccupied | 입력 (CAN) | NotOccupied, Occupied | - | |
| HeaterPWM | 출력 | 0 ~ 100 % | 1 % | |
| SwIndicator | 출력 | OFF, ON, BLINK_1Hz | - | 스위치 표시등 |
| DTC | 출력 | B1001(과열), B1002(센서 고장) | - | |

## 2. 기능 요구사항

**SRS-SH-001** (QM) 히터 단계 제어
IGN_Status = ON일 때 SeatHeaterSw 값에 따라 목표 온도를 LOW 30 ℃, MID 37 ℃, HIGH 42 ℃로 제어한다. SeatHeaterSw = OFF이면 HeaterPWM = 0 %이다. 목표 온도 도달 후 SeatTemp는 목표 ±2 ℃ 이내로 유지되어야 한다. 단계가 ON이면 SwIndicator = ON이다.

**SRS-SH-002** (QM) 동작 전압 범위
BatteryVoltage가 9.0 V 이상 16.0 V 이하일 때만 히터를 구동한다. 범위를 벗어나면 HeaterPWM = 0 %로 한다. 이후 BatteryVoltage가 9.5 V 이상 15.5 V 이하로 복귀하면 이전 단계로 재개한다.

**SRS-SH-003** (ASIL A) 과열 보호
SeatTemp ≥ 50.0 ℃가 되면 1 s 이내에 HeaterPWM = 0 %로 하고 DTC B1001을 저장한다. SeatTemp ≤ 45.0 ℃가 되면 이전 단계로 재개한다.

**SRS-SH-004** (ASIL A) 센서 고장 처리
SeatTemp가 -40.0 ℃ 미만 또는 125.0 ℃ 초과인 상태가 100 ms 이상 지속되면 HeaterPWM = 0 %, SwIndicator = BLINK_1Hz로 하고 DTC B1002를 저장한다. 고장 상태는 IGN 재시동 전까지 유지된다.

**SRS-SH-005** (QM) HIGH 단계 시간 제한
HIGH 단계가 연속 30분 유지되면 자동으로 MID 단계로 전환한다. 운전자가 스위치를 다시 조작하면 타이머는 초기화된다.

**SRS-SH-006** (QM) 원격 시동 연동
RemoteStart = Active이고 AmbientTemp ≤ 5 ℃이면 운전석 히터를 HIGH로 자동 동작한다. AmbientTemp가 무효(0xFF)이면 자동 동작하지 않는다. 이후 IGN_Status = ON이 되면 SeatHeaterSw 값을 따른다. SeatOccupied 신호와 무관하게 동작한다.

## 3. 비기능 요구사항

**SRS-SH-007** (QM) 응답 시간
SeatHeaterSw 변경 후 200 ms 이내에 HeaterPWM 출력 변경이 시작되어야 한다.

**SRS-SH-008** (QM) 실행 주기 및 부하
히터 제어 태스크는 10 ms 주기로 실행되며, 최대 부하 조건에서 ECU CPU 사용률은 70 % 이하여야 한다.
