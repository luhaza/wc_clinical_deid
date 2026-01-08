from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine



file_loc = "../sample data/lab_result.txt"
text = open(file_loc).read()
print(text, "----------")

# Set up the engine, loads the NLP module (spaCy model by default) 
# and other PII recognizers
analyzer = AnalyzerEngine()

# Call analyzer to get results
results = analyzer.analyze(text=text, 
                           entities=['PERSON', 'PHONE_NUMBER', 'MEDICAL_LICENSE','LOCATION', 'IP_ADDRESS',
                                     'EMAIL_ADDRESS', 'US_SSN', 'US_DRIVER_LICENSE',
                                     'CREDIT_CARD', 'US_BANK_NUMBER', 'US_ITIN', 'US_PASSPORT'], 
                           language='en',
                           )

# Analyzer results are passed to the AnonymizerEngine for anonymization

anonymizer = AnonymizerEngine()

anonymized_text = anonymizer.anonymize(text=text,analyzer_results=results)

print(anonymized_text)
