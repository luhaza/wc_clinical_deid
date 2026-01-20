from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
import hashlib
import json
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig, OperatorResult
from presidio_anonymizer.operators import Operator
from faker import Faker
import random
import re


class DemographicContext:
    """Manages demographic coherence across anonymized entities"""
    def __init__(self, name_groupings: List[set]=None):
        self.mappings: Dict[str, Dict[str, Any]] = {}
        self.faker = Faker()
        self.names = [
            'Noah', 'Ezra', 'Dylan', 'Carter', 'Logan', 'Cameron', 'Jordan',
            'Rowan', 'Micah', 'August', 'Parker', 'Riley', 'Avery', 'Quinn',
            'Kai', 'Blake', 'Asher', 'Robin', 'Rory', 'Spencer', 'Tatum', 
            'Jessie', 'Jackie', 'Baker', 'Tommie', 'Sammy', 'Jamie', 'Noel'
        ]
        self.name_group_map = {}
        if name_groupings:
            for group in name_groupings:
                canonical = sorted(group)[0].lower()
                for variant in group:
                    self.name_group_map[variant.lower()] = canonical
    
    def get_or_create_identity(self, original_value: str, entity_type: str, **context) -> Dict[str, Any]:
        """Get existing mapping or create new coherent identity"""
        key = self._get_key(original_value, entity_type)
        if key in self.mappings:
            return self.mappings[key]
        # Create new identity with demographic coherence
        identity = self._create_coherent_identity(original_value, entity_type, **context)
        self.mappings[key] = identity
        
        return identity
    
    def _get_key(self, value: str, entity_type: str=None) -> str:
        """Generate consistent key for value"""
        if entity_type == 'PERSON' and value.lower() in self.name_group_map:
            canonical = self.name_group_map[value.lower()]
        return hashlib.sha256(value.encode()).hexdigest()
    
    
    def _create_coherent_identity(self, original_value: str, entity_type: str, **context) -> Dict[str, Any]:
        identity = {
            'original': original_value,
            'entity_type': entity_type,
        }
        
        # Generate contextually appropriate replacements based on entity type
        if entity_type == 'PERSON':
            identity['fake_name'] = self.names[random.randrange(len(self.names))]
        
        if entity_type == 'LOCATION':
            # Generate city (no gender correlation for locations)
            identity['fake_city'] = self.faker.city()
            identity['fake_state'] = self.faker.state_abbr()
        
        if entity_type == 'DATE_TIME':
            # Store date shift for this entity (will be consistent across all dates)
            # THIS PROVIDES TEMPORAL CONSISTENCY
            # Same patient always gets same shift, preserving time intervals
            identity['date_shift_days'] = random.randint(30, 365)
        
        return identity


