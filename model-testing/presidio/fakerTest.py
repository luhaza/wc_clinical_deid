import sys
import re
from presidio_analyzer import AnalyzerEngine, RecognizerResult, PatternRecognizer, Pattern
from faker import Faker


def create_custom_analyzer():
    """Create analyzer with custom recognizers for medical records"""
    
    # 1. MRN Pattern (Medical Record Number)
    mrn_recognizer = PatternRecognizer(
        supported_entity="MRN",
        patterns=[
            Pattern("MRN_LABELED", r"MRN:?\s*\d{6,10}", 0.95)
        ]
    )
    
    # 2. Address Pattern (US addresses) - more specific
    address_recognizer = PatternRecognizer(
        supported_entity="ADDRESS",
        patterns=[
            Pattern(
                "US_ADDRESS_FULL",
                r"\d+\s+[NSEW]?\.?\s*[A-Z][a-z]+\.?\s+(?:[A-Z][a-z]+\.?\s+)?(?:st|St|street|Street|ave|Ave|avenue|Avenue|rd|Rd|road|Road|blvd|Blvd|boulevard|Boulevard|dr|Dr|drive|Drive|ln|Ln|lane|Lane)\.?\s+(?:Apt|apt|Unit|unit|Suite|suite|#)\s*#?\d+[A-Z]?,\s+[A-Z][a-z]+,\s+[A-Z]{2}\s+\d{5}(?:-\d{4})?",
                0.9
            )
        ]
    )
    
    # 3. Organization/Company Pattern - MORE RESTRICTIVE to avoid false positives
    org_recognizer = PatternRecognizer(
        supported_entity="ORGANIZATION",
        patterns=[
            Pattern(
                "COMPANY_WORK_CONTEXT",
                r"(?:at work \(|works? (?:at|for) )([A-Z][a-z]+(?:[,\s]+[A-Z][a-z]+)*\s+(?:Co|Corp|Corporation|Inc|LLC|Company|Ltd|Limited|Shipping|Services|Group|Industries))[)\.]?",
                0.9
            )
        ]
    )
    
    # 4. DOB Pattern - just the date part, not the label
    dob_recognizer = PatternRecognizer(
        supported_entity="DOB",
        patterns=[
            Pattern("DOB_DATE", r"(?<=DOB:\s{1,5})\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", 0.95)
        ]
    )
    
    # Initialize analyzer
    analyzer = AnalyzerEngine()
    
    # Add custom recognizers
    analyzer.registry.add_recognizer(mrn_recognizer)
    analyzer.registry.add_recognizer(address_recognizer)
    analyzer.registry.add_recognizer(org_recognizer)
    analyzer.registry.add_recognizer(dob_recognizer)
    
    return analyzer


def should_skip_entity(detected_text, text, start_pos, entity_type):
    """Determine if an entity should be skipped based on context"""
    
    # Skip DATE_TIME for durations
    if entity_type == "DATE_TIME":
        # Duration patterns: "2 weeks", "3 days", "x ~2 weeks"
        if re.search(r'(?:x\s*~?\s*)?\d+\s+(week|day|month|year)s?', detected_text, re.IGNORECASE):
            return True
        
        # Relative time references
        if detected_text.lower() in ['today', 'tomorrow', 'yesterday', 'tonight']:
            return True
        
        # Check for "in X weeks/days" pattern
        context_before = text[max(0, start_pos - 15):start_pos].lower()
        if 'in ' in context_before and re.search(r'\d+\s+(week|day|month)', detected_text, re.IGNORECASE):
            return True
    
    return False


def manual_year_obfuscation(text, fake):
    """Manually obfuscate standalone years that Presidio misses"""
    
    # Find patterns like "quit 2015" or "since 2015"
    year_patterns = [
        (r'\bquit\s+(\d{4})\b', lambda m: f"quit {fake.random_int(1990, 2020)}"),
        (r'\bsince\s+(\d{4})\b', lambda m: f"since {fake.random_int(1990, 2020)}"),
        (r'\bin\s+(\d{4})\b', lambda m: f"in {fake.random_int(1990, 2020)}")
    ]
    
    for pattern, replacement_func in year_patterns:
        text = re.sub(pattern, replacement_func, text)
    
    return text


