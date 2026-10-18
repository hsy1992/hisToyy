import threading
from datetime import date, datetime

import pytest

from app.configuration import DatabaseConfig
from app.domain import validate_rows
from test_import import FakeRepository, cache, run_engine, source_row


@pytest.mark.parametrize("invalid", ["X" * 51, "😀" * 26])
def test_review_invalid_source_never_reaches_query_or_blocks_valid_document(tmp_path, invalid):
    class CheckedRepository(FakeRepository):
        def find_existing(self, sources):
            assert all(0 < len(value.encode("utf-16-le")) <= 100 for value in sources)
            return super().find_existing(sources)
    rows = [source_row("GOOD"), source_row(invalid, number=3)]
    result, repository = run_engine(tmp_path, rows, CheckedRepository())
    assert rows[0].status == "导入成功"
    assert rows[1].status == "校验失败"
    assert len(repository.committed) == 1 and result["report"]


def test_review_copied_blank_marker_rows_fail_whole_document_and_keep_other_docs(tmp_path):
    rows = [source_row("DUP", number=2, **{"销售标识": "", "行号": "1"}),
            source_row("DUP", number=3, **{"销售标识": "", "行号": "1"}),
            source_row("DUP", number=4, **{"数量": "5"}), source_row("GOOD", number=5)]
    assert rows[0].values == rows[1].values
    _, repository = run_engine(tmp_path, rows)
    assert [row.status for row in rows] == ["校验失败", "校验失败", "整单受阻", "导入成功"]
    assert set(repository.committed) == {"good"}
    assert any("重复原始明细" in message for message in rows[0].reasons)


def test_review_blank_markers_with_distinct_original_rows_remain_valid():
    rows = [source_row(number=2, **{"销售标识": "", "数量": "1"}),
            source_row(number=3, **{"销售标识": "", "数量": "2"})]
    assert validate_rows(rows, cache(), threading.Event(), lambda *args: None)[0].ready


@pytest.mark.parametrize("other", ["2026/10/12", "20261012", datetime(2026, 10, 12), date(2026, 10, 12)])
def test_review_same_date_different_representations_do_not_conflict(other):
    rows = [source_row(number=2), source_row(number=3, **{"单据日期": other})]
    doc = validate_rows(rows, cache(), threading.Event(), lambda *args: None)[0]
    assert doc.ready
    assert all(row.parsed["date"] == date(2026, 10, 12) for row in rows)


def test_review_invalid_date_still_blocks_whole_document():
    rows = [source_row(number=2), source_row(number=3, **{"单据日期": "bad-date"})]
    assert not validate_rows(rows, cache(), threading.Event(), lambda *args: None)[0].ready
    assert any("日期格式无效" in reason for reason in rows[1].reasons)


@pytest.mark.parametrize("text", ["password=must-not-appear\n", "[sqlserver]\nip=localhost\nip=127.0.0.1\n", "[sqlserver]\n[sqlserver]\n"])
def test_review_ini_syntax_errors_are_safe_value_errors(tmp_path, text):
    path = tmp_path / "config.ini"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="配置文件语法错误") as error:
        DatabaseConfig.load(path)
    assert "must-not-appear" not in str(error.value)
