"""!
@brief 파일별 주석률을 검사한다.
"""

import argparse
import sys
from collections import Counter

from line_kinds import BLANK, CODE, classify_lines, iter_python_files


def comment_ratio(source):
    """!
    @brief 주석률을 계산한다.
    @param source 소스 문자열
    @return (주석 줄 + docstring 줄) / 빈 줄을 뺀 전체 줄.
            빈 줄만 있는 파일은 None
    """
    counts = Counter(classify_lines(source).values())
    nonblank = sum(n for kind, n in counts.items() if kind != BLANK)
    if nonblank == 0:
        return None
    return (nonblank - counts[CODE]) / nonblank


def main(argv=None):
    """!
    @brief 명령줄 진입점. 기준 미달 파일과 주석률을 출력한다.
    @param argv 명령줄 인자 (None이면 sys.argv 사용)
    @return 모든 파일이 기준 이상이면 0, 아니면 1
    """
    parser = argparse.ArgumentParser(description="파일별 주석률 검사")
    parser.add_argument("paths", nargs="+", help="검사할 파일 또는 폴더")
    parser.add_argument("--min", type=float, default=0.2, help="최소 주석률")
    args = parser.parse_args(argv)
    failed = False
    for path in iter_python_files(args.paths):
        ratio = comment_ratio(path.read_text(encoding="utf-8"))
        if ratio is not None and ratio < args.min:
            print(f"{path} {ratio:.1%} < {args.min:.1%}")
            failed = True
    return 1 if failed else 0


# 스크립트 직접 실행 진입점: main()은 테스트로 검증하므로 제외
if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
