# Dependencies: Tesseract (on PATH), pytesseract, Pillow, pdf2image, pydicom 
import sys
import os
import json
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import pydicom
from pydicom.tag import Tag

OUTPUT_DIR = "ocr_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def ocr_image(image, base_name, page_num=None, output_dir=OUTPUT_DIR):
    # saving both json and text for source file
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
        try:
            conf = int(data["conf"][i])
        except ValueError:
            conf = 0

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

    os.makedirs(output_dir, exist_ok=True)
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Save full text
    with open(text_file, "w", encoding="utf-8") as f:
        f.write(full_text)

    print(f"Saved JSON to {json_file} and text to {text_file}")


def main():
    if len(sys.argv) < 2:
        print("python run_ocr.py <input_file>")
        sys.exit(1)

    input_path = sys.argv[1]
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    extension = os.path.splitext(input_path)[1].lower()

    #DICOM
    if extension == ".dcm":
        print("filetype: DICOM")
        try:
            ds = pydicom.dcmread(input_path)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

        # save dicom metadata
        metadata_text = str(ds)
        metadata_path = os.path.join(OUTPUT_DIR, f"{base_name}_metadata.txt")

        with open(metadata_path, "w", encoding="utf-8") as out:
            out.write(metadata_text)

        print(f"Metadata saved to {metadata_path}")

    # PDF
    if extension == ".pdf":
        pdf_output_dir = os.path.join(OUTPUT_DIR, base_name)
        os.makedirs(pdf_output_dir, exist_ok=True)

        pages = convert_from_path(input_path, dpi=300)
        for idx, page_img in enumerate(pages, start=1):
            ocr_image(page_img, base_name, page_num=idx, output_dir=pdf_output_dir)

        print(f"Outputs saved in {pdf_output_dir}")
        return


    img_ext = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}
    if extension not in img_ext:
        return

    try:
        image = Image.open(input_path).convert("RGB")
    except Exception as e:
        print(f"Error opening image: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
