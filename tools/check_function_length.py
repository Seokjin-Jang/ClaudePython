"""!
@brief 함수별 순수 코드 줄 수를 검사한다.
"""

import argparse
import ast
import sys
from dataclasses import dataclass

from line_kinds import CODE, classify_lines, iter_python_files


@dataclass(frozen=True)
class Violation:
    """!
    @brief 기준을 넘은 함수 정보.
    """

    name: str
    lineno: int
    lines: int


def find_long_functions(source, max_lines):
    """!
    @brief 기준을 넘는 함수를 찾는다.
    """
    kinds = classify_lines(source)
    result = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            span = range(node.lineno, node.end_lineno + 1)
            count = sum(1 for no in span if kinds[no] == CODE)
            if count > max_lines:
                result.append(Violation(node.name, node.lineno, count))
    return result


def main(argv=None):
    """!
    @brief 명령줄 진입점. 위반이 있으면 위치를 출력한다.
    @param argv 명령줄 인자 (None이면 sys.argv 사용)
    @return 위반이 없으면 0, 있으면 1
    """
    parser = argparse.ArgumentParser(description="함수 순수 코드 줄 수 검사")
    parser.add_argument("paths", nargs="+", help="검사할 파일 또는 폴더")
    parser.add_argument("--max", type=int, default=50, help="허용 최대 줄 수")
    args = parser.parse_args(argv)
    failed = False
    for path in iter_python_files(args.paths):
        source = path.read_text(encoding="utf-8")
        for v in find_long_functions(source, args.max):
            print(f"{path}:{v.lineno} {v.name} {v.lines}줄 > {args.max}줄")
            failed = True
    return 1 if failed else 0


# 스크립트 직접 실행 진입점: main()은 테스트로 검증하므로 제외
if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
