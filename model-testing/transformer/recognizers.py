from presidio_analyzer import PatternRecognizer, Pattern, RecognizerRegistry
# from configurations import BERT_DEID_CONFIGURATION, STANFORD_COFIGURATION
# from transformers_recognizer import TransformersRecognizer
from presidio_analyzer import PatternRecognizer, Pattern
from typing import List

# A collection of custom recognizers to be used by the AnalyzerEngines

class MedicalRecognizers:
    """
    Factory class for creating all medical-specific entity recognizers.
    These recognizers are designed to identify PII in medical records while
    avoiding false positives with clinical data.
    """
    
    @staticmethod
    def get_mrn_recognizer() -> PatternRecognizer:
        """
        Medical Record Number recognizer.
        Detects MRN with or without label.
        
        Examples:
        - "MRN: 12345678"
        - "MRN 12345678"
        - "MR# 12345678"
        """
        return PatternRecognizer(
            supported_entity="MRN",
            patterns=[
                # MRN with label (high confidence)
                Pattern(
                    "MRN_LABELED",
                    r"(?:MRN|MR#|Medical Record Number):?\s*\d{6,10}",
                    0.95
                ),
                # Standalone 8-digit number (lower confidence, context-dependent)
                Pattern(
                    "MRN_STANDALONE", 
                    r"(?<!\d)\d{8}(?!\d)",
                    0.5  # Lower confidence to avoid false positives
                )
            ],
            context=["medical record", "patient", "MRN"]
        )
    
    @staticmethod
    def get_dob_recognizer() -> PatternRecognizer:
        """
        Date of Birth recognizer.
        Only captures the date portion, not the "DOB:" label.
        
        Examples:
        - "DOB: 3-5-1981" → captures "3-5-1981"
        - "DOB:  12/25/1990" → captures "12/25/1990"
        - "Date of Birth: 1-1-85" → captures "1-1-85"
        """
        return PatternRecognizer(
            supported_entity="DATE_TIME",
            patterns=[
                # Lookbehind to capture only the date, not the label
                Pattern(
                    "DOB_WITH_LABEL",
                    r"(?<=DOB:?\s{1,5})\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",
                    0.95
                ),
                Pattern(
                    "DOB_FULL_LABEL",
                    r"(?<=Date of Birth:?\s{1,5})\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",
                    0.95
                ),
                Pattern(
                    "DOB_BIRTH_DATE",
                    r"(?<=Birth Date:?\s{1,5})\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",
                    0.95
                )
            ]
        )
    
    @staticmethod
    def get_address_recognizer() -> PatternRecognizer:
        """
        US Address recognizer.
        Handles various address formats with street, city, state, ZIP.
        
        Examples:
        - "123 Main St, Boston, MA 02101"
        - "4127 W. Elm st Apt #3B, Springfield, IL 62704"
        - "456 Oak Ave Unit 2C, New York, NY 10001"
        """
        return PatternRecognizer(
            supported_entity="ADDRESS",
            patterns=[
                # Full address with apartment/unit
                Pattern(
                    "US_ADDRESS_WITH_APT",
                    r"\d+\s+(?:[NSEW]\.?\s+)?[A-Z][a-z]+\.?\s+(?:[A-Z][a-z]+\.?\s+)?(?:st|St|street|Street|ave|Ave|avenue|Avenue|rd|Rd|road|Road|blvd|Blvd|dr|Dr|ln|Ln|way|Way)\.?\s+(?:Apt|apt|Unit|unit|Suite|suite|#)\s*#?\d+[A-Z]?,\s+[A-Z][a-z]+,\s+[A-Z]{2}\s+\d{5}(?:-\d{4})?",
                    0.90
                ),
                # Address without apartment
                Pattern(
                    "US_ADDRESS_SIMPLE",
                    r"\d+\s+(?:[NSEW]\.?\s+)?[A-Z][a-z]+\.?\s+(?:[A-Z][a-z]+\.?\s+)?(?:st|St|street|Street|ave|Ave|avenue|Avenue|rd|Rd|road|Road|blvd|Blvd|dr|Dr|ln|Ln|way|Way)\.?,\s+[A-Z][a-z]+,\s+[A-Z]{2}\s+\d{5}(?:-\d{4})?",
                    0.85
                )
            ]
        )
    
    @staticmethod
    def get_organization_recognizer() -> PatternRecognizer:
        """
        Organization/Company name recognizer.
        CRITICAL: Only matches in work-related contexts to avoid false positives.
        
        Examples (WILL match):
        - "works at Google Inc"
        - "employed by ABC Company"
        - "at work (McArthur Shipping Co)"
        
        Examples (WON'T match):
        - "CHIEF COMPLAINT:" (avoids matching "CO" in COMPLAINT)
        - "Emergency contact" (avoids matching "CO" in contact)
        """
        return PatternRecognizer(
            supported_entity="ORGANIZATION",
            patterns=[
                # After "works at/for" or "employed by/at"
                Pattern(
                    "COMPANY_EMPLOYMENT",
                    r"(?<=works? (?:at|for) )[A-Z][a-zA-Z\s,&]+\s+(?:Co\.?|Corp\.?|Corporation|Inc\.?|LLC|Company|Ltd\.?|Limited|Shipping|Services|Group|Industries|Partners)",
                    0.85
                ),
                Pattern(
                    "COMPANY_EMPLOYED",
                    r"(?<=employed (?:by|at) )[A-Z][a-zA-Z\s,&]+\s+(?:Co\.?|Corp\.?|Corporation|Inc\.?|LLC|Company|Ltd\.?|Limited|Shipping|Services|Group|Industries|Partners)",
                    0.85
                ),
                # In parentheses after "work"
                Pattern(
                    "COMPANY_PARENTHESES",
                    r"(?<=work \()[A-Z][a-zA-Z\s,&]+\s+(?:Co\.?|Corp\.?|Corporation|Inc\.?|LLC|Company|Ltd\.?|Limited|Shipping|Services|Group|Industries|Partners)(?=\))",
                    0.85
                ),
                # "at [Company Name]" pattern
                Pattern(
                    "COMPANY_AT",
                    r"(?<=\sat )[A-Z][a-zA-Z\s,&]+\s+(?:Co\.?|Corp\.?|Corporation|Inc\.?|LLC|Company|Ltd\.?|Limited|Shipping|Services|Group|Industries|Partners)(?=[\.,\s])",
                    0.75
                )
            ]
        )
    
    @staticmethod
    def get_phone_recognizer() -> PatternRecognizer:
        """
        Phone number recognizer (supplements Presidio's default).
        Handles various formats including extensions.
        
        Examples:
        - "555-123-4567"
        - "(555) 123-4567"
        - "555.123.4567"
        - "+1-555-123-4567"
        - "555-123-4567 x123"
        """
        return PatternRecognizer(
            supported_entity="PHONE_NUMBER",
            patterns=[
                # US phone with dashes
                Pattern(
                    "PHONE_DASHES",
                    r"\d{3}[-\.\s]\d{3}[-\.\s]\d{4}(?:\s*(?:x|ext|extension)\s*\d+)?",
                    0.85
                ),
                # US phone with parentheses
                Pattern(
                    "PHONE_PARENS",
                    r"\(\d{3}\)\s*\d{3}[-\.\s]\d{4}(?:\s*(?:x|ext|extension)\s*\d+)?",
                    0.85
                ),
                # International format
                Pattern(
                    "PHONE_INTERNATIONAL",
                    r"\+\d{1,3}[-\.\s]\d{3}[-\.\s]\d{3}[-\.\s]\d{4}(?:\s*(?:x|ext|extension)\s*\d+)?",
                    0.85
                )
            ]
        )
    
    @staticmethod
    def get_email_recognizer() -> PatternRecognizer:
        """
        Email address recognizer (supplements Presidio's default).
        
        Examples:
        - "john.smith@example.com"
        - "patient@hospital.org"
        """
        return PatternRecognizer(
            supported_entity="EMAIL_ADDRESS",
            patterns=[
                Pattern(
                    "EMAIL_STANDARD",
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                    0.90
                )
            ]
        )
    
    @staticmethod
    def get_ssn_recognizer() -> PatternRecognizer:
        """
        Social Security Number recognizer.
        
        Examples:
        - "123-45-6789"
        - "SSN: 123-45-6789"
        """
        return PatternRecognizer(
            supported_entity="SSN",
            patterns=[
                Pattern(
                    "SSN_STANDARD",
                    r"(?:SSN:?\s*)?\d{3}-\d{2}-\d{4}",
                    0.95
                ),
                Pattern(
                    "SSN_NO_DASHES",
                    r"(?:SSN:?\s*)?\d{9}",
                    0.85
                )
            ],
            context=["social security", "SSN", "ss#"]
        )
    
    @staticmethod
    def get_zipcode_recognizer() -> PatternRecognizer:
        """
        ZIP code recognizer.
        Note: Should preserve first 3 digits per HIPAA Safe Harbor.
        
        Examples:
        - "62704"
        - "02101-1234"
        """
        return PatternRecognizer(
            supported_entity="ZIPCODE",
            patterns=[
                # 5-digit ZIP
                Pattern(
                    "ZIP_5",
                    r"(?<!\d)\d{5}(?!\d)(?!-)",
                    0.70
                ),
                # ZIP+4
                Pattern(
                    "ZIP_PLUS4",
                    r"(?<!\d)\d{5}-\d{4}(?!\d)",
                    0.90
                )
            ],
            context=["zip", "postal"]
        )
    
    @staticmethod
    def get_age_recognizer() -> PatternRecognizer:
        """
        Age recognizer - but we'll PRESERVE ages <89 in the filter.
        This is just for detection.
        
        Examples:
        - "43 y/o"
        - "Age: 67"
        - "67 year old"
        """
        return PatternRecognizer(
            supported_entity="AGE",
            patterns=[
                Pattern(
                    "AGE_YO",
                    r"\b\d{1,3}\s*(?:y/?o|year[s]?[ -]old)\b",
                    0.85
                ),
                Pattern(
                    "AGE_LABEL",
                    r"(?:Age|age):?\s*\d{1,3}",
                    0.90
                )
            ]
        )
    
    @staticmethod
    def get_license_recognizer() -> PatternRecognizer:
        """
        Driver's License and other license numbers.
        
        Examples:
        - "DL: A12345678"
        - "License: 123-456-789"
        """
        return PatternRecognizer(
            supported_entity="LICENSE",
            patterns=[
                Pattern(
                    "DL_LABELED",
                    r"(?:DL|Driver'?s? License|License):?\s*[A-Z0-9-]{5,15}",
                    0.85
                )
            ]
        )
    
    @staticmethod
    def get_all_recognizers() -> List[PatternRecognizer]:
        """
        Returns all medical recognizers in priority order.
        Higher priority recognizers should be listed first.
        """
        return [
            MedicalRecognizers.get_ssn_recognizer(),
            MedicalRecognizers.get_mrn_recognizer(),
            MedicalRecognizers.get_dob_recognizer(),
            MedicalRecognizers.get_license_recognizer(),
            MedicalRecognizers.get_phone_recognizer(),
            MedicalRecognizers.get_email_recognizer(),
            MedicalRecognizers.get_address_recognizer(),
            MedicalRecognizers.get_organization_recognizer(),
            MedicalRecognizers.get_age_recognizer(),
            MedicalRecognizers.get_zipcode_recognizer()
        ]
    
    @staticmethod
    def get_recognizer_by_entity(entity_type: str) -> PatternRecognizer:
        """
        Get a specific recognizer by entity type.
        
        Args:
            entity_type: One of "MRN", "DOB", "ADDRESS", etc.
        
        Returns:
            PatternRecognizer for that entity type
        
        Raises:
            ValueError if entity_type not found
        """
        recognizer_map = {
            "MRN": MedicalRecognizers.get_mrn_recognizer,
            "DOB": MedicalRecognizers.get_dob_recognizer,
            "ADDRESS": MedicalRecognizers.get_address_recognizer,
            "ORGANIZATION": MedicalRecognizers.get_organization_recognizer,
            "PHONE_NUMBER": MedicalRecognizers.get_phone_recognizer,
            "EMAIL_ADDRESS": MedicalRecognizers.get_email_recognizer,
            "SSN": MedicalRecognizers.get_ssn_recognizer,
            "ZIPCODE": MedicalRecognizers.get_zipcode_recognizer,
            "AGE": MedicalRecognizers.get_age_recognizer,
            "LICENSE": MedicalRecognizers.get_license_recognizer
        }
        
        if entity_type not in recognizer_map:
            raise ValueError(f"Unknown entity type: {entity_type}")
        
        return recognizer_map[entity_type]()

################################################################################################################
# Transformer registry, determined to be not as effectived as Transformer NLP Engine + MedicalRecognizers
################################################################################################################

# RECOGNIZER_LIST = [get_titles_recognizer, get_location_deny_list, get_age_recognizer, get_zipcode_recognizer]

# bert_path = "obi/deid_roberta_i2b2"
# supported_entities = BERT_DEID_CONFIGURATION.get("PRESIDIO_SUPPORTED_ENTITIES")
# bert_recognizer = TransformersRecognizer(model_path=bert_path, supported_entities=supported_entities)
# bert_recognizer.load_transformer(**BERT_DEID_CONFIGURATION)

# stanford_path = "StanfordAIMI/stanford-deidentifier-base"
# stanford_recognizer = TransformersRecognizer(model_path=stanford_path, supported_entities=supported_entities)
# stanford_recognizer.load_transformer(**STANFORD_COFIGURATION)

# # add transformers model to the registry
# TRANSFORMER_REGISTRY = RecognizerRegistry()
# TRANSFORMER_REGISTRY.add_recognizer(bert_recognizer)
# TRANSFORMER_REGISTRY.add_recognizer(stanford_recognizer)
# TRANSFORMER_REGISTRY.remove_recognizer("SpacyRecognizer")
