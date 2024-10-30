import argparse
import glob
import os
import re
import sys

import nltk
import usaddress
from nltk.corpus import wordnet as wn
from nltk.stem import PorterStemmer
import en_core_web_lg


def init_model():
    nltk.download('punkt')
    nltk.download('punkt_tab')
    nltk.download('wordnet')
    stemmer = PorterStemmer()
    nlp = en_core_web_lg.load()
    return nlp, stemmer


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
        redact_line = False
        tokens = nltk.word_tokenize(line)

        for token in tokens:
            stemmed_token = stemmer.stem(token.lower())
            if stemmed_token in related_word_stems:
                redact_line = True
                break

        if redact_line:
            redacted_line = ""

            for char in line:
                if char == '\n':
                    redacted_line += '\n'
                elif char == '\t':
                    redacted_line += '\t'
                else:
                    redacted_line += '█'

            censored_terms.append({
                "term": line.strip(),
                "start": text.find(line),
                "end": text.find(line) + len(line) - 1,
                "type": "CONCEPT"
            })
            result.append(redacted_line)
        else:
            result.append(line)

    return result


def concept_redaction(text, concept_words, stemmer):
    lines = text.splitlines(keepends=True)

    header_lines = []
    body_lines = []
    body_started = False

    for line in lines:
        if body_started:
            body_lines.append(line)
        else:
            if line.strip() == "":
                body_started = True
            else:
                header_lines.append(line)

    headers = ''.join(header_lines)

    related_word_stems = get_related_word_stems(concept_words, stemmer)
    censored_terms = []

    redacted_header_lines = redact_lines(header_lines, stemmer, related_word_stems, headers, censored_terms)

    body_text = ''.join(body_lines)
    sentences = nltk.sent_tokenize(body_text)

    redacted_sentences = redact_lines(sentences, stemmer, related_word_stems, body_text, censored_terms)

    redacted_body_text = ' '.join(redacted_sentences)

    return ''.join(redacted_header_lines) + redacted_body_text, censored_terms


def redact_names(text, doc, redaction_char, censored_terms):
    email_pattern = r'([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})'
    text = re.sub(email_pattern, lambda match: ' '.join(match.group(1).split('.')) + ' @' + match.group(2), text)

    for ent in doc.ents:
        if ent.label_ == 'PERSON':
            redacted_text = redaction_char * len(ent.text)
            text = text.replace(ent.text, redacted_text)
            censored_terms.append({
                "term": ent.text,
                "start": ent.start_char,
                "end": ent.end_char,
                "type": "PERSON"
            })
    return text


def redact_dates(text, doc, redaction_char, censored_terms):
    date_pattern = re.compile(
        r'(?:(?<!\:)(?<!\:\d)[0-3]?\d(?:st|nd|rd|th)?\s+(?:of\s+)?'
        r'(?:jan\.?|january|feb\.?|february|mar\.?|march|apr\.?|april|may|jun\.?|june|jul\.?|july|aug\.?|august|'
        r'sep\.?|september|oct\.?|october|nov\.?|november|dec\.?|december)|'
        r'(?:jan\.?|january|feb\.?|february|mar\.?|march|apr\.?|april|may|jun\.?|june|jul\.?|july|aug\.?|august|'
        r'sep\.?|september|oct\.?|october|nov\.?|november|dec\.?|december)\s+(?<!\:)(?<!\:\d)[0-3]?\d(?:st|nd|rd|th)?)'
        r'(?:\,)?\s*(?:\d{4})?|[0-3]?\d[-\./][0-3]?\d[-\./]\d{2,4}',
        re.IGNORECASE
    )
    for match in date_pattern.finditer(text):
        redacted_text = redaction_char * len(match.group())
        start, end = match.span()
        text = text[:start] + redacted_text + text[end:]
        censored_terms.append({
            "term": match.group(),
            "start": start,
            "end": end,
            "type": "DATE"
        })

    for ent in doc.ents:
        if ent.label_ == 'DATE':
            redacted_text = redaction_char * len(ent.text)
            text = text.replace(ent.text, redacted_text)
            censored_terms.append({
                "term": ent.text,
                "start": ent.start_char,
                "end": ent.end_char,
                "type": "DATE"
            })

    return text


