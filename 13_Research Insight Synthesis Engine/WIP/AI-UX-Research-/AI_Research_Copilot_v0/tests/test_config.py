import os
import tempfile
import unittest
from pathlib import Path

from ai_ux_core import config


class DotenvLoadingTests(unittest.TestCase):
    """Isolated from the rest of the suite: patches config's module globals
    and os.environ, and always restores both so other tests never see a
    leaked AI_UX_LLM_API_KEY that would flip them out of offline_preview."""

    ENV_KEYS = (
        "AI_UX_LLM_API_KEY",
        "OPENAI_API_KEY",
        "AI_UX_LLM_MODEL",
        "AI_UX_LLM_BASE_URL",
        "AI_UX_LLM_TIMEOUT_SECONDS",
        "AI_UX_LLM_API_STYLE",
    )

    def setUp(self):
        self._original_environ = {key: os.environ.get(key) for key in self.ENV_KEYS}
        self._original_env_file_path = config.ENV_FILE_PATH
        self._original_dotenv_loaded = config._dotenv_loaded
        for key in self.ENV_KEYS:
            os.environ.pop(key, None)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.addCleanup(self._restore)

    def _restore(self):
        for key, value in self._original_environ.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        config.ENV_FILE_PATH = self._original_env_file_path
        config._dotenv_loaded = self._original_dotenv_loaded

    def _write_env_file(self, content: str) -> Path:
        env_path = Path(self.temp_dir.name) / ".env"
        env_path.write_text(content, encoding="utf-8")
        config.ENV_FILE_PATH = env_path
        config._dotenv_loaded = False
        return env_path

    def test_parses_values_and_skips_comments_and_blank_lines(self):
        self._write_env_file(
            "AI_UX_LLM_API_KEY=dotenv-key\n"
            "\n"
            "# a comment\n"
            'AI_UX_LLM_MODEL="quoted-model"\n'
            "AI_UX_LLM_BASE_URL=https://example.com/v1\n"
        )
        settings = config.load_llm_settings(default_timeout_seconds=42.0)
        self.assertEqual(settings.api_key, "dotenv-key")
        self.assertEqual(settings.model, "quoted-model")
        self.assertEqual(settings.base_url, "https://example.com/v1")
        self.assertEqual(settings.timeout_seconds, 42.0)

    def test_real_environment_variable_wins_over_dotenv(self):
        self._write_env_file("AI_UX_LLM_MODEL=from-dotenv\n")
        os.environ["AI_UX_LLM_MODEL"] = "from-real-env"
        settings = config.load_llm_settings(default_timeout_seconds=42.0)
        self.assertEqual(settings.model, "from-real-env")

    def test_missing_env_file_is_a_no_op(self):
        config.ENV_FILE_PATH = Path(self.temp_dir.name) / "does-not-exist.env"
        config._dotenv_loaded = False
        settings = config.load_llm_settings(default_timeout_seconds=7.0)
        self.assertIsNone(settings.api_key)
        self.assertEqual(settings.timeout_seconds, 7.0)

    def test_dotenv_is_only_read_once_per_process(self):
        env_path = self._write_env_file("AI_UX_LLM_API_KEY=first-value\n")
        config.load_llm_settings(default_timeout_seconds=1.0)
        env_path.write_text("AI_UX_LLM_API_KEY=second-value\n", encoding="utf-8")
        settings = config.load_llm_settings(default_timeout_seconds=1.0)
        self.assertEqual(settings.api_key, "first-value")

    def test_openai_api_key_is_a_fallback(self):
        self._write_env_file("")
        os.environ["OPENAI_API_KEY"] = "fallback-key"
        settings = config.load_llm_settings(default_timeout_seconds=1.0)
        self.assertEqual(settings.api_key, "fallback-key")


if __name__ == "__main__":
    unittest.main()
