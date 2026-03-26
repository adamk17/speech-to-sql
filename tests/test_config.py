import pytest
from unittest.mock import patch
import config


class TestConfigValidate:
    def test_raises_when_db_name_missing(self):
        with patch.multiple(config, DB_NAME=None, DB_USER="u", DB_PASSWORD="p", LLM_API_KEY="k"):
            with pytest.raises(ValueError, match="DB_NAME"):
                config.validate()

    def test_raises_when_db_user_missing(self):
        with patch.multiple(config, DB_NAME="db", DB_USER=None, DB_PASSWORD="p", LLM_API_KEY="k"):
            with pytest.raises(ValueError, match="DB_USER"):
                config.validate()

    def test_raises_when_llm_api_key_missing(self):
        with patch.multiple(config, DB_NAME="db", DB_USER="u", DB_PASSWORD="p", LLM_API_KEY=None):
            with pytest.raises(ValueError, match="LLM_API_KEY"):
                config.validate()

    def test_raises_when_multiple_missing(self):
        with patch.multiple(config, DB_NAME=None, DB_USER=None, DB_PASSWORD="p", LLM_API_KEY="k"):
            with pytest.raises(ValueError):
                config.validate()

    def test_passes_when_all_present(self):
        with patch.multiple(config, DB_NAME="db", DB_USER="u", DB_PASSWORD="p", LLM_API_KEY="k"):
            config.validate()
