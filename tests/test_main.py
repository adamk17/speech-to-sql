import pytest
import json
import os
from unittest.mock import patch
from main import print_history, export_history


SAMPLE_HISTORY = [
    {
        "question": "show all employees",
        "sql": "SELECT * FROM employees",
        "columns": ["emp_id", "full_name"],
        "rows": [{"emp_id": 1, "full_name": "Jan Kowal"}],
    }
]


class TestPrintHistory:
    def test_empty_history(self, capsys):
        print_history([])
        assert "(no history)" in capsys.readouterr().out

    def test_prints_question_and_sql(self, capsys):
        print_history(SAMPLE_HISTORY)
        output = capsys.readouterr().out
        assert "show all employees" in output
        assert "SELECT * FROM employees" in output


class TestExportHistory:
    def test_empty_history(self, capsys):
        export_history([])
        assert "(no history to export)" in capsys.readouterr().out

    def test_creates_json_file(self, tmp_path, capsys):
        with patch("main.os.makedirs") as mock_makedirs, \
             patch("main.datetime") as mock_datetime, \
             patch("builtins.open", create=True):

            mock_datetime.now.return_value.strftime.return_value = "2026-01-01_12-00-00"

            export_history(SAMPLE_HISTORY)

        mock_makedirs.assert_called_once_with("history", exist_ok=True)
        output = capsys.readouterr().out
        assert "2026-01-01_12-00-00" in output

    def test_json_content(self):
        with patch("main.os.makedirs"), \
             patch("main.datetime") as mock_datetime:

            mock_datetime.now.return_value.strftime.return_value = "2026-01-01_12-00-00"

            real_open = open
            written = {}

            def fake_open(path, mode="r", **kwargs):
                if mode == "w":
                    import io
                    buf = io.StringIO()
                    class FakeFile:
                        def __enter__(self): return buf
                        def __exit__(self, *a): written["content"] = buf.getvalue()
                    return FakeFile()
                return real_open(path, mode, **kwargs)

            with patch("builtins.open", side_effect=fake_open):
                export_history(SAMPLE_HISTORY)

        data = json.loads(written["content"])
        assert data[0]["question"] == "show all employees"
        assert data[0]["sql"] == "SELECT * FROM employees"
