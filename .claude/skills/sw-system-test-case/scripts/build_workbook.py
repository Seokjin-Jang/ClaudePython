"""Validate test-case JSON and build the system test specification workbook (.xlsx).

Usage:
  python build_workbook.py cases.json --out spec.xlsx [--template form.xlsx] [--check-only]

Exit code 1 (and no workbook) when validation errors exist. Warnings are printed
but do not block the build. See SKILL.md for the JSON schema.
"""
import argparse
import json
import re
import sys
from collections import Counter, OrderedDict
from copy import copy

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    sys.exit("openpyxl is required: python -m pip install openpyxl")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

FUNC, NONFUNC = "기능", "비기능"
SHEET = {FUNC: "기능 테스트", NONFUNC: "비기능 테스트"}
EP, BVA, PW, WOW = "동치 클래스", "경계값 분석", "페어와이즈", "WoW 검증"
KNOWN_TECHNIQUES = {EP, BVA, PW, WOW, "요구사항 분석", "오류 추정", "고장 주입",
                    "운용 시나리오", "상태 전이", "결정 테이블", "기능 의존성 분석", "백투백"}
PROPOSAL_LABEL, BASE_LABEL = "제안", "기본"

# Default columns: (field key, header)
DEFAULT_COLUMNS = [
    ("id", "테스트 케이스 ID"),
    ("basis_ids", "테스트 베이시스 ID"),
    ("objective", "테스트 목적"),
    ("preconditions", "사전 조건"),
    ("inputs", "입력값"),
    ("procedure", "절차"),
    ("expected", "예상 출력값"),
    ("techniques", "사용한 테스트 기법"),
    ("proposal", "구분"),
    ("environment", "테스트 환경"),
    ("notes", "비고"),
]

# Template header synonyms (compared after removing spaces/punctuation, lowercase)
SYNONYMS = {
    "id": ["테스트케이스id", "tcid", "testcaseid", "케이스id", "시험항목id", "시험케이스id", "tc번호", "testid", "id", "no", "번호"],
    "basis_ids": ["테스트베이시스id", "베이시스id", "요구사항id", "관련요구사항", "요구사항", "reqid", "requirementid",
                  "requirement", "testbasisid", "testbasis", "추적id", "traceability"],
    "objective": ["테스트목적", "시험목적", "목적", "objective", "purpose", "testobjective", "설명", "description", "테스트명",
                  "title", "시험항목", "테스트항목", "테스트제목", "시험명"],
    "preconditions": ["사전조건", "전제조건", "선행조건", "precondition", "preconditions"],
    "inputs": ["입력값", "입력", "입력조건", "입력데이터", "테스트데이터", "시험데이터", "input", "inputs", "testdata"],
    "procedure": ["절차", "테스트절차", "시험절차", "테스트단계", "수행절차", "procedure", "steps", "teststeps"],
    "expected": ["예상출력값", "예상결과", "기대결과", "기대값", "예상값", "합격기준", "expected", "expectedresult",
                 "expectedoutput", "passcriteria"],
    "techniques": ["사용한테스트기법", "테스트기법", "시험기법", "기법", "설계기법", "technique", "techniques", "testtechnique"],
    "proposal": ["구분", "제안", "제안여부", "proposal"],
    "environment": ["테스트환경", "시험환경", "환경", "environment", "testenvironment"],
    "notes": ["비고", "참고", "notes", "note", "remark", "remarks", "comment"],
    "category": ["분류", "테스트유형", "유형", "category", "type"],
}

VAGUE = [r"정상\s*적으로", r"정상\s*동작", r"적절", r"올바르", r"올바른", r"문제\s*없", r"잘\s+동작",
         r"\bTBD\b", r"\bTBC\b", r"\?\?", r"등등"]

HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(bold=True, color="FFFFFF")
PROPOSAL_FILL = PatternFill("solid", fgColor="FFF2CC")
GAP_FILL = PatternFill("solid", fgColor="F8CBAD")
THIN = Side(style="thin", color="A6A6A6")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")


def norm(s):
    return re.sub(r"[\s_\-./()\[\]:#]", "", str(s or "")).lower()


def as_list(v):
    if v is None or v == "":
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip() for x in re.split(r"[,\n;]", str(v)) if x.strip()]


def cell_text(tc, key):
    v = tc.get(key)
    if key == "proposal":
        return PROPOSAL_LABEL if tc.get("proposal") else BASE_LABEL
    if key == "procedure":
        steps = as_list(v) if not isinstance(v, list) else [str(x) for x in v]
        return "\n".join(s if re.match(r"^\d+[.)]", s.strip()) else f"{i}. {s}" for i, s in enumerate(steps, 1))
    if key in ("basis_ids", "techniques"):
        return ", ".join(as_list(v))
    if isinstance(v, list):
        return "\n".join(str(x) for x in v)
    return "" if v is None else str(v)


