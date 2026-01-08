from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine, DeanonymizeEngine, OperatorConfig
from presidio_anonymizer.operators import Operator, OperatorType

from typing import Dict
from pprint import pprint
replaceDict = {"PERSON": ["Bob", "Kevin", "Kate"], "LOCATION": ["New York", "Boston", "Philly"]}

class InstanceCounterAnonymizer(Operator):
    """
    Anonymizer which replaces the entity value
    with an instance counter per entity.
    """

    # REPLACING_FORMAT = "<{entity_type}_{index}>"
    # REPLACING_FORMAT = replaceDict[entity_type][index]

    def operate(self, text: str, params: Dict = None) -> str:
        """Anonymize the input text."""

        entity_type: str = params["entity_type"]

        # entity_mapping is a dict of dicts containing mappings per entity type
        entity_mapping: Dict[Dict:str] = params["entity_mapping"]

        entity_mapping_for_type = entity_mapping.get(entity_type)
        if not entity_mapping_for_type:
            new_text = replaceDict[entity_type][0]
            entity_mapping[entity_type] = {}

        else:
            if text in entity_mapping_for_type:
                return entity_mapping_for_type[text]

            previous_index = self._get_last_index(entity_mapping_for_type)
            new_text = replaceDict[entity_type][previous_index]
            # self.REPLACING_FORMAT.format(
            #     entity_type=entity_type, index=previous_index + 1
            # )

        entity_mapping[entity_type][text] = new_text
        return new_text

    @staticmethod
    def _get_last_index(entity_mapping_for_type: Dict) -> int:
        """Get the last index for a given entity type."""
        return len(entity_mapping_for_type)

    def validate(self, params: Dict = None) -> None:
        """Validate operator parameters."""

        if "entity_mapping" not in params:
            raise ValueError("An input Dict called `entity_mapping` is required.")
        if "entity_type" not in params:
            raise ValueError("An entity_type param is required.")

    def operator_name(self) -> str:
        return "entity_counter"

    def operator_type(self) -> OperatorType:
        return OperatorType.Anonymize
    
class InstanceCounterDeanonymizer(Operator):
    """
    Deanonymizer which replaces the unique identifier 
    with the original text.
    """

    def operate(self, text: str, params: Dict = None) -> str:
        """Anonymize the input text."""

        entity_type: str = params["entity_type"]

        # entity_mapping is a dict of dicts containing mappings per entity type
        entity_mapping: Dict[Dict:str] = params["entity_mapping"]

        if entity_type not in entity_mapping:
            raise ValueError(f"Entity type {entity_type} not found in entity mapping!")
        if text not in entity_mapping[entity_type].values():
            raise ValueError(f"Text {text} not found in entity mapping for entity type {entity_type}!")

        return self._find_key_by_value(entity_mapping[entity_type], text)

    @staticmethod
    def _find_key_by_value(entity_mapping, value):
        for key, val in entity_mapping.items():
            if val == value:
                return key
        return None
    
    def validate(self, params: Dict = None) -> None:
        """Validate operator parameters."""

        if "entity_mapping" not in params:
            raise ValueError("An input Dict called `entity_mapping` is required.")
        if "entity_type" not in params:
            raise ValueError("An entity_type param is required.")

    def operator_name(self) -> str:
        return "entity_counter_deanonymizer"

    def operator_type(self) -> OperatorType:
        return OperatorType.Deanonymize


def main():
    text = "Peter gave his book to Heidi which later gave it to Nicole. Peter lives in London and Nicole lives in Tashkent."
    print("original text:")
    print(f"\n{text}\n")
    analyzer = AnalyzerEngine()
    analyzer_results = analyzer.analyze(text=text, language="en")
    print("analyzer results:")
    pprint(analyzer_results)

    # Create Anonymizer engine and add the custom anonymizer
    anonymizer_engine = AnonymizerEngine()
    anonymizer_engine.add_anonymizer(InstanceCounterAnonymizer)

    # Create a mapping between entity types and counters
    entity_mapping = dict()

    # Anonymize the text
    anonymized_result = anonymizer_engine.anonymize(
        text,
        analyzer_results,
        {
            "DEFAULT": OperatorConfig(
                "entity_counter", {"entity_mapping": entity_mapping}
            )
        },
    )

    print(f"\n{anonymized_result.text}")

    deanonymizer_engine = DeanonymizeEngine()
    deanonymizer_engine.add_deanonymizer(InstanceCounterDeanonymizer)

    deanonymized = deanonymizer_engine.deanonymize(
        anonymized_result.text, 
        anonymized_result.items, 
        {"DEFAULT": OperatorConfig("entity_counter_deanonymizer", 
                                params={"entity_mapping": entity_mapping})}
    )
    print("anonymized text:")
    pprint(anonymized_result.text)
    print("de-anonymized text:")
    pprint(deanonymized.text)

if __name__ == "__main__":
    main()