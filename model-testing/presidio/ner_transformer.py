from transformers import AutoTokenizer, AutoModelForTokenClassification
from huggingface_hub import snapshot_download
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine.transformers_nlp_engine import TransformersNlpEngine
from presidio_analyzer.nlp_engine.ner_model_configuration import NerModelConfiguration
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, RecognizerRegistry, Pattern
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer


transformers_model = "StanfordAIMI/stanford-deidentifier-base"

snapshot_download(repo_id=transformers_model)

AutoTokenizer.from_pretrained(transformers_model)
AutoModelForTokenClassification.from_pretrained(transformers_model)

# Transformer model config
model_config = [
    {"lang_code": "en",
     "model_name": {
         "spacy": "en_core_web_sm", # for tokenization
         "transformers": "StanfordAIMI/stanford-deidentifier-base" # for NER
    }
}]

# Entity mappings
mapping = dict(
    PER="PERSON",
    LOC="LOCATION",
    ORG="ORGANIZATION",
    AGE="AGE",
    ID="ID",
    EMAIL="EMAIL",
    DATE="DATE_TIME",
    PHONE="PHONE_NUMBER",
    PERSON="PERSON",
    LOCATION="LOCATION",
    GPE="LOCATION",
    ORGANIZATION="ORGANIZATION",
    NORP="NRP",
    PATIENT="PERSON",
    STAFF="PERSON",
    HOSP="LOCATION",
    PATORG="ORGANIZATION",
    TIME="DATE_TIME",
    HCW="PERSON",
    HOSPITAL="LOCATION",
    FACILITY="LOCATION",
    VENDOR="ORGANIZATION",
)

labels_to_ignore = ["O"]

# NER
ner_model_configuration = NerModelConfiguration(
    model_to_presidio_entity_mapping=mapping,
    alignment_mode="expand", # "strict", "contract", "expand"
    aggregation_strategy="max", # "simple", "first", "average", "max"
    labels_to_ignore = labels_to_ignore)

transformers_nlp_engine = TransformersNlpEngine(
    models=model_config,
    ner_model_configuration=ner_model_configuration)

transformers_nlp_engine.load()

# recognizers
def get_titles_recognizer():
    titles_recognizer = PatternRecognizer(deny_list=["Mr.", "Mrs.", "Ms.", "Miss", "Dr.", "Prof.", "manager"],
                                          supported_entity="TITLE", name="TitlesRecognizer")
    return titles_recognizer

def get_location_deny_list():
    location_deny_list = PatternRecognizer(deny_list=["APO", "PSC", "AA", "Cyprus (Greek)", 
                                                      "ul", "AE", "DPO", "AP", "nan"],
                                          supported_entity="LOCATION", name="LocationDenylist")
    return location_deny_list

def get_age_recognizer():
    weak_regex= r"\b(110|[1-9]?[0-9])\b"
    age_pattern = Pattern(name="age (very weak)", 
                          regex=weak_regex, 
                          score=0.01)
    age_recognizer = PatternRecognizer(
        supported_entity="AGE",
        patterns = [age_pattern],
        name="AgeRecognizer",
        context=["month", "old", "turn", "age", "y/o"]
    )
    return age_recognizer

def get_zipcode_recognizer():
    weak_regex = r"\b\d{3,5}(?:-\d{3})?\b"
    med_regex = r"""
    (?:                           # Non-capturing group for matching
        (?:zip(?:code)?.{0,10})|  # Matches 'zip' or 'zipcode' with up to 10 non-alphanumeric characters
        (?:[A-Z]{2}\s)            # Matches a two-letter state acronym followed by a space
    )                             # End of non-capturing group
    (\d{3,7}(?:-\d{3})?)          # Captures 3 to 7 digits for the zip code, optionally followed by a dash and 3 more digits
    """ # weak regex pattern
    zipcode_pattern_weak = Pattern(name="zip code (weak)", regex=weak_regex, score=0.01)
    zipcode_pattern_med = Pattern(name="zip code (medium)", regex=med_regex, score=0.4)


    # Define the recognizer with the defined pattern
    zipcode_recognizer = PatternRecognizer(
        supported_entity="ZIP_CODE", 
        patterns=[zipcode_pattern_weak, zipcode_pattern_med], 
        name="ZipCodeRecognizer", 
        context=["zip", "zipcode"]
    )
    return zipcode_recognizer

registry = RecognizerRegistry()
registry.load_predefined_recognizers(nlp_engine=transformers_nlp_engine)
registry.add_recognizer(get_titles_recognizer())
registry.add_recognizer(get_zipcode_recognizer())
registry.add_recognizer(get_location_deny_list())
registry.add_recognizer(get_age_recognizer())

# remove unnecessary recognizers
unnecessary = ['NhsRecognizer', 'UkNinoRecognizer', 'SgFinRecognizer', 'AuAbnRecognizer', 
               'AuAcnRecognizer','AuTfnRecognizer', 'AuMedicareRecognizer', 'InPanRecognizer',
               'InAadhaarRecognizer', 'InVehicleRegistrationRecognizer', 'InPassportRecognizer', 
               'InVoterRecognizer']

for rec in unnecessary:
    registry.remove_recognizer(rec)

# context aware enhancer
context_enhancer = LemmaContextAwareEnhancer(
    context_prefix_count=10, 
    context_suffix_count=10
    )

analyzer = AnalyzerEngine(
    nlp_engine=transformers_nlp_engine, 
    context_aware_enhancer=context_enhancer,
    registry=registry, 
    default_score_threshold=0.3
    )
