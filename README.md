# Text Redactor

## AUTHOR

Avaneesh Khandekar

## INSTALLATION

To install the required dependencies:

```bash
pipenv install
```

## USAGE

To redact sensitive information from specified input files:

```bash
pipenv run python redactor.py --input <input_file_pattern> --output <output_directory> --names --dates --phones --address [--concept <concepts>] --stats <stats_file_path> 
```

Required:

``` 
- <input_file_pattern> -> Example: '*.txt' for all text files.
- <output_directory> -> Example: /files to create a folder called 
                        files for redacted files.
```

Optional:

```
- --names -> Redact names in given file
- --dates -> Redact dates in given file
- --phones -> Redact phone numbers in given file
- --address -> Redact addresses in given file
- --concept -> Redact all sentences containing words related to 
               given concept word. Can chain multiple concepts like 
               --concept house --concept bike
- --stats -> Create a stats file containing redaction information
```

## OVERVIEW

This script redacts sensitive information from text documents. It uses the ```Spacy``` library with pre-trained models
for NER along with ```Regular Expression``` to identify and mask sensitive data, such as names, dates, phone numbers,
and addresses.\
The concept flag redacts all portions of text that have anything to do with a particular concept.
For redacting concepts the script uses ```NLTK wordnet``` to get synonyms and hyponyms for the given concept words and
redacts sentences based on the created set.\
The script can process multiple input files, generating redacted output files with the extension ```.censored```.

### Work Flow:

- Read input arguments.
- Initialize a Spacy model for entity recognition.
- Initialize Porter Stemmer to get stems of words to be used in concept redaction.
- Based on the arguments check for entities like ```PERSON, DATE, PHONE_NUMBER, LOCATION, GPE, LOC, FAC``` using Spacy's
  NER model.
- Additionally, use regex to cover some corner cases missed my Spacy and redact combined results from regex and speacy.
- Store censored terms with start and end index and entity type for stats file.
- Get related words for given concept words.
    - Get the stem of the concept word.
    - Add word stem in final set of related words.
    - Add all stemmed lemma names from the synonym set for the concept using wordnet.
    - Add all stemmed hyponym lemma names from the hyponyms present in the synset based on threshold of 0.938. (Words
      with WUP similarity greater than 0.93 are added)
    - Final set of related words is returned.
- Split the lines in the files and perform sentence tokenization.
- For each sentence, tokenize the words in it.
- For each token check if its stem matches anything in related word stems.
- If it matches redact the whole line.
- If it does not match add line as it is to result.
- Store censored lines with start and end index and entity type concept for stats file.
- Write redacted text to output file directory provided.
- Write redaction information to a stats file with given name.

### Stats File

- The stats file summarizes the processing of input files during the redaction operation.
- It includes details such as the file name, total count of censored terms, and for each term, the number of occurrences
  along with their start and end indices in the text.
- It provides transparency about how sensitive information was handled.

### Functions

#### - `init_model():`

- Initializes the Spacy model and the Porter Stemmer.
- DDownloads necessary NLTK resources.
- Returns the initialized NLP model and stemmer.

#### - `get_related_word_stems(concept_words, stemmer, threshold=0.938):`

- Takes a list of concept words and returns their stems along with related words (synonyms and hyponyms) from WordNet.
- The `threshold` parameter defines the similarity cutoff for hyponyms.
- Returns the set of related word stems.

#### - `redact_lines(lines, stemmer, related_word_stems, text, censored_terms):`

- Takes a list of lines, tokenizes each line into words, stems them, and determines which lines contain related word
  stems.
- Redacts the identified lines by replacing them with masked characters.
- Returns list of processed lines.

#### - `concept_redaction(text, concept_words, stemmer=None):`

- Performs concept-based redaction on the provided text.
- Splits input by line.
- Tokenizes sentences in a given line.
- Calls the get_related_word_stems function and the redact_lines function.
- Returns the redacted text and a list of censored terms.

