# wc_clinical_deid
Repository for WorldCare AI Team Winter Study '26 internship project.

## Quick Start

### Installation

1. **Create and activate conda environment:**
```bash
conda env create -f env.yml
conda activate deid-pipeline
```

2. **Download spaCy model:**
```bash
python -m spacy download en_core_web_sm
```

3. **Install system dependencies:**
```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr
```

### Usage Options

#### Option 1: Web Application (Recommended)
```bash
./run_app.sh
# Or: streamlit run app.py
```
Then open http://localhost:8501 in your browser.

#### Option 2: Jupyter Notebook
```bash
jupyter notebook model-testing/transformer/pipeline.ipynb
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

### Deactivate Environment
```bash
conda deactivate
```

## Project Structure

- `app.py` - Streamlit web application
- `model-testing/transformer/` - Core pipeline components
  - `pipeline.ipynb` - Interactive notebook workflow
  - `models_config.py` - Model configuration and loading
  - `log_analysis.py` - First/second pass orchestration
  - `context_anonymizer.py` - Context-aware replacement logic
  - `clinical_filter.py` - Medical false positive filtering
- `ocr/` - OCR processing for PDFs/images/DICOM
- `.github/copilot-instructions.md` - AI agent development guide

## Documentation

- **Deployment Guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **AI Agent Instructions**: [.github/copilot-instructions.md](.github/copilot-instructions.md)
- **Pipeline Workflow**: See `model-testing/transformer/pipeline.ipynb`
