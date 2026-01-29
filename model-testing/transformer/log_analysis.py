import json
from datetime import datetime
from presidio_anonymizer import AnonymizerEngine
from presidio_analyzer import PatternRecognizer
from pathlib import Path
from context_anonymizer import ContextAwareAnonymizer
from group_entities import group_names
from clinical_filter import ClinicalDataFilter

def results_to_json(text, results, replacements={}, window=40):
    rows = []
    print(replacements)
    for r in results:
        original_text = text[r.start:r.end]
        # print(original_text, replacements[original_text])
        rows.append({
            "entity_type": r.entity_type,
            "start": r.start,
            "end": r.end,
            "score": float(r.score),
            "text": original_text,
            "left_context": text[max(0, r.start-window):r.start],
            "right_context": text[r.end:r.end+window],
            "replacement": replacements[original_text] if len(replacements) > 0 and original_text in replacements else ""
        })
    return rows

def write_json(path, rows):
    with open(path, "a", encoding="utf-8") as f:
        # for row in rows:
        f.write(json.dumps(rows, ensure_ascii=False) + "\n")

def first_pass(analyzer, text, doc_id, case, language="en", allow_list=[], deny_list=[], window=40):
    if len(deny_list) > 0:
        deny_recognizer = PatternRecognizer(supported_entity="HITL", deny_list=deny_list)
        analyzer.registry.add_recognizer(deny_recognizer)

    results = analyzer.analyze(text=text, language=language, allow_list=allow_list)
    
    # filtered_results = ClinicalDataFilter.filter_results(text, results)
    tagged_person = [text[r.start:r.end] for r in results if r.entity_type == "PERSON"]
    # tagged_location = [text[r.start:r.end] for r in results if r.entity_type in ["LOCATION", "GPE", "US_CITY"]]

    groups = group_names(tagged_person)

    anonymized_text = AnonymizerEngine().anonymize(text=text,analyzer_results=results).text
    Path(f"logs/{case}/{doc_id}").mkdir(parents=True, exist_ok=True)

    json_results = results_to_json(text, results, window=window)
    
    # if doc_id == 1:
    #     with open(f"logs/{case}/original_text.txt", "w", encoding="utf-8") as f:
    #         f.write(text)
    with open(f"logs/{case}/{doc_id}/anonymized_text_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "w", encoding="utf-8") as f:
        f.write(anonymized_text)

    with open(f"logs/{case}/{doc_id}/params.txt", "w", encoding="utf-8") as f:
        f.write(f"language: {language}\n")
        f.write(f"allow_list: {allow_list}\n")
        f.write(f"deny_list: {deny_list}\n")
    
    write_json(f"logs/{case}/{doc_id}/results_{datetime.now().strftime('%Y%m%d_%H%M%S')}", json_results)
    return anonymized_text, groups, doc_id + 1

def second_pass(analyzer, text, doc_id, case, language="en", allow_list=[], deny_list=[], window=40):
    if len(deny_list) > 0:
        deny_recognizer = PatternRecognizer(supported_entity="HITL", deny_list=deny_list)
        analyzer.registry.add_recognizer(deny_recognizer)

    results = analyzer.analyze(text=text, language=language, allow_list=allow_list)
    
    # filtered_results = ClinicalDataFilter.filter_results(text, results)
    tagged_person = [text[r.start:r.end] for r in results if r.entity_type == "PERSON"]
    # tagged_location = [text[r.start:r.end] for r in results if r.entity_type in ["LOCATION", "GPE", "US_CITY"]]

    groups = group_names(tagged_person)

    anonymizer = ContextAwareAnonymizer(groups)

    anonymized_text = anonymizer.anonymize(text=text,analyzer_results=results)

    replacements_dict = anonymizer.replacements

    Path(f"logs/{case}/{doc_id}").mkdir(parents=True, exist_ok=True)

    json_results = results_to_json(text, results, replacements_dict, window=window)
    
    # if doc_id == 1:
    #     with open(f"logs/{case}/original_text.txt", "w", encoding="utf-8") as f:
    #         f.write(text)
    with open(f"logs/{case}/{doc_id}/anonymized_text_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "w", encoding="utf-8") as f:
        f.write(anonymized_text)

    with open(f"logs/{case}/{doc_id}/params.txt", "w", encoding="utf-8") as f:
        f.write(f"language: {language}\n")
        f.write(f"allow_list: {allow_list}\n")
        f.write(f"deny_list: {deny_list}\n")
    
    write_json(f"logs/{case}/{doc_id}/results_{datetime.now().strftime('%Y%m%d_%H%M%S')}", json_results)
    return anonymized_text, groups, doc_id + 1
