import pytest
from unittest.mock import MagicMock
from redactor import (init_analyzer, get_related_word_stems,
                      redact_lines, concept_redaction,
                      anonymize_text, redact_file)


@pytest.fixture
def analyzer_and_stemmer():
    analyzer, stemmer = init_analyzer(model="en_core_web_lg")
    return analyzer, stemmer


def test_init_analyzer(analyzer_and_stemmer):
    analyzer, stemmer = analyzer_and_stemmer
    assert analyzer is not None
    assert stemmer is not None


def test_get_related_word_stems():
    stemmer = MagicMock()
    stemmer.stem = lambda x: x
    concept_words = ["test", "example"]

    related_stems = get_related_word_stems(concept_words, stemmer)

    assert "test" in related_stems
    assert "example" in related_stems
    assert "tests" in related_stems
    assert "examples" in related_stems


def test_redact_lines():
    lines = ["This is a test line.", "This line is not sensitive."]
    stemmer = MagicMock()
    stemmer.stem = lambda x: x
    related_word_stems = {"test"}

    result = redact_lines(lines, stemmer, related_word_stems, "This is a test.", [])
    assert result == ['████████████████████', 'This line is not sensitive.']


def test_concept_redaction():
    text = "This is a test. This is another line."
    concept_words = ["test"]
    stemmer = MagicMock()
    stemmer.stem = lambda x: x

    redacted_text, censored_terms = concept_redaction(text, concept_words, stemmer)
    assert redacted_text == "███████████████ This is another line."
    assert len(censored_terms) == 1
    assert censored_terms[0]["term"] == "This is a test."


def test_anonymize_text(analyzer_and_stemmer):
    analyzer, _ = analyzer_and_stemmer
    flags = MagicMock()
    flags.names = True
    flags.dates = False
    flags.phones = False
    flags.address = False

    text = "John Doe went to the store on 2022-01-01."

    anonymized_result, censored_terms = anonymize_text(text, analyzer, flags)

    assert anonymized_result != text
    assert len(censored_terms) > 0


def test_redact_file(analyzer_and_stemmer, tmp_path):
    analyzer, stemmer = analyzer_and_stemmer
    input_file = tmp_path / "test_input.txt"
    input_file.write_text("This is a test file.")

    flags = MagicMock()
    flags.names = False
    flags.dates = False
    flags.phones = False
    flags.address = False
    flags.concept = ["test"]

    redacted_text, censored_terms = redact_file(input_file, flags, analyzer, stemmer)

    assert redacted_text == "████████████████████"
    assert len(censored_terms) == 1
    assert censored_terms[0]["term"] == "This is a test file."


def test_redact_lines_no_matching_stems():
    lines = ["This line is safe.", "Another safe line."]
    stemmer = MagicMock()
    stemmer.stem = lambda x: x
    related_word_stems = {"sensitive"}

    result = redact_lines(lines, stemmer, related_word_stems, "This is a safe text.", [])

    assert result == lines


def test_anonymize_text_no_flags(analyzer_and_stemmer):
    analyzer, _ = analyzer_and_stemmer
    flags = MagicMock()
    flags.names = False
    flags.dates = False
    flags.phones = False
    flags.address = False

    text = "This text contains no sensitive information."

    anonymized_result, censored_terms = anonymize_text(text, analyzer, flags)

    assert anonymized_result == text
    assert len(censored_terms) == 0
