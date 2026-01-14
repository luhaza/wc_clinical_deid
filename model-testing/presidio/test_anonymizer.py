import sys
from pathlib import Path
from presidio_analyzer import AnalyzerEngine
from context_anonymizer import ContextAwareAnonymizer
from medical_recognizer import MedicalRecognizers
from clinical_filter import ClinicalDataFilter

# Get file paths from command line
if len(sys.argv) < 3:
    print("Usage: python test_anonymizer.py <input_file> <output_file>")
    sys.exit(1)

input_file = sys.argv[1]
output_file = sys.argv[2]

# Read input
print(f"Reading: {input_file}")
with open(input_file, 'r') as f:
    text = f.read()

# Setup analyzer WITHOUT NLP engine (same as test_recognizer)
print("Setting up analyzer...")
analyzer = AnalyzerEngine()

# Add medical recognizers
print("Adding medical recognizers...")
for recognizer in MedicalRecognizers.get_all_recognizers():
    analyzer.registry.add_recognizer(recognizer)

# Analyze
print("Analyzing text...")
raw_results = analyzer.analyze(text=text, language='en', score_threshold=0.35)
print(f"  Raw detections: {len(raw_results)}")

# Apply clinical filter
print("Filtering results...")
results = ClinicalDataFilter.filter_results(text, raw_results)
print(f"  After filtering: {len(results)} entities")

# Anonymize
print("Anonymizing...")
anonymizer = ContextAwareAnonymizer()
anonymized = anonymizer.anonymize(text, results)

# Write output
output_path = Path(output_file)
output_path.parent.mkdir(parents=True, exist_ok=True)

with open(output_path, 'w') as f:
    f.write(anonymized)

print(f"\n✓ Done! Anonymized text saved to {output_file}")