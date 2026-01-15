from dataclasses import dataclass

# Helper functions to run parallel PII/PHI deidentification-
# Stanford model is trained on radiology & biomedical documents
# ab-ai model is more general, but achieves higher recall on PII
@dataclass
class Span:
    start: int
    end: int
    length: int
    entity_type: str
    score: float
    source: str

def to_spans(results):
    """
    Transforms Microsoft Presidio AnalyzerEngine results to custom Span data structure for comparison
    
    Params
    results: results from AnalyzerEngine
    
    returns Span wrapper of result
    """
    return [Span(r.start, r.end, r.end-r.start, r.entity_type, float(r.score)) for r in results]

def merge_spans(spans_a, spans_b, prefer=None):
    """
    Merges the results of two models

    Params:
    spans_a: Span of model A
    spans_b: Span of model B
    prefer: optional dict like {"PERSON": "A", "PHONE_NUMBER": "B"} to prefer one model per entity_type.

    returns list of merged spans
    """
    all_spans = spans_a + spans_b

    # sort by start, then longest first, then score
    # this allows us to process longer spans first, like "John Doe" vs "John"
    # 
    all_spans.sort(key=lambda s: (s.start, -(s.length), -s.score))

    merged = []
    for s in all_spans:
        overlap = False
        for m in merged:
            if not (s.end <= m.start or s.start >= m.end):
                # overlapping spans -> decide winner
                overlap = True

                # if we select an entity to be preferred
                if prefer and s.entity_type in prefer:
                    winner = s if prefer[s.entity_type] == s.source else m
                    loser  = m if winner is s else s

                else:
                    if s.length != m.length:
                        winner = s if s.length > m.length else m
                        loser  = m if winner is s else s
                    else:
                        winner = s if s.score > m.score else m
                        loser  = m if winner is s else s

                if winner is s:
                    merged.remove(loser)
                    merged.append(winner)
                break

        if not overlap:
            merged.append(s)

    merged.sort(key=lambda s: (s.start, s.end))
    return merged
