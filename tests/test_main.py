import json
from unittest.mock import patch
from main import print_history, export_history, display_result, main
from pipeline import PipelineResult


SAMPLE_HISTORY = [
    {
        "question": "show all employees",
        "sql": "SELECT * FROM employees",
        "columns": ["emp_id", "full_name"],
        "rows": [{"emp_id": 1, "full_name": "Jan Kowal"}],
    }
]


class TestMain:
    def test_print_history_empty(self, capsys):
        print_history([])
        assert "(no history)" in capsys.readouterr().out

    def test_print_history_shows_question_and_sql(self, capsys):
        print_history(SAMPLE_HISTORY)
        output = capsys.readouterr().out
        assert "show all employees" in output
        assert "SELECT * FROM employees" in output

    def test_export_history_empty(self, capsys):
        export_history([])
        assert "(no history to export)" in capsys.readouterr().out

    def test_export_history_creates_file(self, capsys):
        with patch("main.os.makedirs"), \
             patch("main.datetime") as mock_dt, \
             patch("builtins.open", create=True):
            mock_dt.now.return_value.strftime.return_value = "2026-01-01_12-00-00"
            export_history(SAMPLE_HISTORY)
        assert "2026-01-01_12-00-00" in capsys.readouterr().out

    def test_export_history_json_content(self):
        import io
        with patch("main.os.makedirs"), \
             patch("main.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2026-01-01_12-00-00"
            written = {}
            real_open = open

            def fake_open(path, mode="r", **kwargs):
                if mode == "w":
                    buf = io.StringIO()
                    class FakeFile:
                        def __enter__(self): return buf
                        def __exit__(self, *_): written["content"] = buf.getvalue()
                    return FakeFile()
                return real_open(path, mode, **kwargs)

            with patch("builtins.open", side_effect=fake_open):
                export_history(SAMPLE_HISTORY)

        data = json.loads(written["content"])
        assert data[0]["question"] == "show all employees"
        assert data[0]["sql"] == "SELECT * FROM employees"

    def test_display_result_shows_sql_and_rows(self, capsys):
        result = PipelineResult(
            sql="SELECT * FROM employees",
            columns=["id", "name"],
            rows=[{"id": 1, "name": "Jan"}],
        )
        display_result(result)
        output = capsys.readouterr().out
        assert "SELECT * FROM employees" in output
        assert "Jan" in output

    def test_display_result_shows_message(self, capsys):
        result = PipelineResult(message="Inserted 3 rows.")
        display_result(result)
        assert "Inserted 3 rows." in capsys.readouterr().out

    def test_main_exits_on_config_error(self, capsys):
        with patch("main.config.validate", side_effect=ValueError("Missing DB_NAME")):
            main()
        assert "Configuration error" in capsys.readouterr().out

    def test_main_calls_pipeline_and_displays_result(self, capsys):
        mock_result = PipelineResult(
            sql="SELECT * FROM employees",
            columns=["id"],
            rows=[{"id": 1}],
        )
        with patch("main.config.validate"), \
             patch("main.Database"), \
             patch("main.Pipeline") as mock_pipeline_cls, \
             patch("builtins.input", side_effect=["show employees", KeyboardInterrupt]):
            mock_pipeline_cls.return_value.run.return_value = mock_result
            main()
        assert "SELECT * FROM employees" in capsys.readouterr().out

    def test_main_result_added_to_history(self, capsys):
        mock_result = PipelineResult(
            sql="SELECT * FROM employees",
            columns=["id"],
            rows=[{"id": 1}],
        )
        with patch("main.config.validate"), \
             patch("main.Database"), \
             patch("main.Pipeline") as mock_pipeline_cls, \
             patch("builtins.input", side_effect=["show employees", "print history", KeyboardInterrupt]):
            mock_pipeline_cls.return_value.run.return_value = mock_result
            main()
        output = capsys.readouterr().out
        assert "show employees" in output