# ---------------------------------------------------------------- validation
def validate(data):
    errors, warnings = [], []
    basis = data.get("test_basis") or []
    cases = data.get("test_cases") or []
    if not basis:
        errors.append("test_basis가 비어 있습니다.")
    if not cases:
        errors.append("test_cases가 비어 있습니다.")

    basis_ids = [str(b.get("id", "")).strip() for b in basis]
    for bid, n in Counter(basis_ids).items():
        if not bid:
            errors.append("ID가 없는 테스트 베이시스 항목이 있습니다.")
        elif n > 1:
            errors.append(f"테스트 베이시스 ID 중복: {bid}")
    basis_set = set(basis_ids)

    for cid, n in Counter(str(c.get("id", "")).strip() for c in cases).items():
        if cid and n > 1:
            errors.append(f"테스트 케이스 ID 중복: {cid} ({n}개)")

    pw_case_ids = {cid for m in data.get("pairwise") or [] for cid in as_list(m.get("case_ids"))}
    seen_content = {}
    tech_counter = Counter()
    for c in cases:
        cid = str(c.get("id", "")).strip() or "(ID 없음)"
        for key, label in [("id", "테스트 케이스 ID"), ("objective", "테스트 목적"), ("inputs", "입력값"),
                           ("expected", "예상 출력값")]:
            if not str(c.get(key) or "").strip():
                errors.append(f"{cid}: '{label}' 누락")
        if not as_list(c.get("procedure")):
            errors.append(f"{cid}: '절차' 누락")
        if c.get("category") not in (FUNC, NONFUNC):
            errors.append(f"{cid}: category는 '{FUNC}' 또는 '{NONFUNC}'여야 합니다 (현재: {c.get('category')!r})")
        bids = as_list(c.get("basis_ids"))
        if not bids:
            errors.append(f"{cid}: 테스트 베이시스 ID가 없습니다 (추적성 위반)")
        for b in bids:
            if b not in basis_set:
                errors.append(f"{cid}: 존재하지 않는 테스트 베이시스 ID '{b}' (추적성 위반)")
        techs = as_list(c.get("techniques"))
        if not techs:
            errors.append(f"{cid}: '사용한 테스트 기법' 누락")
        for t in techs:
            tech_counter[t] += 1
            if t not in KNOWN_TECHNIQUES:
                warnings.append(f"{cid}: 알 수 없는 기법 표기 '{t}' (오타인지 확인)")
        if PW in techs and cid not in pw_case_ids:
            errors.append(f"{cid}: '{PW}' 케이스인데 PICT 결과(pairwise[].case_ids)에 연결되어 있지 않습니다")
        if not str(c.get("environment") or "").strip():
            warnings.append(f"{cid}: 테스트 환경 미기재")
        exp = str(c.get("expected") or "")
        for pat in VAGUE:
            if re.search(pat, exp, re.IGNORECASE):
                warnings.append(f"{cid}: 예상 출력값에 판정하기 어려운 표현 ('{re.search(pat, exp, re.IGNORECASE).group(0)}')")
                break
        key = (c.get("category"), norm(c.get("preconditions")), norm(c.get("inputs")), norm(c.get("expected")))
        if key[2] and key[3]:
            if key in seen_content:
                errors.append(f"{cid}: {seen_content[key]}와 사전 조건·입력·예상 결과가 같은 중복 케이스")
            else:
                seen_content[key] = cid

    # coverage: only non-proposal cases count
    covered = {b for c in cases if not c.get("proposal") for b in as_list(c.get("basis_ids"))}
    for b in basis:
        bid = str(b.get("id", "")).strip()
        if bid and bid not in covered:
            only_prop = any(bid in as_list(c.get("basis_ids")) for c in cases)
            why = " (제안 케이스만 있음 — 제안은 커버리지에 포함되지 않음)" if only_prop else ""
            errors.append(f"커버리지 누락: {bid}{why}")
        btype = b.get("type")
        if btype in (FUNC, NONFUNC):
            cats = {c.get("category") for c in cases if bid in as_list(c.get("basis_ids"))}
            if cats and btype not in cats:
                warnings.append(f"{bid}: 베이시스 유형은 '{btype}'인데 해당 시트의 케이스가 없습니다")

    if tech_counter[EP] == 0:
        errors.append(f"필수 기법 '{EP}'이(가) 한 번도 사용되지 않았습니다")
    if tech_counter[BVA] == 0:
        errors.append(f"필수 기법 '{BVA}'이(가) 한 번도 사용되지 않았습니다")
    if tech_counter[WOW] == 0:
        warnings.append(f"'{WOW}'(엣지 케이스)가 없습니다")

    for m in data.get("pairwise") or []:
        rows, ids = m.get("rows") or [], as_list(m.get("case_ids"))
        if len(rows) != len(ids):
            warnings.append(f"페어와이즈 '{m.get('name')}': PICT 행 {len(rows)}개 / 케이스 {len(ids)}개 — 행과 케이스가 1:1이 아닙니다")
        for b in as_list(m.get("basis_ids")):
            if b not in basis_set:
                errors.append(f"페어와이즈 '{m.get('name')}': 존재하지 않는 베이시스 ID '{b}'")

    for i in data.get("issues") or []:
        if i.get("basis_id") and str(i["basis_id"]) not in basis_set:
            warnings.append(f"확인 필요 항목의 베이시스 ID '{i['basis_id']}'가 test_basis에 없습니다")

    return errors, warnings, tech_counter, covered


