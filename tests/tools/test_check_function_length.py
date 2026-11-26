"""!
@brief tools/check_function_length.py 단위 테스트.
"""

import textwrap

from check_function_length import find_long_functions, main


def _source(text: str) -> str:
    """!
    @brief 들여쓰기를 제거한 테스트용 소스를 만든다.
    @param text 원본 문자열
    @return 들여쓰기가 제거된 소스
    """
    return textwrap.dedent(text)


def test_function_over_limit_is_reported():
    """!
    @brief 기준을 넘는 함수의 이름, 시작 줄, 줄 수를 보고하는지 확인한다.
    """
    body = "".join(f"    x{i} = {i}\n" for i in range(4))
    src = "def f():\n" + body
    result = find_long_functions(src, max_lines=4)
    assert [(v.name, v.lineno, v.lines) for v in result] == [("f", 1, 5)]


def test_blank_comment_and_docstring_lines_are_not_counted():
    """!
    @brief 빈 줄, 주석 줄, docstring을 세면 잘못된 위반이 나오는 결함을 잡는다.
    """
    src = _source('''
        def f():
            """!
            @brief 설명
            """
            # 주석

            a = 1
            b = 2  # 줄 끝 주석은 코드 줄
            return a + b
    ''')
    # 순수 코드: def, a, b, return = 4줄
    assert find_long_functions(src, max_lines=3)[0].lines == 4
    assert find_long_functions(src, max_lines=4) == []


def test_async_function_and_method_are_checked():
    """!
    @brief async 함수와 클래스 메서드를 빠뜨리는 결함을 잡는다.
    """
    src = _source("""
        class A:
            async def run(self):
                a = 1
                return a
    """)
    result = find_long_functions(src, max_lines=2)
    assert [(v.name, v.lines) for v in result] == [("run", 3)]


def test_main_fails_and_reports_location_when_a_file_violates(tmp_path, capsys):
    """!
    @brief 위반 파일이 있으면 종료 코드 1과 위치를 출력하는지 확인한다.
    """
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "ok.py").write_text("def a():\n    return 1\n", encoding="utf-8")
    (pkg / "bad.py").write_text(
        "def big():\n    x = 1\n    y = 2\n    return x + y\n",
        encoding="utf-8",
    )
    assert main([str(pkg), "--max", "3"]) == 1
    out = capsys.readouterr().out
    assert "bad.py:1 big 4" in out
    assert "ok.py" not in out


def test_main_passes_when_all_functions_within_limit(tmp_path):
    """!
    @brief 위반이 없으면 종료 코드 0인지 확인한다.
    """
    f = tmp_path / "ok.py"
    f.write_text("def a():\n    return 1\n", encoding="utf-8")
    assert main([str(f)]) == 0
