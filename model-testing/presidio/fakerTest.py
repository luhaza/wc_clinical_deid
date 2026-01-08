from presidio_anonymizer import AnonymizerEngine
from presidio_analyzer import AnalyzerEngine

from presidio_anonymizer.entities import OperatorConfig, EngineResult, RecognizerResult
from faker import Faker
# from faker.providers import phone_numbers 


fake = Faker()

# Create faker function (note that it has to receive a value)
def fake_name(x):
    return fake.name()

def fakeNumber(x):
    return fake.phone_number()


text = "My name is Raphael, my number is 423-467-321, my name is Raphael, and I like to fish."

# Create custom operator for the PERSON entity
operators = {"PERSON": OperatorConfig("custom", {"lambda": fake_name})}
#  "PHONE_NUMBER": OperatorConfig("custom", {"lambda": fakeNumber})
analyzer = AnalyzerEngine()
# Analyzer output
analyzer_results = analyzer.analyze(text=text, language="en")



anonymizer = AnonymizerEngine()

anonymized_results = anonymizer.anonymize(
    text=text, analyzer_results=analyzer_results, operators=operators
)

print(anonymized_results.text)