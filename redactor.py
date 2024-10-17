import argparse
import glob
import os
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine, OperatorConfig
from presidio_analyzer.nlp_engine import NlpEngineProvider
import nltk
from nltk.corpus import wordnet as wn
from nltk.stem import PorterStemmer


def init_analyzer():
    nltk.download('punkt')
    nltk.download('punkt_tab')
    nltk.download('wordnet')
    stemmer = PorterStemmer()
    configuration = {"nlp_engine_name": "spacy", "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}]}
    provider = NlpEngineProvider(nlp_configuration=configuration)
    nlp_engine = provider.create_engine()
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=['en'])
    return analyzer, stemmer


def get_related_words(concept_words, stemmer):
    related_words = set(concept_words)

    for word in concept_words:
        for syn in wn.synsets(word):
            for lemma in syn.lemmas():
                related_words.add(lemma.name().lower())
                related_words.add(stemmer.stem(lemma.name().lower()))
        if word.endswith('s'):
            singular = word[:-1]
            related_words.add(singular)
            related_words.add(stemmer.stem(singular))
        else:
            plural = word + 's'
            related_words.add(plural)
            related_words.add(stemmer.stem(plural))

    return related_words


def concept_redaction(text, concept_words, stemmer):
    sentences = nltk.sent_tokenize(text)
    related_words = get_related_words(concept_words, stemmer)
    redacted_text = text
    censored_terms = []

    for sentence in sentences:
        tokens = nltk.word_tokenize(sentence)
        redacted_sentence = []

        for i, token in enumerate(tokens):
            if token.lower() in related_words:
                redacted_token = "*" * len(token)
                redacted_sentence.append(redacted_token)
                start_index = text.find(token, redacted_text.index(sentence))
                end_index = start_index + len(token) - 1
                censored_terms.append({"term": token, "start": start_index, "end": end_index, "type": "CONCEPT"})

            else:
                redacted_sentence.append(token)

        new_sentence = ' '.join(redacted_sentence)
        redacted_text = redacted_text.replace(sentence, new_sentence)

    return redacted_text, censored_terms


def anonymize_text(text, analyzer, flags):
    entities = []
    if flags.names:
        entities.append("PERSON")
    if flags.dates:
        entities.append("DATE_TIME")
    if flags.phones:
        entities.append("PHONE_NUMBER")
    if flags.address:
        entities.append("LOCATION")

    operators = {}
    for entity in entities:
        operators[entity] = OperatorConfig("mask", {"masking_char": "*", "chars_to_mask": 100, "from_end": False})

    analyzer_results = analyzer.analyze(text=text, entities=entities, language='en')

    anonymizer = AnonymizerEngine()
    anonymized_result = anonymizer.anonymize(text=text, analyzer_results=analyzer_results, operators=operators)

    censored_terms = []
    for result in analyzer_results:
        start_index = result.start
        end_index = result.end - 1
        term = text[start_index:end_index + 1]
        censored_terms.append({"term": term, "start": start_index, "end": end_index, "type": result.entity_type})

    return anonymized_result.text, censored_terms


def redact_file(input_file, flags, analyzer, stemmer):
    with open(input_file, 'r') as file:
        text = file.read()

    censored_terms = []

    if flags.names or flags.dates or flags.phones or flags.address:
        text, terms = anonymize_text(text, analyzer, flags)
        censored_terms.extend(terms)

    if flags.concept:
        text, terms = concept_redaction(text, flags.concept, stemmer)
        censored_terms.extend(terms)

    return text, censored_terms


def main():
    parser = argparse.ArgumentParser(description='Text Redactor')
    parser.add_argument('--input', required=True, help='Input files pattern (e.g. *.txt)')
    parser.add_argument('--names', action='store_true', help='Anonymize names')
    parser.add_argument('--dates', action='store_true', help='Anonymize dates')
    parser.add_argument('--phones', action='store_true', help='Anonymize phone numbers')
    parser.add_argument('--address', action='store_true', help='Anonymize addresses')
    parser.add_argument('--concept', action='append', help='Redact specific concepts (multiple concepts can be passed)',
                        required=True)
    parser.add_argument('--output', required=True, help='Output directory')
    parser.add_argument('--stats', help='Output anonymization stats file path')

    args = parser.parse_args()

    analyzer, stemmer = init_analyzer()

    input_files = sorted(glob.glob(args.input))

    if not os.path.exists(args.output):
        os.makedirs(args.output)

    stats = []

    for input_file in input_files:
        redacted_text, censored_terms = redact_file(input_file, args, analyzer, stemmer)
        output_file = os.path.join(args.output, os.path.basename(input_file)+'.censored')

        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(redacted_text)

        term_counts = {}
        for term in censored_terms:
            term_type = term["term"].lower()
            term_counts[term_type] = term_counts.get(term_type, 0) + 1

        stats.append(f"Processed file: {input_file}\n")
        stats.append(f"Censored Terms Count: {len(censored_terms)}\n")

        for term, count in term_counts.items():
            stats.append(f"Term: {term}, Count: {count}\n")
            for censored in censored_terms:
                if censored["term"].lower() == term:
                    stats.append(
                        f"  - Censored Term: {censored['term']}, Start Index: {censored['start']}, End Index: {censored['end']}, Type: {censored['type']}\n")

    if args.stats:
        with open(args.stats, 'w', encoding='utf-8') as stats_file:
            stats_file.writelines(stats)


if __name__ == '__main__':
    main()