# ---------------------------------------------------------------- workbook helpers
def style_header(ws, row, ncols):
    for col in range(1, ncols + 1):
        c = ws.cell(row=row, column=col)
        c.fill, c.font, c.border = HEADER_FILL, HEADER_FONT, BORDER
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")


def write_table(ws, headers, rows, widths=None, start_row=1, fills=None):
    for j, h in enumerate(headers, 1):
        ws.cell(row=start_row, column=j, value=h)
    style_header(ws, start_row, len(headers))
    for i, r in enumerate(rows, start_row + 1):
        for j, v in enumerate(r, 1):
            c = ws.cell(row=i, column=j, value=v)
            c.alignment, c.border = WRAP, BORDER
            if fills and fills[i - start_row - 1]:
                c.fill = fills[i - start_row - 1]
    if widths:
        for j, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(j)].width = w
    return start_row + len(rows)


CASE_WIDTHS = {"id": 14, "basis_ids": 16, "objective": 36, "preconditions": 26, "inputs": 30,
               "procedure": 46, "expected": 40, "techniques": 20, "proposal": 8, "environment": 12,
               "notes": 30, "category": 8}


def find_header_row(ws):
    best = (None, 0)
    for r in range(1, min(ws.max_row, 20) + 1):
        vals = [ws.cell(row=r, column=c).value for c in range(1, ws.max_column + 1)]
        hits = sum(1 for v in vals if v and map_header(v))
        if hits > best[1]:
            best = (r, hits)
    return best[0] if best[1] >= 3 else None


def map_header(h):
    n = norm(h)
    for key, syns in SYNONYMS.items():
        if n in syns:
            return key
    return None


