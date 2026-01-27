import json
from datetime import datetime
from presidio_anonymizer import AnonymizerEngine
from presidio_analyzer import PatternRecognizer
from pathlib import Path
from context_anonymizer import ContextAwareAnonymizer
from group_entities import group_names
from clinical_filter import ClinicalDataFilter

def results_to_json(text, results, window=40):
    rows = []
    for r in results:
        rows.append({
            "entity_type": r.entity_type,
            "start": r.start,
            "end": r.end,
            "score": float(r.score),
            "text": text[r.start:r.end],
            "left_context": text[max(0, r.start-window):r.start],
            "right_context": text[r.end:r.end+window],
            "replacement": text[r.start:r.end]  # Placeholder; actual replacement can be filled in later
        })
    return rows

def write_json(path, rows):
    with open(path, "a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

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

    print(anonymizer.replacements)

    Path(f"logs/{case}/{doc_id}").mkdir(parents=True, exist_ok=True)

    json_results = results_to_json(anonymized_text, results, window=window)
    
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

import json
import re
from typing import Dict, List, Tuple

def _norm_token(s: str) -> str:
    """
    Normalize token text for matching.
    - lowercase
    - remove non-alphanumerics (keep digits/letters)
    """
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s

def _phrase_to_norm_tokens(phrase: str) -> List[str]:
    # split phrase into rough tokens, normalize each
    raw = re.split(r"\s+", phrase.strip())
    out = [_norm_token(t) for t in raw if _norm_token(t)]
    return out

def insert_phrase_replacements_into_json(
    json_in_path: str,
    json_out_path: str,
    replacements: Dict[str, str],
    overwrite_existing: bool = True,
    placeholder_mode: str = "whole_span",
):
    """
    Updates OCR token JSON with replacements.

    Params:
      replacements: dict original_entity -> replacement
        - original_entity may contain multiple words.
      placeholder_mode:
        - "whole_span": put replacement text in first token, blank out the rest
                        (best for image burn-in; avoids overflow)
        - "repeat": write same replacement into every token in span
    """

    with open(json_in_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tokens = data.get("tokens", [])
    if not tokens:
        raise ValueError("No tokens found in JSON")

    # Build normalized token stream
    token_norm = [_norm_token(t.get("text", "")) for t in tokens]

    # Sort phrases by length (longest first) to avoid partial matches
    phrase_items: List[Tuple[str, str]] = sorted(
        replacements.items(),
        key=lambda kv: len(_phrase_to_norm_tokens(kv[0])),
        reverse=True,
    )

    occupied = [False] * len(tokens)  # to prevent overlapping replacements (optional)

    for original, repl in phrase_items:
        phrase_norm = _phrase_to_norm_tokens(original)
        if not phrase_norm:
            continue

        L = len(phrase_norm)

        # sliding window match
        i = 0
        while i <= len(tokens) - L:
            # skip if window overlaps a prior matched span
            if any(occupied[i:i+L]):
                i += 1
                continue

            window = token_norm[i:i+L]

            if window == phrase_norm:
                # apply replacement over tokens i..i+L-1
                if placeholder_mode == "repeat":
                    for k in range(i, i + L):
                        if overwrite_existing or tokens[k].get("replacement") == tokens[k].get("text"):
                            tokens[k]["replacement"] = repl
                else:
                    # "whole_span": best for your burn-in script
                    # replacement goes in first token, blank out rest
                    if overwrite_existing or tokens[i].get("replacement") == tokens[i].get("text"):
                        tokens[i]["replacement"] = repl
                    for k in range(i + 1, i + L):
                        if overwrite_existing or tokens[k].get("replacement") == tokens[k].get("text"):
                            tokens[k]["replacement"] = ""  # means "erase" in burn-in

                for k in range(i, i + L):
                    occupied[k] = True

                i += L
                continue

            i += 1

    # Write output
    data["tokens"] = tokens
    with open(json_out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return json_out_path