class ContextAwareAnonymizer:
    def __init__(self, name_groupings: List[set]=None):
        self.context = DemographicContext(name_groupings)
        self.anonymizer = AnonymizerEngine()
    
    def anonymize(self, text: str, analyzer_results: List, patient_id: str = None) -> str:
        """
        Anonymize text by replacing ONLY the exact positions in analyzer_results.
        Does NOT use Presidio's anonymizer to avoid re-analysis.
        """
        
        # Sort results by position (reverse order so we replace from end to start)
        # This prevents position shifts when replacing
        sorted_results = sorted(analyzer_results, key=lambda r: r.start, reverse=True)
        
        # Work with the text as a list for easier manipulation
        result_text = text
        
        for result in sorted_results:
            entity_type = result.entity_type
            entity_text = text[result.start:result.end]
            replacement = None
            
            if entity_type == 'PERSON':
                identity = self.context.get_or_create_identity(entity_text, 'PERSON')
                replacement = identity['fake_name']
                
            elif entity_type in ['LOCATION', 'GPE', 'US_CITY']:
                # Get location replacement
                identity = self.context.get_or_create_identity(entity_text, 'LOCATION')
                replacement = identity.get('fake_city', self.context.faker.city())
                
            elif entity_type in ['DATE_TIME', 'DATE', 'DOB']:
                # Get date with consistent shift
                patient_key = patient_id or "default_patient"
                date_identity = self.context.get_or_create_identity(patient_key, 'DATE_TIME')
                shift_days = date_identity['date_shift_days']
                replacement = self._shift_date(entity_text, shift_days)
            
            elif entity_type in ['PHONE_NUMBER']:
                # Generate fake phone number
                replacement = f"{self.context.faker.random_int(200, 999)}.{self.context.faker.random_int(200, 999)}.{self.context.faker.random_int(1000, 9999)}"
            
            elif entity_type == 'EMAIL_ADDRESS':
                # Generate fake email
                replacement = self.context.faker.email()
            
            elif entity_type in ['US_SSN', 'SSN']:
                # Mask SSN
                replacement = "XXX-XX-XXXX"
            
            elif entity_type in ['MRN', 'MEDICAL_RECORD_NUMBER']:
                # Generate fake MRN with same format
                # Extract the number part
                number_match = re.search(r'\d+', entity_text)
                if number_match:
                    original_number = number_match.group()
                    # Generate random number with same length
                    fake_number = ''.join([str(self.context.faker.random_int(0, 9)) for _ in range(len(original_number))])
                    # Replace the number in the original text (preserves "MRN:" label)
                    replacement = entity_text.replace(original_number, fake_number)
                else:
                    # No number found, generate a fake MRN
                    replacement = f"MRN: {self.context.faker.random_int(10000000, 99999999)}"
            
            elif entity_type in ['US_BANK_NUMBER', 'US_DRIVER_LICENSE', 'LICENSE']:
                # Mask with X's of same length
                replacement = "X" * len(entity_text)
            
            elif entity_type == 'ADDRESS':
                # Generate fake address
                replacement = f"{self.context.faker.building_number()} {self.context.faker.street_name()}, {self.context.faker.city()}, {self.context.faker.state_abbr()} {self.context.faker.zipcode()}"
            
            elif entity_type == 'ZIPCODE':
                # Generate fake zipcode
                replacement = self.context.faker.zipcode()
            
            elif entity_type == 'ORGANIZATION':
                # Replace with fake company name
                replacement = self.context.faker.company()
            
            elif entity_type == 'AGE':
                # Keep age as-is (filter already preserved ages <89)
                replacement = entity_text
            
            else:
                # For any unknown types, keep original text
                replacement = entity_text
            
            # Replace the text at this exact position
            if replacement is not None:
                result_text = result_text[:result.start] + replacement + result_text[result.end:]
        
        return result_text
    
    def _shift_date(self, date_str: str, shift_days: int) -> str:
        """Helper to shift dates"""
        try:
            # List of formats to try, including those with single digits
            formats = [
                '%m-%d-%Y',      # 3-5-1981
                '%m-%d-%y',      # 3-5-81
                '%m/%d/%Y',      # 3/5/1981
                '%m/%d/%y',      # 3/5/81
                '%Y-%m-%d',      # 1981-3-5
                '%d/%m/%Y',      # 5/3/1981
                '%d/%m/%y',      # 5/3/81
                '%d-%m-%Y',      # 5-3-1981
                '%d-%m-%y',      # 5-3-81
                '%B %d, %Y',     # March 5, 1981
            ]
            
            for fmt in formats:
                try:
                    original_date = datetime.strptime(date_str.strip(), fmt)
                    shifted_date = original_date + timedelta(days=shift_days)
                    return shifted_date.strftime(fmt)
                except ValueError:
                    continue
            
            # If no format matched, return a fake date instead of XX/XX/XXXX
            fake_date = self.context.faker.date_of_birth(minimum_age=18, maximum_age=89)
            return fake_date.strftime('%m-%d-%y')
        except Exception:
            # Last resort: generate a completely fake DOB
            fake_date = self.context.faker.date_of_birth(minimum_age=18, maximum_age=89)
            return fake_date.strftime('%m-%d-%y')
    
    def export_mappings(self, filepath: str):
        with open(filepath, 'w') as f:
            json.dump(self.context.mappings, f, indent=2, default=str)
    
    def get_context_summary(self, original_value: str) -> Optional[Dict]:
        key = self.context._get_key(original_value)
        return self.context.mappings.get(key)


if __name__ == "__main__":
    print("Context-Aware Anonymizer loaded successfully!")
    print("Use with Presidio Analyzer to detect PII, then anonymize with demographic coherence.")