def obfuscate_text(text, seed=42, verbose=False):
    """Enhanced obfuscation with medical record support"""
    fake = Faker()
    Faker.seed(seed)
    
    # Use custom analyzer
    analyzer = create_custom_analyzer()
    analyzer_results = analyzer.analyze(text=text, language="en", score_threshold=0.4)
    
    if verbose:
        print("\n" + "=" * 80)
        print("DETECTED ENTITIES:")
        print("=" * 80)
        for result in analyzer_results:
            detected_text = text[result.start:result.end]
            print(f"  {result.entity_type}: '{detected_text}' at {result.start}-{result.end} (score: {result.score:.2f})")
    
    # Find all PERSON entities and their duplicates
    person_entities = {}
    for result in analyzer_results:
        if result.entity_type == "PERSON":
            detected_text = text[result.start:result.end]
            person_entities[detected_text] = result
    
    # Find duplicate person names
    additional_results = []
    for person_name in person_entities.keys():
        start = 0
        while True:
            pos = text.find(person_name, start)
            if pos == -1:
                break
            
            already_detected = any(
                r.start == pos and r.end == pos + len(person_name) and r.entity_type == "PERSON"
                for r in analyzer_results
            )
            
            if not already_detected:
                new_result = RecognizerResult(
                    entity_type="PERSON",
                    start=pos,
                    end=pos + len(person_name),
                    score=0.85
                )
                additional_results.append(new_result)
                if verbose:
                    print(f"  [ADDED] PERSON: '{person_name}' at {pos}-{pos + len(person_name)} (duplicate)")
            
            start = pos + 1
    
    all_results = list(analyzer_results) + additional_results
    
    # Create mappings for each entity type
    name_mapping = {}
    phone_mapping = {}
    email_mapping = {}
    date_mapping = {}
    mrn_mapping = {}
    address_mapping = {}
    org_mapping = {}
    
    # Filter out entities that should be skipped
    filtered_results = []
    for result in all_results:
        detected_text = text[result.start:result.end]
        
        if should_skip_entity(detected_text, text, result.start, result.entity_type):
            if verbose:
                print(f"  [SKIPPED] {result.entity_type}: '{detected_text}' (duration/relative time)")
            continue
        
        filtered_results.append(result)
    
    # Sort results by start position in reverse order
    sorted_results = sorted(filtered_results, key=lambda x: x.start, reverse=True)
    
    if verbose:
        print("\n" + "=" * 80)
        print("REPLACEMENT PROCESS:")
        print("=" * 80)
    
    # Replace entities
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
        
        elif result.entity_type == "DATE_TIME":
            if detected_text not in date_mapping:
                date_mapping[detected_text] = fake.date()
            replacement = date_mapping[detected_text]
        
        elif result.entity_type == "DOB":
            if detected_text not in date_mapping:
                # Generate fake DOB in same format
                if re.match(r'\d{1,2}[-/]\d{1,2}[-/]\d{2}', detected_text):
                    # Short year format (YY)
                    date_mapping[detected_text] = fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%m-%d-%y")
                else:
                    # Full year format (YYYY)
                    date_mapping[detected_text] = fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%m-%d-%Y")
            replacement = date_mapping[detected_text]
        
        elif result.entity_type == "MRN":
            if detected_text not in mrn_mapping:
                # Extract the number part
                number_match = re.search(r'\d+', detected_text)
                if number_match:
                    number_length = len(number_match.group())
                    fake_mrn = ''.join([str(fake.random_digit()) for _ in range(number_length)])
                    # Preserve the "MRN:" label
                    replacement = re.sub(r'\d+', fake_mrn, detected_text)
                    mrn_mapping[detected_text] = replacement
                else:
                    mrn_mapping[detected_text] = ''.join([str(fake.random_digit()) for _ in range(8)])
                    replacement = mrn_mapping[detected_text]
            else:
                replacement = mrn_mapping[detected_text]
        
        elif result.entity_type == "ADDRESS":
            if detected_text not in address_mapping:
                # Generate fake address matching the format
                has_apt = any(word in detected_text for word in ['Apt', 'apt', 'Unit', 'unit', '#'])
                if has_apt:
                    apt_num = fake.random_int(1, 99)
                    apt_letter = fake.random_element(['A', 'B', 'C', ''])
                    address_mapping[detected_text] = f"{fake.building_number()} {fake.street_name()} {fake.street_suffix()} Apt #{apt_num}{apt_letter}, {fake.city()}, {fake.state_abbr()} {fake.zipcode()}"
                else:
                    address_mapping[detected_text] = f"{fake.building_number()} {fake.street_name()} {fake.street_suffix()}, {fake.city()}, {fake.state_abbr()} {fake.zipcode()}"
            replacement = address_mapping[detected_text]
        
        elif result.entity_type == "ORGANIZATION":
            if detected_text not in org_mapping:
                org_mapping[detected_text] = fake.company()
            replacement = org_mapping[detected_text]
        
        if replacement:
            if verbose:
                print(f"[{idx + 1}] {result.entity_type}: '{detected_text}' → '{replacement}'")
            anonymized_text = anonymized_text[:result.start] + replacement + anonymized_text[result.end:]
    
    # Manual post-processing for standalone years
    anonymized_text = manual_year_obfuscation(anonymized_text, fake)
    
    all_mappings = {
        "names": name_mapping,
        "phones": phone_mapping,
        "emails": email_mapping,
        "dates": date_mapping,
        "mrns": mrn_mapping,
        "addresses": address_mapping,
        "organizations": org_mapping
    }
    
    return anonymized_text, all_mappings


def main():
    # Check command-line arguments
    if len(sys.argv) < 3:
        print("Usage: python obfuscate.py <input_file> <output_file> [--verbose]")
        print("\nArguments:")
        print("  input_file   Path to input text file")
        print("  output_file  Path to output text file")
        print("  --verbose    (Optional) Print detailed processing info and mappings")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    verbose = "--verbose" in sys.argv
    
    # Read input file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            text = f.read()
        print(f"✓ Read input file: {input_file}")
    except FileNotFoundError:
        print(f"✗ Error: Input file '{input_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error reading input file: {e}")
        sys.exit(1)
    
    # Obfuscate text
    print("Processing text...")
    anonymized_text, mappings = obfuscate_text(text, seed=42, verbose=verbose)
    
    # Write output file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(anonymized_text)
        print(f"✓ Wrote output file: {output_file}")
    except Exception as e:
        print(f"✗ Error writing output file: {e}")
        sys.exit(1)
    
    # Print mappings if verbose
    if verbose:
        print("\n" + "=" * 80)
        print("MAPPINGS SUMMARY:")
        print("=" * 80)
        for category, mapping in mappings.items():
            if mapping:
                print(f"\n{category.upper()}:")
                for original, fake_value in mapping.items():
                    print(f"  '{original}' → '{fake_value}'")
    
    print("\n✓ Obfuscation complete!")


if __name__ == "__main__":
    main()