def build_case_sheets_template(wb_path, cases, warnings):
    wb = load_workbook(wb_path)
    tpl, hrow = None, None
    for ws in wb.worksheets:  # the case sheet is often not first (cover / history sheets)
        hrow = find_header_row(ws)
        if hrow is not None:
            tpl = ws
            break
    if tpl is None:
        sys.exit(f"양식 '{wb_path}'의 어느 시트에서도 머리글 행을 찾지 못했습니다 (알려진 열 이름이 3개 이상 필요).")
    warnings.append(f"양식 시트 '{tpl.title}'의 {hrow}행을 머리글로 사용했습니다")
    headers = []
    for c in range(1, tpl.max_column + 1):
        v = tpl.cell(row=hrow, column=c).value
        if v is not None and str(v).strip():
            headers.append((c, str(v).strip()))
    mapping = {}
    used = set()
    for col, h in headers:
        k = map_header(h)
        if k and k not in used:
            mapping[col] = k
            used.add(k)
        else:
            mapping[col] = ("raw", h)  # filled from a case key with the exact header name, if any
    # traceability and technique are mandatory even when the template lacks them
    last = max(c for c, _ in headers)
    for key, label in [("basis_ids", "테스트 베이시스 ID"), ("techniques", "사용한 테스트 기법"), ("proposal", "구분")]:
        if key not in used:
            last += 1
            mapping[last] = key
            src = tpl.cell(row=hrow, column=last - 1)
            dst = tpl.cell(row=hrow, column=last, value=label)
            dst._style = copy(src._style)
            warnings.append(f"양식에 '{label}' 열이 없어 끝에 추가했습니다")
    unmapped = [h for c, h in headers if isinstance(mapping[c], tuple)]
    sample_style = {c: copy(tpl.cell(row=hrow + 1, column=c)._style) for c in mapping}

    # clear existing data rows below the header
    if tpl.max_row > hrow:
        tpl.delete_rows(hrow + 1, tpl.max_row - hrow)
    nf = wb.copy_worksheet(tpl)
    tpl.title, nf.title = SHEET[FUNC], SHEET[NONFUNC]
    wb.move_sheet(nf, offset=wb.index(tpl) + 1 - wb.index(nf))

    filled_raw = set()
    for cat, ws in [(FUNC, tpl), (NONFUNC, nf)]:
        r = hrow + 1
        for tc in (c for c in cases if c.get("category") == cat):
            for col, key in mapping.items():
                if isinstance(key, tuple):
                    v = tc.get(key[1])
                    if v is not None:
                        filled_raw.add(key[1])
                    v = "" if v is None else (", ".join(map(str, v)) if isinstance(v, list) else v)
                else:
                    v = cat if key == "category" else cell_text(tc, key)
                    if key == "notes" and "environment" not in used and tc.get("environment"):
                        v = f"[환경: {tc['environment']}] {v}".strip()
                cell = ws.cell(row=r, column=col, value=v)
                cell._style = copy(sample_style[col])
                cell.alignment = WRAP
                if tc.get("proposal"):
                    cell.fill = PROPOSAL_FILL
            r += 1
    missing = [h for h in unmapped if h not in filled_raw]
    if missing:
        warnings.append("양식의 다음 열은 채울 값이 없어 비워 두었습니다: " + ", ".join(missing))
    not_in_template = [lbl for k, lbl in DEFAULT_COLUMNS if k not in used and k not in ("basis_ids", "techniques", "proposal")
                       and not (k == "environment" and "notes" in used)]
    if "environment" not in used and "notes" in used:
        warnings.append("양식에 테스트 환경 열이 없어 비고 열에 '[환경: ...]'으로 넣었습니다")
    if not_in_template:
        warnings.append("양식에 없는 기본 항목(출력하지 않음): " + ", ".join(not_in_template))
    return wb


def build_case_sheets_default(cases):
    wb = Workbook()
    wb.remove(wb.active)
    headers = [h for _, h in DEFAULT_COLUMNS]
    widths = [CASE_WIDTHS[k] for k, _ in DEFAULT_COLUMNS]
    for cat in (FUNC, NONFUNC):
        ws = wb.create_sheet(SHEET[cat])
        sel = [c for c in cases if c.get("category") == cat]
        rows = [[cell_text(tc, k) for k, _ in DEFAULT_COLUMNS] for tc in sel]
        fills = [PROPOSAL_FILL if tc.get("proposal") else None for tc in sel]
        write_table(ws, headers, rows, widths, fills=fills)
        ws.freeze_panes = "B2"
        ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{max(1, len(rows) + 1)}"
    return wb


def add_trace_sheet(wb, data):
    ws = wb.create_sheet("추적성 매트릭스")
    cases = data["test_cases"]
    rows, fills = [], []
    for b in data["test_basis"]:
        bid = str(b["id"]).strip()
        rel = [c for c in cases if bid in as_list(c.get("basis_ids"))]
        base = [c["id"] for c in rel if not c.get("proposal")]
        prop = [c["id"] for c in rel if c.get("proposal")]
        techs = sorted({t for c in rel for t in as_list(c.get("techniques"))})
        ok = bool(base)
        rows.append([bid, b.get("title", ""), b.get("type", ""), b.get("asil", ""), len(base), len(prop),
                     "\n".join(base), "\n".join(prop), ", ".join(techs), "O" if ok else "X"])
        fills.append(None if ok else GAP_FILL)
    write_table(ws, ["베이시스 ID", "제목", "유형", "ASIL", "기본 TC 수", "제안 TC 수", "기본 테스트 케이스",
                     "제안 테스트 케이스", "적용 기법", "커버"],
                rows, [14, 34, 8, 6, 9, 9, 18, 18, 30, 6], fills=fills)
    ws.freeze_panes = "B2"


