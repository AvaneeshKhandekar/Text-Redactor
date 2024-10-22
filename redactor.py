import argparse
import glob
import os

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine, OperatorConfig
from presidio_analyzer.nlp_engine import NlpEngineProvider
import nltk
from nltk.corpus import wordnet as wn
from nltk.stem import PorterStemmer


def init_analyzer(model="en_core_web_trf"):
    nltk.download('punkt')
    nltk.download('punkt_tab')
    nltk.download('wordnet')
    stemmer = PorterStemmer()
    configuration = {"nlp_engine_name": "spacy", "models": [{"lang_code": "en", "model_name": model}]}

    provider = NlpEngineProvider(nlp_configuration=configuration)
    nlp_engine = provider.create_engine()
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=['en'])
    return analyzer, stemmer


def get_related_word_stems(concept_words, stemmer, threshold=0.938):
    related_word_stems = set()

    for word in concept_words:
        word_stem = stemmer.stem(word.lower())
        related_word_stems.add(word_stem)

        for synset in wn.synsets(word):
            for lemma in synset.lemmas():
                related_word_stems.add(stemmer.stem(lemma.name().replace('_', ' ').lower()))

            for hyponym in synset.hyponyms():
                if synset.wup_similarity(hyponym) >= threshold:
                    for lemma in hyponym.lemmas():
                        related_word_stems.add(stemmer.stem(lemma.name().replace('_', ' ').lower()))

        related_word_stems.add(stemmer.stem(word))

        if word.endswith('s'):
            related_word_stems.add(stemmer.stem(word[:-1]))
        else:
            related_word_stems.add(stemmer.stem(word + 's'))

    return related_word_stems


def redact_lines(lines, stemmer, related_word_stems, text, censored_terms):
    result = []

    for line in lines:
        tokens = nltk.word_tokenize(line)
        redact_line = False

        for token in tokens:
            stemmed_token = stemmer.stem(token.lower())
            if stemmed_token in related_word_stems:
                redact_line = True
                break

        if redact_line:
            start_index = text.find(line)
            end_index = start_index + len(line) - 1
            censored_terms.append({
                "term": line.strip(),
                "start": start_index,
                "end": end_index,
                "type": "CONCEPT"
            })
            result.append("█" * len(line))
        else:
            result.append(line)
    return result


def concept_redaction(text, concept_words, stemmer=None):
    if stemmer is None:
        stemmer = PorterStemmer()

    lines = text.splitlines(keepends=True)
    related_word_stems = get_related_word_stems(concept_words, stemmer)
    censored_terms = []
    redacted_lines = []
    for line in lines:
        sentences = nltk.sent_tokenize(line)
        redacted_sentences = redact_lines(sentences, stemmer, related_word_stems, text, censored_terms)

        redacted_line = ' '.join(redacted_sentences).strip()
        redacted_lines.append(redacted_line + line[len(line.rstrip()):])

    redacted_text = ''.join(redacted_lines)
    return redacted_text, censored_terms


def anonymize_text(text, analyzer, flags):
    entities = []
    if flags.names:
        entities.append("PERSON")
    if flags.dates:
        entities.append("DATE")
    if flags.phones:
        entities.append("PHONE_NUMBER")
    if flags.address:
        entities.extend(["LOCATION", "GPE", "LOC", "FAC"])

    operators = {}
    for entity in entities:
        operators[entity] = OperatorConfig("mask", {"masking_char": "█", "chars_to_mask": 50, "from_end": False})

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
    parser.add_argument('--input', required=True, help='Input files pattern')
    parser.add_argument('--names', action='store_true', help='Redact names')
    parser.add_argument('--dates', action='store_true', help='Redact dates')
    parser.add_argument('--phones', action='store_true', help='Redact phone numbers')
    parser.add_argument('--address', action='store_true', help='Redact addresses')
    parser.add_argument('--concept', action='append', help='Redact specific concepts (multiple concepts can be passed)',
                        required=False)
    parser.add_argument('--output', required=True, help='Output directory')
    parser.add_argument('--stats', help='Output redaction stats file path')

    args = parser.parse_args()

    analyzer, stemmer = init_analyzer()

    input_files = sorted(glob.glob(args.input))

    if not os.path.exists(args.output):
        os.makedirs(args.output)

    stats = []

    for input_file in input_files:
        redacted_text, censored_terms = redact_file(input_file, args, analyzer, stemmer)
        output_file = os.path.join(args.output, os.path.basename(input_file) + '.censored')

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
                        f"  - Start Index: {censored['start']}, End Index: {censored['end']}, Type: {censored['type']}\n")

    if args.stats:
        with open(args.stats, 'w', encoding='utf-8') as stats_file:
            stats_file.writelines(stats)


if __name__ == '__main__':
    main()
