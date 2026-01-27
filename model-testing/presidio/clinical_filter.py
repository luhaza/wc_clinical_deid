import re
from typing import List
from presidio_analyzer import RecognizerResult


class ClinicalDataFilter:
    RELATIVE_TIMES = {
        'today', 'yesterday', 'tomorrow', 'tonight',
        'last week', 'last month', 'last year', 'last night',
        'this morning', 'this afternoon', 'this evening', 'this week',
        'next week', 'next month'
    }
    
    DURATION_PATTERNS = [
        r'^\d+\s+(week|day|month|year)s?$', 
        r'^x\s*~?\s*\d+\s+(week|day|month)s?$',  
        r'^(week|day|month|year)s?$', 
        r'^breath x ~\d+$',  
    ]
    
    MEDICAL_TERMS = {
        'ekg', 'ecg', 'mri', 'ct', 'xray', 'lab', 'labs',
        'lisinopril', 'atorvastatin', 'metformin', 'aspirin', 'ibuprofen',
        'tylenol', 'advil', 'prednisone', 'amoxicillin', 'azithromycin',
        'htn', 'dm', 'copd', 'cad', 'chf', 'gerd', 'mi', 'dvt', 'pe',
        'occ', 'prn', 'qhs', 'bid', 'tid', 'qid',
        'patient', 'complaint', 'history', 'assessment', 'plan'
    }
    
    @staticmethod
    def filter_results(text: str, results: List[RecognizerResult]) -> List[RecognizerResult]:
        # Step 1: Clean person names
        results = ClinicalDataFilter.clean_person_names(text, results)
        
        # Step 2: Filter out false positives and clinical data
        filtered = []
        for result in results:
            detected_text = text[result.start:result.end].strip()
            
            # Skip if should be preserved
            if ClinicalDataFilter._should_preserve(detected_text, text, result):
                continue
            
            # Skip if it's a false positive
            if ClinicalDataFilter._is_false_positive(detected_text, result.entity_type):
                continue
            
            filtered.append(result)
        
        # Step 3: Resolve conflicts (e.g., same text detected as both ZIPCODE and DATE_TIME)
        filtered = ClinicalDataFilter._resolve_conflicts(text, filtered)
        
        # Step 4: Remove nested entities (e.g., city/ZIP inside ADDRESS)
        filtered = ClinicalDataFilter._remove_nested_entities(filtered)
        
        return filtered
    
    @staticmethod
    def _should_preserve(detected_text: str, full_text: str, result: RecognizerResult) -> bool:
        """Determine if entity should be preserved (not obfuscated)"""
        
        # Preserve relative times
        if result.entity_type == "DATE_TIME":
            if detected_text.lower() in ClinicalDataFilter.RELATIVE_TIMES:
                return True
            
            # Preserve durations
            for pattern in ClinicalDataFilter.DURATION_PATTERNS:
                if re.match(pattern, detected_text, re.IGNORECASE):
                    return True
            
            # Check context for duration indicators
            context_before = full_text[max(0, result.start - 20):result.start].lower()
            
            # "in 2 weeks" or "for 3 days" patterns
            if any(word in context_before for word in ['in ', 'for ', 'x ', 'x~']):
                if re.search(r'\d+\s+(week|day|month|year)s?', detected_text, re.IGNORECASE):
                    return True
            
            context_before_expanded = full_text[max(0, result.start - 50):result.start].lower()
            
            # Preserve dates after these medical history keywords
            history_keywords = [
                'began', 'started', 'onset', 'quit', 'stopped', 
                'diagnosed', 'since', 'symptoms', 'history'
            ]
            
            if any(keyword in context_before_expanded for keyword in history_keywords):
                return True
            
            # "quit 2015", "since 2010", etc.
            if re.match(r'^\d{4}$', detected_text):
                if any(keyword in context_before_expanded for keyword in ['quit', 'since', 'started', 'began', 'stopped']):
                    return True
        
        # Preserve ages under 89
        if result.entity_type == "AGE":
            age_match = re.search(r'\d+', detected_text)
            if age_match and int(age_match.group()) < 89:
                return True
        
        return False
    
    @staticmethod
    def _is_false_positive(detected_text: str, entity_type: str) -> bool:
        """Check if detected entity is a false positive"""
        
        text_lower = detected_text.lower().strip()
        
        # Check if it's a medical term
        if text_lower in ClinicalDataFilter.MEDICAL_TERMS:
            return True
        
        # Single letters or very short strings that are likely abbreviations
        if len(text_lower) <= 2 and entity_type in ['PERSON', 'ORGANIZATION', 'LOCATION']:
            return True
        
        # Single word "weeks", "days", etc. should not be DATE_TIME
        if entity_type == "DATE_TIME":
            if re.match(r'^(week|day|month|year)s?$', detected_text, re.IGNORECASE):
                return True
            
            # 5-digit numbers that look like ZIP codes
            if re.match(r'^\d{5}$', detected_text):
                return True
            
            # Numbers without context (likely part of MRN or other ID)
            if re.match(r'^\d+$', detected_text) and len(detected_text) > 4:
                return True
        
        # Common false positive org patterns
        if entity_type == 'ORGANIZATION':
            # State abbreviations
            if re.match(r'^[A-Z]{2}$', detected_text):
                return True
            # Duration patterns like "breath x ~2"
            if re.search(r'x\s*~?\s*\d+', detected_text):
                return True
        
        # Single capitalized words that are likely NOT people
        if entity_type == 'PERSON':
            # Single word names that are likely not people
            if len(detected_text.split()) == 1:
                # Check if it's a common place or medical term
                if text_lower in ClinicalDataFilter.MEDICAL_TERMS:
                    return True
                # Check if it looks like a medication (ends in common suffixes)
                med_suffixes = ['pril', 'statin', 'olol', 'pine', 'cillin', 'mycin', 'oxacin']
                if any(text_lower.endswith(suffix) for suffix in med_suffixes):
                    return True
        
        return False
    
    @staticmethod
    def _resolve_conflicts(text: str, results: List[RecognizerResult]) -> List[RecognizerResult]:
        # Group by position
        by_position = {}
        for result in results:
            key = (result.start, result.end)
            if key not in by_position:
                by_position[key] = []
            by_position[key].append(result)
        
        # Define priority order (higher priority = keep this one)
        priority = {
            'SSN': 10,
            'MRN': 9,
            'PHONE_NUMBER': 8,
            'EMAIL_ADDRESS': 8,
            'DOB': 7,
            'ZIPCODE': 6,
            'ADDRESS': 5,
            'PERSON': 4,
            'ORGANIZATION': 3,
            'LICENSE': 3,
            'AGE': 2,
            'LOCATION': 1,
            'DATE_TIME': 0  # Lowest priority
        }
        
        resolved = []
        for (start, end), candidates in by_position.items():
            if len(candidates) == 1:
                resolved.append(candidates[0])
            else:
                # Keep the one with highest priority
                best = max(candidates, key=lambda r: priority.get(r.entity_type, 0))
                resolved.append(best)
        
        return resolved
    
    @staticmethod
    def _remove_nested_entities(results: List[RecognizerResult]) -> List[RecognizerResult]:
        # Sort by span size (larger spans first)
        sorted_results = sorted(results, key=lambda r: (r.end - r.start), reverse=True)
        
        # Entity types that should "consume" smaller entities inside them
        container_types = {'ADDRESS', 'PERSON', 'ORGANIZATION'}
        
        keep = []
        
        for result in sorted_results:
            # Check if this entity is nested inside a container we're already keeping
            is_nested = False
            
            for kept_result in keep:
                # Check if kept_result is a container type
                if kept_result.entity_type in container_types:
                    # Check if current result is inside kept_result
                    if kept_result.start <= result.start and result.end <= kept_result.end:
                        # This result is nested inside a container
                        # Only skip if it's a lower-priority type
                        if result.entity_type in ['LOCATION', 'ZIPCODE', 'DATE_TIME']:
                            is_nested = True
                            break
            
            if not is_nested:
                keep.append(result)
        
        # Sort back by position
        return sorted(keep, key=lambda r: r.start)
    
    @staticmethod
    def clean_person_names(text: str, results: List[RecognizerResult]) -> List[RecognizerResult]:
        cleaned = []
        
        for result in results:
            if result.entity_type == "PERSON":
                detected_text = text[result.start:result.end]
                
                # Regex Explanation:
                # ^                  Start of string
                # [A-Z]              Must start with capital
                # [a-zA-Z\.]*       Can contain letters and dots (for initials like 'K.')
                # (?: ... )*         Optional subgroups (subsequent parts of name)
                # \s+                Separated by whitespace
                # [A-Z][a-zA-Z\.]*  Next word must also look like a name part
                
                name_pattern = r'^([A-Z][a-zA-Z\.]*(?:\s+[A-Z][a-zA-Z\.]*)*)'
                clean_match = re.match(name_pattern, detected_text)
                
                if clean_match:
                    clean_name = clean_match.group(1)
                    # Helper: Don't accidentally capture trailing punctuation if it wasn't part of an initial
                    # e.g., "Smith," -> regex might match "Smith" properly if comma not in []
                    # but if we had [.,] it would match. Current [a-zA-Z\.] includes dots but not commas.
                    
                    # Create new result with corrected end position
                    new_result = RecognizerResult(
                        entity_type="PERSON",
                        start=result.start,
                        end=result.start + len(clean_name),
                        score=result.score
                    )
                    cleaned.append(new_result)
                else:
                    cleaned.append(result)
            else:
                cleaned.append(result)
        
        return cleaned