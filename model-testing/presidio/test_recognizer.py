# test_recognizers.py

import sys
from presidio_analyzer import AnalyzerEngine
from medical_recognizer import MedicalRecognizers
from clinical_filter import ClinicalDataFilter


def test_recognizers_on_file(input_file, verbose=False, show_filtered=False):
    """
    Test medical recognizers on a text file and print detected entities.
    
    Args:
        input_file: Path to text file to analyze
        verbose: If True, print full context around each detection
        show_filtered: If True, show entities that were filtered out
    """
    
    # Read the file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            text = f.read()
        print(f"✓ Loaded file: {input_file}")
        print(f"  File length: {len(text)} characters\n")
    except FileNotFoundError:
        print(f"✗ Error: File '{input_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error reading file: {e}")
        sys.exit(1)
    
    # Create analyzer with custom recognizers
    print("Initializing analyzer with medical recognizers...")
    analyzer = AnalyzerEngine()
    
    for recognizer in MedicalRecognizers.get_all_recognizers():
        analyzer.registry.add_recognizer(recognizer)
    
    print("✓ Analyzer ready\n")
    
    # Analyze the text
    print("Analyzing text...\n")
    raw_results = analyzer.analyze(text=text, language="en", score_threshold=0.35)
    
    print(f"Raw detections: {len(raw_results)}")
    
    # Apply filters using the unified filter_results method
    print("Applying filters...")
    results = ClinicalDataFilter.filter_results(text, raw_results)
    
    print(f"After filtering: {len(results)} entities\n")
    
    # Calculate what was filtered out for reporting
    if show_filtered:
        filtered_out = []
        filtered_result_positions = {(r.start, r.end) for r in results}
        
        for raw_result in raw_results:
            if (raw_result.start, raw_result.end) not in filtered_result_positions:
                detected_text = text[raw_result.start:raw_result.end]
                
                # Determine why it was filtered
                if ClinicalDataFilter._should_preserve(detected_text, text, raw_result):
                    reason = "PRESERVED (clinical data)"
                elif ClinicalDataFilter._is_false_positive(detected_text, raw_result.entity_type):
                    reason = "FALSE POSITIVE"
                else:
                    reason = "NESTED/OVERLAPPING"
                
                filtered_out.append((raw_result, reason))
        
        if filtered_out:
            print("=" * 80)
            print(f"FILTERED OUT ENTITIES ({len(filtered_out)} total)")
            print("=" * 80)
            for result, reason in filtered_out:
                detected_text = text[result.start:result.end]
                print(f"\n{result.entity_type}: '{detected_text}'")
                print(f"  Position: {result.start}-{result.end}")
                print(f"  Reason: {reason}")
            print()
    
    # Print results
    print("=" * 80)
    print(f"ENTITIES TO OBFUSCATE ({len(results)} total)")
    print("=" * 80)
    
    if not results:
        print("No entities to obfuscate.")
        return
    
    # Sort by position in text
    results = sorted(results, key=lambda x: x.start)
    
    # Group by entity type for summary
    by_type = {}
    for result in results:
        if result.entity_type not in by_type:
            by_type[result.entity_type] = []
        by_type[result.entity_type].append(result)
    
    # Print summary
    print("\nSUMMARY BY TYPE:")
    print("-" * 80)
    for entity_type, entities in sorted(by_type.items()):
        print(f"  {entity_type}: {len(entities)} occurrences")
    print()
    
    # Print detailed results
    print("\nDETAILED RESULTS:")
    print("-" * 80)
    
    for idx, result in enumerate(results, 1):
        detected_text = text[result.start:result.end]
        
        print(f"\n[{idx}] {result.entity_type}")
        print(f"    Text: '{detected_text}'")
        print(f"    Position: {result.start}-{result.end}")
        print(f"    Confidence: {result.score:.2f}")
        
        if verbose:
            # Show context (50 chars before and after)
            context_start = max(0, result.start - 50)
            context_end = min(len(text), result.end + 50)
            context = text[context_start:context_end]
            
            # Add markers around the detected entity
            marker_start = result.start - context_start
            marker_end = marker_start + (result.end - result.start)
            context_with_markers = (
                context[:marker_start] + 
                ">>>" + 
                context[marker_start:marker_end] + 
                "<<<" + 
                context[marker_end:]
            )
            
            print(f"    Context: ...{context_with_markers}...")
    
    print("\n" + "=" * 80)
    print(f"TOTAL: {len(results)} entities to obfuscate")
    print("=" * 80)


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_recognizers.py <input_file> [--verbose] [--show-filtered]")
        print("\nArguments:")
        print("  input_file       Path to text file to analyze")
        print("  --verbose        Show context around each detection")
        print("  --show-filtered  Show entities that were filtered out")
        print("\nExample:")
        print("  python test_recognizers.py primary_care_visit.txt")
        print("  python test_recognizers.py primary_care_visit.txt --verbose --show-filtered")
        sys.exit(1)
    
    input_file = sys.argv[1]
    verbose = "--verbose" in sys.argv
    show_filtered = "--show-filtered" in sys.argv
    
    test_recognizers_on_file(input_file, verbose, show_filtered)


if __name__ == "__main__":
    main()