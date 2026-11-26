"""!
@brief tools/check_comment_ratio.py 단위 테스트.
"""

from check_comment_ratio import comment_ratio, main


def test_ratio_counts_comment_and_docstring_lines_over_nonblank_lines():
    """!
    @brief docstring·주석을 분자에, 빈 줄을 뺀 전체를 분모에 쓰는지 확인한다.
    """
    src = (
        '"""!\n'  # docstring 3줄
        "@brief 모듈\n"
        '"""\n'
        "\n"  # 빈 줄 제외
        "# 주석\n"  # 주석 1줄
        "x = 1  # 줄 끝 주석은 코드 줄\n"  # 코드
        "y = 2\n"  # 코드
        "z = 3\n"  # 코드
        "w = 4\n"  # 코드
    )
    # (3 + 1) / (3 + 1 + 4) = 0.5
    assert comment_ratio(src) == 0.5


def test_ratio_is_none_for_file_without_nonblank_lines():
    """!
    @brief 빈 파일에서 0으로 나누기 오류가 나는 결함을 잡는다.
    """
    assert comment_ratio("\n\n") is None


def test_main_fails_for_file_below_threshold(tmp_path, capsys):
    """!
    @brief 기준 미달 파일만 보고하고 빈 파일은 건너뛰는지 확인한다.
    """
    (tmp_path / "low.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
    (tmp_path / "high.py").write_text("# 설명\nx = 1\n", encoding="utf-8")
    (tmp_path / "empty.py").write_text("", encoding="utf-8")
    assert main([str(tmp_path), "--min", "0.2"]) == 1
    out = capsys.readouterr().out
    assert "low.py 0.0% < 20.0%" in out
    assert "high.py" not in out
    assert "empty.py" not in out


def test_main_passes_when_every_file_meets_threshold(tmp_path):
    """!
    @brief 모든 파일이 기준 이상이면 종료 코드 0인지 확인한다.
    """
    (tmp_path / "ok.py").write_text("# 설명\nx = 1\n", encoding="utf-8")
    assert main([str(tmp_path)]) == 0