def redact_addresses(text, doc, redaction_char, censored_terms):
    for ent in doc.ents:
        if ent.label_ in ['GPE', 'LOC', 'FAC']:
            redacted_text = redaction_char * len(ent.text)
            text = text.replace(ent.text, redacted_text)
            censored_terms.append({
                "term": ent.text,
                "start": ent.start_char,
                "end": ent.end_char,
                "type": ent.label_
            })

    datetime_regex = r'\b\d{1,2}:\d{2}:\d{2}'
    address_entities = usaddress.parse(text)
    for addr_entity in address_entities:
        term, label = addr_entity
        if re.fullmatch(datetime_regex, term):
            continue
        if label in ['AddressNumber', 'StreetName', 'StreetNamePostType', 'StreetNamePreDirectional', 'OccupancyType',
                     'OccupancyIdentifier',
                     'PlaceName', 'StateName', 'ZipCode']:
            start_idx = text.find(term)
            if start_idx != -1:
                end_idx = start_idx + len(term)
                redacted_text = redaction_char * len(term)
                text = text[:start_idx] + redacted_text + text[end_idx:]
                censored_terms.append({
                    "term": term,
                    "start": start_idx,
                    "end": end_idx,
                    "type": label
                })

    street_address_pattern = re.compile('\d{1,4} [\w\s]{1,20}(?:street|st|avenue|ave|road|rd|highway|hwy|square|sq|trail|trl|drive|dr|court|ct|park|parkway|pkwy|circle|cir|boulevard|blvd)\W?(?=\s|$)', re.IGNORECASE)
    po_box_pattern = re.compile(r'P\.? ?O\.? Box \d+', re.IGNORECASE)
    zip_code_pattern = re.compile(r'\b\d{5}(?:[-\s]\d{4})?\b')

    for pattern, label in [(street_address_pattern, "STREET_ADDRESS"),
                           (po_box_pattern, "PO_BOX"),
                           (zip_code_pattern, "ZIP_CODE")]:
        matches = pattern.finditer(text)
        for match in matches:
            term = match.group()
            redacted_text = redaction_char * len(term)
            text = text.replace(term, redacted_text)
            censored_terms.append({
                "term": term,
                "start": match.start(),
                "end": match.end(),
                "type": label
            })

    return text


def redact_phones(text, redaction_char, censored_terms):
    phone_pattern = re.compile('''((?:(?<![\d-])(?:\+?\d{1,3}[-.\s*]?)?(?:\(?\d{3}\)?[-.\s*]?)?\d{3}[-.\s*]?\d{4}(?![\d-]))|(?:(?<![\d-])(?:(?:\(\+?\d{2}\))|(?:\+?\d{2}))\s*\d{2}\s*\d{3}\s*\d{4}(?![\d-])))''')
    matches = re.finditer(phone_pattern, text)

    for match in matches:
        term = match.group()
        redacted_text = redaction_char * len(term)
        text = text.replace(term, redacted_text)
        censored_terms.append({
            "term": term,
            "start": match.start(),
            "end": match.end(),
            "type": "PHONE"
        })

    return text


def redact_file(input_file, flags, nlp, stemmer):
    with open(input_file, 'r') as file:
        text = file.read()

    censored_terms = []
    redaction_char = '█'

    doc = nlp(text)

    if flags.names:
        text = redact_names(text, doc, redaction_char, censored_terms)

    if flags.dates:
        text = redact_dates(text, doc, redaction_char, censored_terms)

    if flags.address:
        text = redact_addresses(text, doc, redaction_char, censored_terms)

    if flags.phones:
        text = redact_phones(text, redaction_char, censored_terms)

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

    nlp, stemmer = init_model()

    input_files = sorted(glob.glob(args.input))

    if not os.path.exists(args.output):
        os.makedirs(args.output)

    stats = []

    for input_file in input_files:
        redacted_text, censored_terms = redact_file(input_file, args, nlp, stemmer)
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
        if args.stats.lower() == 'stdout':
            sys.stdout.writelines(stats)
        elif args.stats.lower() == 'stderr':
            sys.stderr.writelines(stats)
        else:
            with open(args.stats, 'w', encoding='utf-8') as stats_file:
                stats_file.writelines(stats)


if __name__ == "__main__":
    main()