def add_summary_sheet(wb, data, tech_counter, covered, keep_cover=False):
    # with a user template, keep its own first sheet (usually a cover) in front
    pos = wb.index(wb[SHEET[NONFUNC]]) + 1 if keep_cover else 0
    ws = wb.create_sheet("커버리지 요약", pos)
    basis, cases = data["test_basis"], data["test_cases"]
    nb = len(basis)
    ncov = sum(1 for b in basis if str(b["id"]).strip() in covered)
    traced = sum(1 for c in cases if as_list(c.get("basis_ids")))
    info = [
        ("프로젝트", data.get("project", "")),
        ("문서 ID", data.get("document_id", "")),
        ("버전", data.get("version", "")),
        ("테스트 베이시스 항목 수", nb),
        ("커버된 베이시스 항목 수 (제안 제외)", ncov),
        ("테스트 베이시스 커버리지", f"{(ncov / nb * 100) if nb else 0:.1f}%"),
        ("테스트 케이스 수 (전체)", len(cases)),
        ("  기능 테스트", sum(1 for c in cases if c.get("category") == FUNC)),
        ("  비기능 테스트", sum(1 for c in cases if c.get("category") == NONFUNC)),
        ("  제안 케이스", sum(1 for c in cases if c.get("proposal"))),
        ("베이시스로 추적되는 케이스 비율", f"{(traced / len(cases) * 100) if cases else 0:.1f}%"),
        ("PICT 페어와이즈 모델 수", len(data.get("pairwise") or [])),
        ("확인 필요 항목 수", len(data.get("issues") or [])),
    ]
    end = write_table(ws, ["항목", "값"], [list(x) for x in info], [38, 24])
    tech_rows = [[t, n] for t, n in sorted(tech_counter.items(), key=lambda x: -x[1])]
    write_table(ws, ["테스트 기법", "케이스 수"], tech_rows, start_row=end + 2)


def add_pairwise_sheet(wb, data):
    models = data.get("pairwise") or []
    if not models:
        return
    ws = wb.create_sheet("페어와이즈")
    r = 1
    for m in models:
        ws.cell(row=r, column=1, value=f"모델: {m.get('name', '')}").font = Font(bold=True, size=12)
        r += 1
        for label, val in [("베이시스 ID", ", ".join(as_list(m.get("basis_ids")))),
                           ("도구", "Microsoft PICT (github.com/microsoft/pict)"),
                           ("옵션", m.get("options", "/o:2")),
                           ("모델", m.get("model", ""))]:
            ws.cell(row=r, column=1, value=label).font = Font(bold=True)
            c = ws.cell(row=r, column=2, value=val)
            c.alignment = WRAP
            r += 1
        rows = m.get("rows") or []
        ids = as_list(m.get("case_ids"))
        if rows:
            params = list(OrderedDict.fromkeys(k for row in rows for k in row))
            table = [[ids[i] if i < len(ids) else ""] + [row.get(p, "") for p in params] for i, row in enumerate(rows)]
            r = write_table(ws, ["테스트 케이스 ID"] + params, table, start_row=r + 1) + 2
        else:
            r += 1
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 60


def add_issue_sheet(wb, data):
    issues = data.get("issues") or []
    if not issues:
        return
    ws = wb.create_sheet("확인 필요")
    rows = [[i.get("basis_id", ""), i.get("issue", ""), i.get("assumption", ""), ", ".join(as_list(i.get("case_ids")))]
            for i in issues]
    write_table(ws, ["베이시스 ID", "확인 필요 사항", "테스트에 적용한 가정", "관련 테스트 케이스"], rows, [14, 50, 40, 24])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cases")
    ap.add_argument("--out")
    ap.add_argument("--template")
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()

    with open(args.cases, encoding="utf-8-sig") as f:
        data = json.load(f)
    errors, warnings, tech_counter, covered = validate(data)

    nb = len(data.get("test_basis") or [])
    ncov = sum(1 for b in data.get("test_basis") or [] if str(b.get("id", "")).strip() in covered)
    print(f"베이시스 {nb}개, 커버 {ncov}개 ({(ncov / nb * 100) if nb else 0:.1f}%), "
          f"테스트 케이스 {len(data.get('test_cases') or [])}개")
    print("기법별: " + ", ".join(f"{t} {n}" for t, n in tech_counter.most_common()))
    for e in errors:
        print(f"[오류] {e}")

    if errors:
        for w in warnings:
            print(f"[경고] {w}")
        print(f"오류 {len(errors)}개 — 엑셀을 만들지 않았습니다.")
        return 1
    if args.check_only:
        for w in warnings:
            print(f"[경고] {w}")
        print(f"검사 통과 (경고 {len(warnings)}개)")
        return 0
    if not args.out:
        sys.exit("--out 이 필요합니다")

    if args.template:
        wb = build_case_sheets_template(args.template, data["test_cases"], warnings)
    else:
        wb = build_case_sheets_default(data["test_cases"])
    add_trace_sheet(wb, data)
    add_summary_sheet(wb, data, tech_counter, covered, keep_cover=bool(args.template))
    add_pairwise_sheet(wb, data)
    add_issue_sheet(wb, data)
    wb.save(args.out)

    for w in warnings:
        print(f"[경고] {w}")
    print(f"저장: {args.out} (경고 {len(warnings)}개)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
