"""!
@brief 소스 줄을 코드, 주석, docstring, 빈 줄로 분류한다.

함수 길이 검사와 주석률 검사가 같은 기준으로 줄을 세도록 공용으로 쓴다.
"""

import ast
import io
import tokenize
from pathlib import Path

CODE = "code"
COMMENT = "comment"
DOCSTRING = "docstring"
BLANK = "blank"

# 코드 줄 판정에서 무시하는 토큰 (구조 토큰과 주석)
_NON_CODE_TOKENS = {
    tokenize.COMMENT,
    tokenize.NL,
    tokenize.NEWLINE,
    tokenize.INDENT,
    tokenize.DEDENT,
    tokenize.ENDMARKER,
    tokenize.ENCODING,
}


def _docstring_lines(tree):
    """!
    @brief 모듈, 클래스, 함수 docstring이 차지하는 줄 번호를 모은다.
    @param tree ast.parse 결과
    @return docstring 줄 번호 집합
    """
    owners = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    lines = set()
    for node in ast.walk(tree):
        if not isinstance(node, owners) or not node.body:
            continue
        first = node.body[0]
        is_doc = isinstance(first, ast.Expr) and isinstance(
            getattr(first, "value", None), ast.Constant
        )
        if is_doc and isinstance(first.value.value, str):
            lines.update(range(first.lineno, first.end_lineno + 1))
    return lines


def _token_lines(source):
    """!
    @brief 코드 토큰과 주석 토큰이 있는 줄 번호를 각각 모은다.
    @param source 소스 문자열
    @return (코드 줄 집합, 주석 줄 집합)
    """
    code, comment = set(), set()
    readline = io.StringIO(source).readline
    for tok in tokenize.generate_tokens(readline):
        if tok.type == tokenize.COMMENT:
            comment.add(tok.start[0])
        elif tok.type not in _NON_CODE_TOKENS:
            code.update(range(tok.start[0], tok.end[0] + 1))
    return code, comment


def iter_python_files(paths):
    """!
    @brief 파일과 폴더 목록에서 .py 파일을 정렬된 순서로 나열한다.
    @param paths 파일 또는 폴더 경로 목록
    @return Path 목록
    """
    files = []
    for p in map(Path, paths):
        files.extend(sorted(p.rglob("*.py")) if p.is_dir() else [p])
    return files


def classify_lines(source):
    """!
    @brief 각 줄의 종류를 판정한다.
    @param source 소스 문자열
    @return {줄 번호(1부터): CODE | COMMENT | DOCSTRING | BLANK}
    """
    docs = _docstring_lines(ast.parse(source))
    code, comment = _token_lines(source)
    kinds = {}
    for no in range(1, len(source.splitlines()) + 1):
        if no in docs:
            kinds[no] = DOCSTRING
        elif no in code:
            kinds[no] = CODE  # 줄 끝 주석이 있어도 코드 줄
        elif no in comment:
            kinds[no] = COMMENT
        else:
            kinds[no] = BLANK
    return kinds
