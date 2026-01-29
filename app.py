"""
Clinical De-identification Pipeline - Streamlit Web Application
Follows the workflow from model-testing/transformer/pipeline.ipynb
"""

import streamlit as st
import sys
import os
import tempfile
import shutil
from pathlib import Path
import json
from datetime import datetime

# Add model-testing/transformer to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'model-testing', 'transformer'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'ocr'))

from models_config import stanford_model
from log_analysis import first_pass, second_pass
from match_results import link_json
import subprocess
from PIL import Image
import fitz  # PyMuPDF for PDF rendering

# Page configuration
st.set_page_config(
    page_title="Clinical De-identification Pipeline",
    page_icon="🏥",
    layout="wide"
)

# Initialize session state
if 'stage' not in st.session_state:
    st.session_state.stage = 'upload'
if 'ocr_text' not in st.session_state:
    st.session_state.ocr_text = None
if 'first_pass_results' not in st.session_state:
    st.session_state.first_pass_results = None
if 'case_name' not in st.session_state:
    st.session_state.case_name = f"case_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
if 'temp_dir' not in st.session_state:
    st.session_state.temp_dir = None
if 'uploaded_file_path' not in st.session_state:
    st.session_state.uploaded_file_path = None
if 'ocr_output_dir' not in st.session_state:
    st.session_state.ocr_output_dir = None
if 'original_file_type' not in st.session_state:
    st.session_state.original_file_type = None
if 'redacted_text' not in st.session_state:
    st.session_state.redacted_text = None
if 'base_name' not in st.session_state:
    st.session_state.base_name = None
if 'model_loaded' not in st.session_state:
    st.session_state.model_loaded = False

# Title and description
st.title("🏥 Clinical De-identification Pipeline")
st.markdown("""
**HIPAA-compliant PHI removal from medical documents**  
Upload PDF, image, or DICOM files for automated de-identification with human-in-the-loop review.
""")

# Sidebar - Progress tracker
st.sidebar.title("Pipeline Progress")
stages = {
    'upload': '📤 Upload Document',
    'ocr': '🔍 OCR Processing',
    'first_pass': '🤖 First Pass Detection',
    'review': '👁️ Review & Correct',
    'second_pass': '✅ Second Pass',
    'output': '📥 Download Results'
}

for stage_key, stage_label in stages.items():
    if st.session_state.stage == stage_key:
        st.sidebar.markdown(f"**➡️ {stage_label}**")
    elif list(stages.keys()).index(stage_key) < list(stages.keys()).index(st.session_state.stage):
        st.sidebar.markdown(f"✓ {stage_label}")
    else:
        st.sidebar.markdown(f"⚪ {stage_label}")

# Load model once
@st.cache_resource
def load_model():
    """Load the Stanford model (cached for performance)"""
    return stanford_model

def pdf_to_images(pdf_path, dpi=150):
    """Convert PDF to images for preview"""
    try:
        doc = fitz.open(pdf_path)
        images = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
        doc.close()
        return images
    except Exception as e:
        st.error(f"Error converting PDF to images: {str(e)}")
        return []

def load_original_document(file_path):
    """Load original document for display"""
    file_ext = file_path.split('.')[-1].lower()
    
    if file_ext == 'pdf':
        return pdf_to_images(file_path)
    elif file_ext in ['png', 'jpg', 'jpeg']:
        return [Image.open(file_path)]
    elif file_ext == 'dcm':
        # For DICOM, you'd need pydicom rendering
        st.info("DICOM preview not yet implemented")
        return []
    return []

def generate_redaction_preview(original_path, anonymized_text):
    """Store anonymized text for preview (text-based, not images)"""
    # Returns the anonymized text, not images
    return anonymized_text

