from presidio_analyzer import AnalyzerEngine, RecognizerResult
from faker import Faker

fake = Faker()
Faker.seed(42)  # For reproducibility

# Test text
text = "My name is Raphael, my number is 423-467-321, my email is raphael@example.com. You can reach Raphael at 423-467-321 and raphael@example.com or Sarah at 555-123-4567. Sarah is out of town on 4/22/2003"

# Initialize analyzer
analyzer = AnalyzerEngine()
analyzer_results = analyzer.analyze(text=text, language="en")

print("=" * 80)
print("ORIGINAL PRESIDIO DETECTIONS:")
print("=" * 80)
for result in analyzer_results:
    detected_text = text[result.start:result.end]
    print(f"  {result.entity_type}: '{detected_text}' at position {result.start}-{result.end}")

# Find all PERSON entities detected by Presidio
person_entities = {}
for result in analyzer_results:
    if result.entity_type == "PERSON":
        detected_text = text[result.start:result.end]
        person_entities[detected_text] = result

# For each detected person, find ALL occurrences in the text
additional_results = []
for person_name in person_entities.keys():
    start = 0
    occurrences = []
    while True:
        pos = text.find(person_name, start)
        if pos == -1:
            break
        occurrences.append(pos)        
        # Check if this position is already in analyzer_results
        already_detected = any(
            r.start == pos and r.end == pos + len(person_name) and r.entity_type == "PERSON"
            for r in analyzer_results
        )
        
        if not already_detected:
            # Create a new RecognizerResult for this occurrence
            new_result = RecognizerResult(
                entity_type="PERSON",
                start=pos,
                end=pos + len(person_name),
                score=0.85  # Same score as Presidio typically gives
            )
            additional_results.append(new_result)
        
        start = pos + 1

# Combine original results with additional results
all_results = list(analyzer_results) + additional_results

# Create mappings
name_mapping = {}
phone_mapping = {}
email_mapping = {}

# Sort results by start position in reverse order
sorted_results = sorted(all_results, key=lambda x: x.start, reverse=True)

# Manually replace entities
anonymized_text = text
for idx, result in enumerate(sorted_results):
    detected_text = text[result.start:result.end]
    replacement = None
    
    if result.entity_type == "PERSON":
        if detected_text not in name_mapping:
            name_mapping[detected_text] = fake.name()
        replacement = name_mapping[detected_text]
    
    elif result.entity_type == "PHONE_NUMBER":
        if detected_text not in phone_mapping:
            phone_mapping[detected_text] = fake.phone_number()
        replacement = phone_mapping[detected_text]
    
    elif result.entity_type == "EMAIL_ADDRESS":
        if detected_text not in email_mapping:
            email_mapping[detected_text] = fake.email()
        replacement = email_mapping[detected_text]
    
    elif result.entity_type == "DATE_TIME" and any(char.isdigit() for char in detected_text):
        if detected_text not in phone_mapping:
            phone_mapping[detected_text] = fake.phone_number()
        replacement = phone_mapping[detected_text]
    
    if replacement:
        anonymized_text = anonymized_text[:result.start] + replacement + anonymized_text[result.end:]

print("\nFINAL RESULTS:\n")
print(text)
print("\n")
print(anonymized_text)

# print(f"Names: {name_mapping}")
# print(f"Phones: {phone_mapping}")
# print(f"Emails: {email_mapping}")
