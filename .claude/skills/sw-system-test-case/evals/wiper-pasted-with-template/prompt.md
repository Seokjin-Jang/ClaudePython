---
tags: [skill-creator]
max_turns: 60
timeout_seconds: 1800
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

와이퍼 제어 SW 요구사항 붙여넣을게. 우리 팀 시험 사양서 양식(stc_form.xlsx)에 맞춰서 시스템 테스트 케이스 작성해서 wiper_STC.xlsx로 줘.

REQ-WP-01 와이퍼 스위치(WiperSw: OFF, INT, LOW, HIGH)에 따라 모터를 구동한다. LOW = 45 cycle/min, HIGH = 65 cycle/min (허용오차 ±5 cycle/min).
REQ-WP-02 INT 모드의 간헐 주기는 차속(VehicleSpeed, 0~255 km/h, 해상도 1 km/h)에 따라 정한다: 0~30 km/h는 6 s, 31~80 km/h는 4 s, 81 km/h 이상은 2 s. 차속 신호가 무효(0xFF)이면 4 s로 한다.
REQ-WP-03 와셔 스위치(WasherSw)가 0.5 s 이상 눌리면 와셔 펌프를 구동하고, 스위치를 놓은 뒤 LOW 속도로 3회 와이핑 후 이전 모드로 복귀한다. 0.5 s 미만이면 와이핑 1회만 한다.
REQ-WP-04 후드가 열려 있고(HoodStatus = Open) 차속이 5 km/h 미만이면 와이퍼 스위치 입력과 무관하게 모터를 정지한다. 차속이 5 km/h 이상이면 스위치 입력을 따른다.
REQ-WP-05 와이퍼 동작 중 IGN이 OFF가 되면 와이퍼 암을 파킹 위치로 복귀시킨 후 정지한다.
REQ-WP-06 모터 전류가 15.0 A 이상인 상태가 200 ms 이상 지속되면 모터를 정지하고 DTC B2001을 저장한다. 3 s 후 1회 재시도한다.
REQ-WP-07 스위치 입력 후 모터 동작 변경은 100 ms 이내에 시작되어야 한다.

Input files: stc_form.xlsx
