from transformers import AutoTokenizer, AutoModelForTokenClassification
from huggingface_hub import snapshot_download
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine.transformers_nlp_engine import TransformersNlpEngine
from presidio_analyzer.nlp_engine.ner_model_configuration import NerModelConfiguration
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, RecognizerRegistry, Pattern
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer
from recognizers import MedicalRecognizers

# Configure Presidio Analyzer models
def config(modelA, modelA_mapping, 
           labels_to_ignore, recognizers, context_enhancer, 
           modelB=None, modelB_mapping=None, use_B=False):

    unnecessary = ['NhsRecognizer', 'UkNinoRecognizer', 'SgFinRecognizer', 'AuAbnRecognizer', 
                'AuAcnRecognizer','AuTfnRecognizer', 'AuMedicareRecognizer', 'InPanRecognizer',
                'InAadhaarRecognizer', 'InVehicleRegistrationRecognizer', 'InPassportRecognizer', 
                'InVoterRecognizer']
    
    analyzers = []
    models = [(modelA, modelA_mapping), (modelB, modelB_mapping)] if use_B else [(modelA, modelA_mapping)]

    for m in models:

        model, mapping = m

        model_config = [
        {
            "lang_code": "en",
            "model_name": {
                "spacy": "en_core_web_sm", # for tokenization
                "transformers": model # for NER
                }
            }
        ]

        # NER
        ner_model_configuration = NerModelConfiguration(
            model_to_presidio_entity_mapping=mapping,
            alignment_mode="expand", # "strict", "contract", "expand"
            aggregation_strategy="first", # "simple", "first", "average", "max"
            labels_to_ignore = labels_to_ignore,
            low_score_entity_names=[])
        

        nlp_engine = TransformersNlpEngine(
            models=model_config,
            ner_model_configuration=ner_model_configuration)
        

        nlp_engine.load()

        registry = RecognizerRegistry(supported_languages=["en"])
        registry.load_predefined_recognizers(languages=["en"], nlp_engine=nlp_engine)

        for func in recognizers:
            registry.add_recognizer(func)

        for rec in unnecessary:
            registry.remove_recognizer(rec)

        analyzer = AnalyzerEngine(
            nlp_engine=nlp_engine, 
            context_aware_enhancer=context_enhancer,
            registry=registry, 
            default_score_threshold=0.505
            )
        
        analyzers.append(analyzer)

    return analyzers
    
def build_analyzer(dual_model=False):
    # Load transformer models from huggingface
    stanford_model = "StanfordAIMI/stanford-deidentifier-base"
    snapshot_download(repo_id=stanford_model)
    AutoTokenizer.from_pretrained(stanford_model)
    AutoModelForTokenClassification.from_pretrained(stanford_model)

    if dual_model:
        ab_ai_model = "ab-ai/pii_model"
        snapshot_download(repo_id=ab_ai_model)
        AutoTokenizer.from_pretrained(ab_ai_model)
        AutoModelForTokenClassification.from_pretrained(ab_ai_model)
        # Entity mappings
        abai_mapping = dict(
            FIRSTNAME="PERSON",
            MIDDLENAME="PERSON",
            LASTNAME="PERSON",
            PREFIX="TITLE",

            EMAIL="EMAIL",
            PHONENUMBER="PHONE_NUMBER",
            URL="URL",

            DOB="DATE_TIME",
            DATE="DATE_TIME",
            AGE="AGE",

            STREET="LOCATION",
            BUILDINGNUMBER="LOCATION",
            SECONDARYADDRESS="LOCATION",
            CITY="LOCATION",
            STATE="LOCATION",
            ZIPCODE="LOCATION",
            COUNTY="LOCATION",

            COMPANYNAME="ORGANIZATION",

            ACCOUNTNUMBER="ID",
            ACCOUNTNAME="ID",
            SSN="US_SSN",
            IBAN="ID",
            PIN="ID",
            USERNAME="ID",
            PASSWORD="ID", 
            CREDITCARDNUMBER="CREDIT_CARD",
            CREDITCARDCVV="CREDIT_CARD",
            CREDITCARDISSUER="ORGANIZATION",

            # GENDER="NRP",  # optional; depends on your policy
            # SEX="NRP",     # optional; depends on your policy
            # AMOUNT="MONEY",
        )
    else:
        ab_ai_model = None
        abai_mapping = None

    stanford_mapping = dict(
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
    context_enhancer = LemmaContextAwareEnhancer(
            context_prefix_count=10, 
            context_suffix_count=10
            )

    recognizers = MedicalRecognizers.get_all_recognizers()
    transformer_models = config(stanford_model, stanford_mapping, 
           labels_to_ignore, recognizers, context_enhancer, 
           ab_ai_model, abai_mapping, dual_model)
    return transformer_models

stanford_model = build_analyzer(dual_model=False)[0]