# Main content area
if st.session_state.stage == 'upload':
    st.header("Step 1: Upload Document")
    st.markdown("Upload a PDF, image (PNG/JPG), or DICOM file containing clinical text.")
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['pdf', 'png', 'jpg', 'jpeg', 'dcm'],
        help="Supported formats: PDF, PNG, JPG, DICOM"
    )
    
    if uploaded_file is not None:
        st.success(f"Uploaded: {uploaded_file.name}")
        
        # Save to temporary directory
        if st.session_state.temp_dir is None:
            st.session_state.temp_dir = tempfile.mkdtemp()
        st.session_state.original_file_type = uploaded_file.name.split('.')[-1].lower()
        st.session_state.base_name = os.path.splitext(uploaded_file.name)[0]
        
        file_path = os.path.join(st.session_state.temp_dir, uploaded_file.name)
        with open(file_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        st.session_state.uploaded_file_path = file_path
        
        if st.button("Proceed to OCR", type="primary"):
            st.session_state.stage = 'ocr'
            st.rerun()

elif st.session_state.stage == 'ocr':
    st.header("Step 2: OCR Processing")
    st.markdown("Extracting text from your document using Tesseract OCR...")
    
    with st.spinner("Running OCR... This may take a moment."):
        try:
            # Run OCR
            base_name = os.path.splitext(os.path.basename(st.session_state.uploaded_file_path))[0]
            ocr_script = os.path.join(os.path.dirname(__file__), 'model-testing', 'transformer', 'tesseract_test.py')
            
            # Create OCR output directory
            st.session_state.ocr_output_dir = os.path.join(st.session_state.temp_dir, 'ocr_output', base_name)
            os.makedirs(st.session_state.ocr_output_dir, exist_ok=True)
            
            # Run OCR script
            result = subprocess.run(
                ['python', ocr_script, st.session_state.uploaded_file_path],
                cwd=os.path.join(os.path.dirname(__file__), 'model-testing', 'transformer'),
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                st.error(f"OCR failed: {result.stderr}")
            else:
                # Read OCR output
                text_parts = []
                page_num = 1
                while True:
                    text_file = os.path.join('model-testing', 'transformer', 'ocr_output', base_name, f"{base_name}_page{page_num}.txt")
                    if not os.path.exists(text_file):
                        break
                    with open(text_file, 'r') as f:
                        text_parts.append(f.read())
                    page_num += 1
                
                # If no pages found, try single file
                if not text_parts:
                    text_file = os.path.join('model-testing', 'transformer', 'ocr_output', base_name, f"{base_name}.txt")
                    if os.path.exists(text_file):
                        with open(text_file, 'r') as f:
                            text_parts.append(f.read())
                
                st.session_state.ocr_text = "\n".join(text_parts)
                
                st.success(f"✓ OCR completed! Extracted {len(st.session_state.ocr_text)} characters.")
                
                # Show preview
                with st.expander("Preview extracted text"):
                    st.text_area("OCR Output", st.session_state.ocr_text, height=300, disabled=True)
                
                if st.button("Proceed to First Pass", type="primary"):
                    st.session_state.stage = 'first_pass'
                    st.rerun()
                    
        except Exception as e:
            st.error(f"Error during OCR: {str(e)}")
            if st.button("Back to Upload"):
                st.session_state.stage = 'upload'
                st.rerun()

elif st.session_state.stage == 'first_pass':
    st.header("Step 3: First Pass Detection")
    st.markdown("Running transformer model to detect PHI entities...")
    
    if not st.session_state.model_loaded:
        with st.spinner("Loading Stanford model... (this happens once)"):
            model = load_model()
            st.session_state.model_loaded = True
    else:
        model = load_model()
    
    with st.spinner("Analyzing text for PHI..."):
        try:
            anonymized, grouped_names, next_doc_id = first_pass(
                model, 
                st.session_state.ocr_text,
                doc_id=1,
                case=st.session_state.case_name
            )
            
            st.session_state.first_pass_results = {
                'anonymized': anonymized,
                'grouped_names': grouped_names,
                'next_doc_id': next_doc_id
            }
            
            # Load results JSON
            results_dir = f"logs/{st.session_state.case_name}/1/"
            # Store anonymized text for review
            st.session_state.redacted_text = st.session_state.first_pass_results['anonymized']
            
            results_files = [f for f in os.listdir(results_dir) if f.startswith('results_')]
            if results_files:
                with open(os.path.join(results_dir, results_files[0]), 'r') as f:
                    results_data = json.load(f)
                    st.session_state.first_pass_results['entities'] = results_data
            
            st.success(f"✓ First pass completed! Detected {len(results_data)} entities.")
            
            if st.button("Proceed to Review", type="primary"):
                st.session_state.stage = 'review'
                st.rerun()
                
        except Exception as e:
            st.error(f"Error during first pass: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

elif st.session_state.stage == 'review':
    st.header("Step 4: Review & Correct")
    st.markdown("""
    Review detected entities and compare original vs. redacted documents. Add corrections below.
    """)
    
    entities = st.session_state.first_pass_results.get('entities', [])
    
    # Document comparison section
    st.subheader("📄 Document Comparison")
    
    # Display original document and redacted text side by side
    original_images = load_original_document(st.session_state.uploaded_file_path)
    redacted_text = st.session_state.get('redacted_text', '')
    
    col_orig, col_redact = st.columns(2)
    
    with col_orig:
        st.markdown("**Original Document**")
        if original_images:
            page_selector = st.selectbox(
                "Select Page",
                range(1, len(original_images) + 1),
                format_func=lambda x: f"Page {x}"
            )
            st.image(original_images[page_selector - 1], width="stretch")
        else:
            st.info("Original document preview not available")
    
    with col_redact:
        st.markdown("**Redacted Text (First Pass)**")
        st.text_area(
            "Anonymized output",
            redacted_text,
            height=600,
            disabled=True,
            label_visibility="collapsed"
        )
    
    st.divider()
    
    # Display entities by type
    entity_types = set(e['entity_type'] for e in entities)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Detected Entities")
        
        for entity_type in sorted(entity_types):
            with st.expander(f"{entity_type} ({sum(1 for e in entities if e['entity_type'] == entity_type)} found)"):
                type_entities = [e for e in entities if e['entity_type'] == entity_type]
                for i, entity in enumerate(type_entities[:20]):  # Show first 20
                    score = entity['score']
                    text = entity['text']
                    left_ctx = entity['left_context']
                    right_ctx = entity['right_context']
                    st.markdown(f"**{text}** (score: {score:.2f})")
                    st.markdown(f"Context: ...{left_ctx}**[{text}]**{right_ctx}...")
                    st.divider()
                if len(type_entities) > 20:
                    st.info(f"+ {len(type_entities) - 20} more entities")
    
    with col2:
        st.subheader("Corrections")
        
        st.markdown("**Allow List** (false positives)")
        st.caption("Entities that should NOT be redacted")
        allow_list_text = st.text_area(
            "One entity per line",
            height=150,
            key="allow_list",
            placeholder="07:14 AM\n29 y/o\nyesterday"
        )
        
        st.markdown("**Deny List** (false negatives)")
        st.caption("Entities that SHOULD be redacted but were missed")
        deny_list_text = st.text_area(
            "One entity per line",
            height=150,
            key="deny_list",
            placeholder="Dr. Smith\n555-1234\njlee94"
        )
    
    if st.button("Run Second Pass with Corrections", type="primary"):
        # Parse lists
        allow_list = [line.strip() for line in allow_list_text.split('\n') if line.strip()]
        deny_list = [line.strip() for line in deny_list_text.split('\n') if line.strip()]
        
        st.session_state.corrections = {
            'deny_list': deny_list,
            'allow_list': allow_list
        }
        st.session_state.stage = 'second_pass'
        st.rerun()

elif st.session_state.stage == 'second_pass':
    st.header("Step 5: Second Pass")
    st.markdown("Applying corrections and generating final output...")
    model = load_model()
    
    with st.spinner("Applying corrections and generating final output..."):
        try:
            deny_list = st.session_state.corrections['deny_list']
            allow_list = st.session_state.corrections['allow_list']
            
            anonymized, grouped_names, final_doc_id = second_pass(
                model,
                st.session_state.ocr_text,
                case=st.session_state.case_name,
                doc_id=st.session_state.first_pass_results['next_doc_id'],
                allow_list=allow_list,
                deny_list=deny_list
            )
            
            st.session_state.final_results = {
                'anonymized_text': anonymized,
                'doc_id': final_doc_id - 1
            }
            
            st.success("✓ Second pass completed!")
            
            # Show preview
            with st.expander("Preview anonymized text"):
                st.text_area("Anonymized Output", anonymized, height=300, disabled=True)
            
            # Generate final PDF with burned redactions
            with st.spinner("Generating final PDF with redactions..."):
                try:
                    # Link results to OCR output
                    doc_id = st.session_state.final_results['doc_id']
                    case = st.session_state.case_name
                    results_dir = f"logs/{case}/{doc_id}"
                    results_files = [f for f in os.listdir(results_dir) if f.startswith('results_')]
                    
                    if results_files:
                        results_path = os.path.join(results_dir, results_files[0])
                        ocr_base_path = f"model-testing/transformer/ocr_output/{st.session_state.base_name}"
                        
                        if os.path.exists(ocr_base_path):
                            st.info(f"Linking results: {results_path} to OCR: {ocr_base_path}")
                            
                            # Check what JSON files exist in OCR directory
                            ocr_files = [f for f in os.listdir(ocr_base_path) if f.endswith('_ocr.json')]
                            st.info(f"Found OCR JSON files: {ocr_files}")
                            
                            link_json(ocr_base_path, results_path)
                            st.success("✓ Results linked to OCR data")
                    
                    # Run output_layout.py to burn redactions onto PDF
                    if st.session_state.original_file_type == 'pdf':
                        output_script = os.path.join(os.path.dirname(__file__), 'model-testing', 'transformer', 'output_layout.py')
                        
                        # Ensure ocr_base_path exists and has trailing slash
                        if os.path.exists(ocr_base_path):
                            # Verify OCR JSON files have replacement data
                            sample_json = os.path.join(ocr_base_path, f"{st.session_state.base_name}_page1_ocr.json")
                            if os.path.exists(sample_json):
                                with open(sample_json, 'r') as f:
                                    sample_data = json.load(f)
                                    tokens_with_replacements = [t for t in sample_data.get('tokens', []) if t.get('replacement')]
                                    st.info(f"Sample JSON has {len(tokens_with_replacements)} tokens with replacements out of {len(sample_data.get('tokens', []))} total")
                            
                            # Path must be relative to model-testing/transformer/ since that's the cwd
                            ocr_path_relative = f"ocr_output/{st.session_state.base_name}/"
                            
                            st.info(f"Running: python output_layout.py {st.session_state.uploaded_file_path} {ocr_path_relative}")
                            
                            output_result = subprocess.run(
                                ['python', output_script, st.session_state.uploaded_file_path, ocr_path_relative],
                                cwd=os.path.join(os.path.dirname(__file__), 'model-testing', 'transformer'),
                                capture_output=True,
                                text=True
                            )
                            
                            if output_result.returncode == 0:
                                # Output layout script outputs to deid_output/{base_name}/{base_name}_deid.pdf
                                # relative to the model-testing/transformer directory
                                output_pdf_path = os.path.join(os.path.dirname(__file__), 'model-testing', 'transformer', 
                                                              'deid_output', st.session_state.base_name, 
                                                              f"{st.session_state.base_name}_deid.pdf")
                                
                                if os.path.exists(output_pdf_path):
                                    st.session_state.final_pdf_path = output_pdf_path
                                    st.success("✓ Final redacted PDF generated!")
                                else:
                                    # Check if _deid.png files were created
                                    base_dir = os.path.join(os.path.dirname(__file__), 'model-testing', 'transformer', 
                                                           'deid_output', st.session_state.base_name)
                                    if os.path.exists(base_dir):
                                        deid_pngs = [f for f in os.listdir(base_dir) if f.endswith('_deid.png')]
                                        if not deid_pngs:
                                            st.error("❌ insert_from_json() failed silently - no _deid.png files created")
                                            st.warning("This usually means the JSON structure doesn't match what output_layout.py expects")
                                            st.info("**Workaround**: Download the anonymized text below. PDF redaction requires debugging output_layout.py")
                                        else:
                                            st.error(f"Found {len(deid_pngs)} _deid.png files but PDF wasn't assembled")
                                    else:
                                        st.error(f"Output directory doesn't exist: {base_dir}")
                            else:
                                st.warning(f"PDF generation failed: {output_result.stderr}")
                        else:
                            st.warning(f"OCR output directory not found: {ocr_base_path}")
                except Exception as e:
                    st.warning(f"Could not generate PDF: {str(e)}")
            
            if st.button("Proceed to Download", type="primary"):
                st.session_state.stage = 'output'
                st.rerun()
                
        except Exception as e:
            st.error(f"Error during second pass: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

elif st.session_state.stage == 'output':
    st.header("Step 6: Download Results")
    st.markdown("Your de-identified documents are ready!")
    
    doc_id = st.session_state.final_results['doc_id']
    case = st.session_state.case_name
    results_dir = f"logs/{case}/{doc_id}"
    
    # Find files
    anonymized_files = [f for f in os.listdir(results_dir) if f.startswith('anonymized_text_')]
    results_files = [f for f in os.listdir(results_dir) if f.startswith('results_')]
    
    # Primary download - Redacted PDF
    st.subheader("📄 Primary Output")
    if hasattr(st.session_state, 'final_pdf_path') and st.session_state.final_pdf_path and os.path.exists(st.session_state.final_pdf_path):
        with open(st.session_state.final_pdf_path, 'rb') as f:
            st.download_button(
                label="📥 Download Redacted PDF",
                data=f.read(),
                file_name=f"redacted_{st.session_state.base_name}.pdf",
                mime="application/pdf",
                type="primary"
            )
        
        # Show preview
        with st.expander("Preview Redacted Document"):
            pdf_images = pdf_to_images(st.session_state.final_pdf_path)
            for i, img in enumerate(pdf_images):
                st.image(img, caption=f"Page {i+1}", width="stretch")
    else:
        st.warning("Redacted PDF not available. Download text output below.")
    
    st.divider()
    st.subheader("📊 Additional Files")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Anonymized Text**")
        if anonymized_files:
            with open(os.path.join(results_dir, anonymized_files[0]), 'r') as f:
                st.download_button(
                    label="Download Text",
                    data=f.read(),
                    file_name=f"anonymized_{st.session_state.case_name}.txt",
                    mime="text/plain"
                )
    
    with col2:
        st.markdown("**Detection Results**")
        if results_files:
            with open(os.path.join(results_dir, results_files[0]), 'r') as f:
                st.download_button(
                    label="Download JSON",
                    data=f.read(),
                    file_name=f"results_{st.session_state.case_name}.json",
                    mime="application/json"
                )
    
    with col3:
        st.markdown("**Parameters**")
        params_file = os.path.join(results_dir, 'params.txt')
        if os.path.exists(params_file):
            with open(params_file, 'r') as f:
                st.download_button(
                    label="Download Params",
                    data=f.read(),
                    file_name=f"params_{st.session_state.case_name}.txt",
                    mime="text/plain"
                )
    
    st.divider()
    
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔄 Process Another Document", type="primary"):
            # Cleanup
            if st.session_state.temp_dir and os.path.exists(st.session_state.temp_dir):
                shutil.rmtree(st.session_state.temp_dir)
            
            # Reset state
            for key in ['stage', 'ocr_text', 'first_pass_results', 'temp_dir', 
                       'uploaded_file_path', 'ocr_output_dir', 'final_results', 'corrections']:
                if key in st.session_state:
                    del st.session_state[key]
            
            st.session_state.stage = 'upload'
            st.session_state.case_name = f"case_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            st.rerun()
    
    with col_b:
        st.markdown(f"**Results saved in:** `{results_dir}`")

# Footer
st.sidebar.divider()
st.sidebar.markdown("""
### About
Clinical De-identification Pipeline  
Version 1.0  
[Documentation](.github/copilot-instructions.md)
""")
