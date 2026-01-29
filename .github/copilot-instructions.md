# Clinical De-identification Pipeline - AI Agent Instructions

## Project Overview
Clinical text de-identification system using Microsoft Presidio and Stanford transformer models (StanfordAIMI/stanford-deidentifier-base) for HIPAA-compliant PHI removal from medical documents. Supports OCR pre-processing for PDFs, images, and DICOM files.

## Architecture & Data Flow

### Three-Stage Pipeline
1. **OCR Stage** (`ocr/`, `model-testing/transformer/tesseract_test.py`):
   - Converts PDFs/images/DICOM → structured text with positional metadata
   - Uses Tesseract OCR with character-level position tracking
   - Outputs: JSON with tokens (text, coordinates, confidence) + plain text
   - Key challenge: Word-level chunking vs. multi-word entity spans

2. **PII Detection** (`model-testing/transformer/`):
   - **First Pass**: Transformer model detects all PHI entities
   - **Human-in-the-Loop**: User reviews false positives/negatives
   - **Second Pass**: Re-runs with user's allow_list/deny_list corrections
   - Uses Presidio analyzer with custom medical recognizers

3. **Anonymization & Output** (`context_anonymizer.py`, `output_layout.py`):
   - Contextually coherent replacements (same person → same fake name)
   - Preserves temporal relationships (consistent date shifts per patient)
   - Maps replacements back to OCR coordinates for PDF "burning"

### Critical Files
- `models_config.py`: Analyzer configuration, model loading, entity mappings
- `recognizers.py`: Custom regex patterns for MRN, DOB, addresses (medical-specific)
- `clinical_filter.py`: Removes false positives (durations, relative times, ages <89)
- `group_entities.py`: Fuzzy matches name variants (e.g., "Dr. Smith" ↔ "Smith")
- `log_analysis.py`: first_pass() and second_pass() orchestration with logging

## Development Workflow

### Environment Setup
```bash
conda env create -f env.yml
conda activate deid-pipeline
```

### Running the Pipeline
Primary workflow is in `model-testing/transformer/pipeline.ipynb`:
1. Load model: `from models_config import stanford_model as model`
2. OCR: `!python tesseract_test.py data/sample_pdf.pdf`
3. First pass: `first_pass(model, text, doc_id=1, case="sample")`
4. Review output, create allow_list/deny_list
5. Second pass: `second_pass(model, text, case="sample", doc_id=2, allow_list=[], deny_list=[])`
6. Match results: `link_json("ocr_output/sample_pdf", "logs/sample/2/results_...")`
7. Generate output: `!python output_layout.py data/sample_pdf.pdf ocr_output/sample_pdf/`

### Logging Structure
Results stored in `logs/{case}/{doc_id}/`:
- `results_YYYYMMDD_HHMMSS`: JSON with entities, scores, context windows
- `anonymized_text_YYYYMMDD_HHMMSS.txt`: Redacted output
- `params.txt`: allow_list, deny_list, language settings

## Project-Specific Conventions

### Entity Type Mappings
Stanford model outputs (e.g., "PATIENT", "DOCTOR") → Presidio standard types (e.g., "PERSON"):
```python
# See configurations.py STANFORD_COFIGURATION["MODEL_TO_PRESIDIO_MAPPING"]
"PATIENT" → "PERSON"
"HCW" → "PERSON"  # Healthcare worker
"HOSPITAL" → "LOCATION"
"PHONE" → "PHONE_NUMBER"
```

### False Positive Prevention
Medical context requires aggressive filtering (see `clinical_filter.py`):
- **Preserve**: Relative times ("yesterday"), durations ("2 weeks"), ages <89
- **Remove**: Medication names, test results, vitals mistakenly tagged as PHI
- Conflict resolution: If same text tagged as multiple types, choose most specific

### Name Grouping
Use fuzzy matching to treat name variants as single entity:
```python
# group_entities.py uses rapidfuzz with score_cutoff=60
["Dr. John Smith", "John Smith", "Smith"] → same replacement
```

### Context-Aware Anonymization
`DemographicContext` class ensures:
- Same person always gets same fake name (not random each time)
- Same patient gets consistent date shift (preserves intervals)
- Name groupings passed from first_pass to anonymizer

## Common Pitfalls

1. **OCR-to-Entity Mapping**: OCR tokens are word-level, entities can span multiple words → `match_results.py` handles alignment (currently in progress)

2. **Custom Recognizers**: Add to `models_config.py` via `recognizers` parameter:
```python
registry.add_recognizer(MedicalRecognizers.get_mrn_recognizer())
```

3. **Presidio Re-Analysis**: `anonymizer.anonymize()` re-runs analysis by default → Use `ContextAwareAnonymizer` to replace at exact positions only

4. **Filter Order**: Apply `ClinicalDataFilter.filter_results()` AFTER model analysis but BEFORE anonymization

5. **Dependency Installation**: Tesseract must be on PATH (not just Python package). Install via `brew install tesseract` on macOS.

## Key Dependencies
- **Presidio**: analyzer + anonymizer (Microsoft's PII detection framework)
- **Transformers**: HuggingFace for Stanford/BERT NER models
- **Tesseract**: OCR engine (system-level install required)
- **spaCy**: Tokenization (en_core_web_sm)
- **scispacy/medspacy**: Medical NLP support
- **rapidfuzz**: Name variant matching

## Testing & Evaluation
- Sample data: `model-testing/sample_data/` (10 synthetic medical notes)
- Evaluation notebooks: `model-testing/transformer/eval/faker_synth_data_eval.ipynb`
- Run specific test: Open `pipeline.ipynb` and modify `data/sample.txt` path

## Web Application Deployment

### Streamlit Interface
Interactive web app (`app.py`) follows the notebook workflow:
```bash
# Launch locally
./run_app.sh
# Or manually:
streamlit run app.py
```

**User Flow**:
1. Upload PDF/image/DICOM → OCR extraction
2. First pass detection → Entity preview
3. **Human review** → Side-by-side document comparison (original vs. redacted)
   - Visual identification of false negatives
   - Add corrections (allow_list/deny_list)
4. Second pass → Contextually anonymized output
5. **Download redacted PDF** with burned-in black boxes over PHI
   - Also available: text, JSON, params

**Key Features**:
- **Side-by-side document comparison** during review stage
- Real-time entity review interface
- Batch corrections via text area inputs
- **Final PDF generation** with burned redactions via `output_layout.py`
- Page-by-page preview with PDF-to-image conversion (PyMuPDF)

**Configuration**: See `.streamlit/config.toml` for upload limits (default: 200MB)

**Requirements**: `requirements-streamlit.txt` includes all dependencies. System-level Tesseract still required.

**Key Implementation Details**:
- Uses `pdf_to_images()` for document preview rendering
- Calls `match_results.link_json()` to map entities to OCR coordinates
- Executes `output_layout.py` subprocess to burn redactions onto PDF
- Final output: `model-testing/transformer/deid_output/{filename}_redacted.pdf`
**Configuration**: See `.streamlit/config.toml` for upload limits (default: 200MB)

**Requirements**: `requirements-streamlit.txt` includes all dependencies. System-level Tesseract still required.
