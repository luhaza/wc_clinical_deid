# Dependencies: Tesseract (on PATH), pytesseract, Pillow, pdf2image, pydicom
import sys
import os
import json
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import pydicom

OUTPUT_DIR = "ocr_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def ocr_image(image, base_name, page_num=None, output_dir=OUTPUT_DIR):
   #saving both json and text for source file
    if page_num:
        json_file = os.path.join(output_dir, f"{base_name}_page{page_num}_ocr.json")
        text_file = os.path.join(output_dir, f"{base_name}_page{page_num}.txt")
    else:
        json_file = os.path.join(output_dir, f"{base_name}_ocr.json")
        text_file = os.path.join(output_dir, f"{base_name}.txt")
    data = pytesseract.image_to_data(
        image,
        output_type=pytesseract.Output.DICT
    )

    tokens = []
    full_text_parts = []
    char_cursor = 0

    n = len(data["text"])

    for i in range(n):
        word = data["text"][i].strip()
        conf = int(data["conf"][i])

        if not word or conf <= 0:
            continue

        if full_text_parts:
            full_text_parts.append(" ")
            char_cursor += 1

        start = char_cursor
        full_text_parts.append(word)
        char_cursor += len(word)
        end = char_cursor

        tokens.append({
            "text": word,
            "char_start": start,
            "char_end": end,
            "left": data["left"][i],
            "top": data["top"][i],
            "width": data["width"][i],
            "height": data["height"][i],
            "conf": conf,
            "replacement": word  # for later deid insertion
        })

    full_text = "".join(full_text_parts)

    # json format
    output = {
        "full_text": full_text,
        "tokens": tokens
    }

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Save full text
    with open(text_file, "w", encoding="utf-8") as f:
        f.write(full_text)

    print(f"Saved JSON to {json_file} and text to {text_file}")


def save_dicom_metadata(ds, base_name):
    # dicom metadata to text
    # does not handel pixel data
    # not compatible with output_layout atm. 
    meta_file = os.path.join(OUTPUT_DIR, f"{base_name}_dicom_metadata.txt")
    with open(meta_file, "w", encoding="utf-8") as f:
        for elem in ds.iterall():
            # Only write tags with values
            if elem.value not in [None, ""]:
                f.write(f"{elem}\n")
    print(f"Saved DICOM metadata to {meta_file}")


def main():
    if len(sys.argv) < 2:
        print("python run_ocr.py <input_file>")
        sys.exit(1)

    input_path = sys.argv[1]
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    extension = os.path.splitext(input_path)[1].lower()

    # handling DICOM
    if extension == ".dcm":
        print("Processing DICOM...")
        ds = pydicom.dcmread(input_path)
        save_dicom_metadata(ds, base_name)

        if "PixelData" not in ds:
            print("No pixel data found in DICOM, metadata saved")
            return

        pixel_array = ds.pixel_array
        image = (
            Image.fromarray(pixel_array)
            if len(pixel_array.shape) == 3
            else Image.fromarray(pixel_array).convert("L")
        )
        ocr_image(image, base_name)
        return

    # handling PDF
    if extension == ".pdf":
        # Create a subfolder for this PDF (used for output_layout)
        pdf_output_dir = os.path.join(OUTPUT_DIR, base_name)
        os.makedirs(pdf_output_dir, exist_ok=True)

        pages = convert_from_path(input_path, dpi=300)
        for idx, page_img in enumerate(pages, start=1):
            # pass subfolder as output dir
            ocr_image(page_img, base_name, page_num=idx, output_dir=pdf_output_dir)
        print(f"Outputs saved in {pdf_output_dir}")
        return
    # handling single images
    try:
        image = Image.open(input_path).convert("RGB")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    ocr_image(image, base_name)


if __name__ == "__main__":
    main()

