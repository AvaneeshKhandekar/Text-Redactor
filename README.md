
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
This script redacts sensitive information from text documents. It uses the ```Presidio Analyzer and Anonymizer``` with spacy model configuration to identify and mask sensitive data, such as names, dates, phone numbers, and addresses.\
For addresses the script uses ```NLTK wordnet``` to get synonyms and hyponyms for the given concept words and redacts sentences based on the created set.\
The script can process multiple input files, generating redacted output files with the extension ```.censored```.

### Work Flow:
- Read input arguments.
- Initialize Presidio Analyzer with a Spacy model as its NLP engine for entity recognition.
- Initialize Porter Stemmer to get stems of words to be used in concept redaction.
- Based on the arguments check for entities like ```PERSON, DATE, PHONE_NUMBER, LOCATION, GPE, LOC, FAC```
- When an entity is found mask the entity using Presidio Anonymizer engine with the ```█``` character.
- Store censored terms with start and end index and entity type for stats file.
- Get related words for given concept words.
    - Get the stem of the concept word.
    - Add word stem in final set of related words.
    - Add all stemmed lemma names from the synonym set for the concept using wordnet.
    - Add all stemmed hyponym lemma names from the hyponyms present in the synset based on threshold of 0.938. (Words with WUP similarity greater than 0.93 are added)
    - Final set of related words is returned.
- Split the lines in the files and perform sentence tokenization.
- For each sentence, tokenize the words in it.
- For each token check if its stem matches anything in related word stems.
- If it matches redact the whole line.
- If it does not match add line as it is to result.
- Store censored lines with start and end index and entity type concept for stats file.
- Write redacted text to output file directory provided.
- Write redaction information to a stats file with given name.

### Functions
#### - `init_analyzer():`
   - Initializes the analyzer engine and the stemmer.
   - Downloads necessary NLTK resources.
   - Returns the initialized analyzer and stemmer.

#### - `get_related_word_stems(concept_words, stemmer, threshold=0.938):`
   - Takes a list of concept words and returns their stems along with related words (synonyms and hyponyms) from WordNet.
   - The `threshold` parameter defines the similarity cutoff for hyponyms.
   - Returns the set of related word stems.

#### - `redact_lines(lines, stemmer, related_word_stems, text, censored_terms):`
   - Takes a list of lines, tokenizes each line into words, stems them, and determines which lines contain related word stems.
   - Redacts the identified lines by replacing them with masked characters.
   - Returns list of processed lines.

#### - `concept_redaction(text, concept_words, stemmer=None):`
   - Performs concept-based redaction on the provided text.
   - Splits input by line.
   - Tokenizes sentences in a given line. 
   - Calls the get_related_word_stems function and the redact_lines function.
   - Returns the redacted text and a list of censored terms.

#### - `anonymize_text(text, analyzer, flags):`
   - Analyzes the text for sensitive entities based on specified arguments (name, phone, date, address) using Presidio.
   - Returns the anonymized text and a list of censored terms.

#### - `redact_file(input_file, flags, analyzer, stemmer):`
   - Reads an input file, applies anonymization and concept redaction, and returns the redacted text along with censored terms.
   - Returns redacted text and censored terms.

#### - `main():`
   - Entry point of the script that parses command-line arguments and starts the redaction process.

### Tests
#### - `test_init_analyzer(analyzer_and_stemmer):`
   - Function Tested: ```init_analyzer()```.
   - Verifies that the analyzer and stemmer are initialized correctly.
   - Asserts analyzer and stemmer are not None.

#### - `test_get_related_word_stems():`
   - Function Tested: ```get_related_word_stems(concept_words, stemmer, threshold=0.938)```.
   - Tests that related word stems are generated correctly from concept words.
   - Asserts a few words are part of final set given a concept word.

#### - `test_redact_lines():`
   - Function Tested: ```redact_lines(lines, stemmer, related_word_stems, text, censored_terms)```.
   - Confirms that lines containing sensitive terms are redacted properly.
   - Asserts that given a line it is redacted properly.

#### - `test_concept_redaction():`
   - Function Tested: ```concept_redaction(text, concept_words, stemmer=None)```.
   - Tests the concept redaction functionality to ensure it redacts the correct text.
   - Asserts the redacted sentence has sentences censored based on given concept.

#### - `test_anonymize_text(analyzer_and_stemmer):`
   - Function Tested: ```anonymize_text(text, analyzer, flags)```.
   - Validates that sensitive information is anonymized based on the specified flags.
   - Asserts that the given entities are redacted in the result text.

#### - `test_redact_file(analyzer_and_stemmer, tmp_path):`
   - Function Tested: ```redact_file(input_file, flags, analyzer, stemmer)```.
   - Checks the functionality of redacting content from a file and confirms output accuracy.
   - Asserts file is redacted and censored terms contain the relevant stats.

#### - `test_redact_lines_no_matching_stems():`
   - Function Tested: ```redact_lines(lines, stemmer, related_word_stems, text, censored_terms)```.
   - Confirms that safe lines are not altered.
   - Asserts that text is not redacted unnecessarily.

#### - `test_anonymize_text_no_flags(analyzer_and_stemmer):`
   - Function Tested: ```anonymize_text(text, analyzer, flags)```.
   - Checks that no changes are made when no flags are set for anonymization.
   - Asserts that text is not redacted unnecessarily.

### ASSUMPTIONS:
- **Model Dependency**: Accuracy of identifying entities largely depends on the spacy model used.
- **Language**: It is assumed that all text will be in standard English Language.
- **Concept Redaction**: It is assumed that only synonyms and certain hyponyms need to be redacted related to the concept based on WUP similarity threshold of 0.938.

### BUGS:
- **Name Redaction**: Spacy model missed some names in the text like where only first name is given and names in email addresses.




