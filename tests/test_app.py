"""
Unit tests for app.py predict() function.

conftest.py stubs transformers/gradio/torch so the model never loads
and Gradio never launches. We then patch app.summarizer per-test.
"""
import pytest
from unittest.mock import patch, call
import app


def _mock_summarizer(text):
    """Helper: returns the shape the real pipeline returns."""
    return [{"summary_text": text}]


class TestPredictOutput:
    def test_returns_string(self):
        with patch.object(app, "summarizer", return_value=[{"summary_text": "a summary"}]):
            result = app.predict("Some long article text.")
        assert isinstance(result, str)

    def test_returns_summary_text_field(self):
        expected = "Scientists discover new planet."
        with patch.object(app, "summarizer", return_value=[{"summary_text": expected}]):
            result = app.predict("Long article about space exploration...")
        assert result == expected

    def test_returns_empty_string_when_model_returns_empty(self):
        with patch.object(app, "summarizer", return_value=[{"summary_text": ""}]):
            result = app.predict("anything")
        assert result == ""


class TestPredictCallsModel:
    def test_passes_input_text_to_summarizer(self):
        input_text = "The quick brown fox jumps over the lazy dog."
        with patch.object(app, "summarizer", return_value=[{"summary_text": "fox jumps"}]) as mock:
            app.predict(input_text)
        mock.assert_called_once()
        assert mock.call_args[0][0] == input_text

    def test_passes_truncation_flag(self):
        with patch.object(app, "summarizer", return_value=[{"summary_text": "x"}]) as mock:
            app.predict("some text")
        _, kwargs = mock.call_args
        assert kwargs.get("truncation") is True

    def test_passes_token_limits(self):
        with patch.object(app, "summarizer", return_value=[{"summary_text": "x"}]) as mock:
            app.predict("some text")
        _, kwargs = mock.call_args
        assert kwargs.get("max_new_tokens") == 256
        assert kwargs.get("min_new_tokens") == 32

    def test_passes_no_repeat_ngram_size(self):
        with patch.object(app, "summarizer", return_value=[{"summary_text": "x"}]) as mock:
            app.predict("some text")
        _, kwargs = mock.call_args
        assert kwargs.get("no_repeat_ngram_size") == 3


class TestPredictEdgeCases:
    def test_empty_string_input(self):
        with patch.object(app, "summarizer", return_value=[{"summary_text": ""}]):
            result = app.predict("")
        assert result == ""

    def test_long_input_does_not_raise(self):
        long_text = "word " * 2000  # well beyond the 1024-token limit
        with patch.object(app, "summarizer", return_value=[{"summary_text": "summary of long text"}]):
            result = app.predict(long_text)
        assert isinstance(result, str)

    def test_single_sentence_input(self):
        with patch.object(app, "summarizer", return_value=[{"summary_text": "one sentence."}]):
            result = app.predict("One sentence.")
        assert result == "one sentence."