#### - `redact_names(text, doc, redaction_char, censored_terms):`

- Redacts names identified in the text using the provided NLP model and regular expressions.
- Returns the redacted text.

#### - `redact_dates(text, doc, redaction_char, censored_terms):`

- Redacts dates identified in the text using the provided NLP model and regular expressions.
- Returns the redacted text.

#### - `redact_addresses(text, doc, redaction_char, censored_terms):`

- Redacts addresses identified in the text using the provided NLP model and regular expressions.
- Returns the redacted text.

#### - `redact_phones(text, redaction_char, censored_terms):`

- Redacts phone numbers identified in the text using regex.
- Returns the redacted text.

#### - `redact_file(input_file, flags, nlp, stemmer):`

- Reads an input file, applies PII redaction and concept redaction, and returns the redacted text along with censored
  terms.
- Returns redacted text and censored terms.

#### - `main():`

- Entry point of the script that parses command-line arguments and starts the redaction process.
- Also, writes the output censored file and stats file

### Tests

#### - `test_init_model(nlp_and_stemmer):`

- Function Tested: ```init_model()```.
- Verifies that the analyzer and stemmer are initialized correctly.
- Asserts that both the NLP model and stemmer are not None.

#### - `test_get_related_word_stems():`

- Function Tested: ```get_related_word_stems(concept_words, stemmer, threshold=0.938)```.
- Verifies that the NLP model and stemmer are initialized correctly.
- Asserts that the expected words are part of the final set given the input concept words.

#### - `test_redact_lines():`

- Function Tested: ```redact_lines(lines, stemmer, related_word_stems, text, censored_terms)```.
- Verifies that lines containing sensitive terms are redacted properly.
- Asserts that the sensitive line is correctly redacted.

#### - `test_concept_redaction():`

- Function Tested: ```concept_redaction(text, concept_words, stemmer=None)```.
- Verifies the concept redaction functionality to ensure it redacts the correct text.
- Asserts that the redacted sentence contains the correct censored terms based on the given concepts.

#### - `test_redact_names(nlp_and_stemmer):`

- Function Tested: ```redact_names(text, doc, symbol, censored_terms)```.
- Verifies that names are redacted from the text.
- Asserts that the name is not present in the redacted text and that it is recorded in the censored terms.

#### - `test_redact_dates(nlp_and_stemmer):`

- Function Tested: ```redact_dates(text, doc, symbol, censored_terms)```.
- Verifies that dates are redacted correctly from the text.
- Asserts that the date is not present in the redacted text and that it is recorded in the censored terms.

#### - `test_redact_addresses(nlp_and_stemmer):`

- Function Tested: ```redact_addresses(text, doc, symbol, censored_terms)```.
- Verifies that addresses are redacted accurately from the text.
- Asserts that the address is not present in the redacted text and that it is recorded in the censored terms.

#### - `test_redact_phones():`

- Function Tested: ```redact_phones(text, symbol, censored_terms)```.
- Verifies that phone numbers are redacted properly from the text
- Asserts that the phone number is not present in the redacted text and that it is recorded in the censored terms.

#### - `test_redact_file(nlp_and_stemmer, tmp_path):`

- Function Tested: ```redact_file(input_file, flags, nlp, stemmer```.
- Verifies the functionality of redacting content from a file and confirms output accuracy.
- Asserts that the file is redacted appropriately and that the censored terms contain the relevant information.

### ASSUMPTIONS:

- **Model Dependency**: Accuracy of identifying entities largely depends on the spacy model used.
- **Language**: It is assumed that all text will be in standard English Language.
- **Concept Redaction**: It is assumed that only synonyms and certain hyponyms need to be redacted related to the
  concept based on WUP similarity threshold of 0.938.

### BUGS:

- **Name Redaction**: Spacy model missed some names in the text like where only first name is given and names in email
  addresses.
- **Address Redaction**: Spacy is very bad in recognizing street addresses, the regex added does not cover all patterns
  of addresses.




