import pytest
from unittest.mock import MagicMock
from redactor import (
    init_model,
    get_related_word_stems,
    redact_lines,
    concept_redaction,
    redact_file,
    redact_names,
    redact_dates,
    redact_addresses,
    redact_phones,
)


@pytest.fixture
def nlp_and_stemmer():
    nlp, stemmer = init_model()
    return nlp, stemmer


def test_init_model(nlp_and_stemmer):
    nlp, stemmer = nlp_and_stemmer
    assert nlp is not None
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
    print(redacted_text)
    assert redacted_text == "█████████████████████████████████████"
    assert len(censored_terms) == 1
    assert censored_terms[0]["term"] == "This is a test. This is another line."


def test_redact_names(nlp_and_stemmer):
    nlp, _ = nlp_and_stemmer
    text = "John Doe went to the store."
    doc = nlp(text)

    censored_terms = []
    redacted_text = redact_names(text, doc, '█', censored_terms)

    assert 'John Doe' not in redacted_text
    assert len(censored_terms) == 1
    assert censored_terms[0]["term"] == "John Doe"


def test_redact_dates(nlp_and_stemmer):
    nlp, _ = nlp_and_stemmer
    text = "The event is on 2022-01-01."
    doc = nlp(text)

    censored_terms = []
    redacted_text = redact_dates(text, doc, '█', censored_terms)

    assert '2022-01-01' not in redacted_text


def test_redact_addresses(nlp_and_stemmer):
    nlp, _ = nlp_and_stemmer
    text = "Visit me at 3800 Southwest 34TH ST Gainesville"
    doc = nlp(text)

    censored_terms = []
    redacted_text = redact_addresses(text, doc, '█', censored_terms)
    print(redacted_text)
    assert '3800 Southwest 34TH ST Gainesville' not in redacted_text
    assert 'Visit me at ████ █████████ ████ ██ ███████████' == redacted_text


def test_redact_phones():
    text = "My phone number is +1 (555) 123-4567."
    censored_terms = []

    redacted_text = redact_phones(text, '█', censored_terms)

    assert '+1 (555) 123-4567' not in redacted_text
    assert len(censored_terms) == 1
    assert censored_terms[0]["term"] == "+1 (555) 123-4567"


def test_redact_file(nlp_and_stemmer, tmp_path):
    nlp, stemmer = nlp_and_stemmer
    input_file = tmp_path / "test_input.txt"
    input_file.write_text("This is a test file.")

    flags = MagicMock()
    flags.names = False
    flags.dates = False
    flags.phones = False
    flags.address = False
    flags.concept = ["test"]

    redacted_text, censored_terms = redact_file(input_file, flags, nlp, stemmer)

    assert 'test' not in redacted_text
    assert len(censored_terms) > 0


if __name__ == "__main__":
    pytest.main()
