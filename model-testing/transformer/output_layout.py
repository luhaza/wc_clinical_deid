import os
import sys
import json
import re
from PIL import Image, ImageDraw, ImageFont
from pdf2image import convert_from_path

from pydicom import dcmread
from pydicom.tag import Tag

OUTPUT_DIR = "deid_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

VERBOSE = True

#Dicom

def is_group_length(tag):
    return tag.element == 0x0000

def is_pixel_data(tag):
    return tag == Tag(0x7FE0, 0x0010)

def is_file_meta(tag):
    return tag.group == 0x0002

LINE_RE = re.compile(
    r"\((?P<group>[0-9A-Fa-f]{4}),(?P<elem>[0-9A-Fa-f]{4})\)\s+.*?\s(?P<vr>[A-Z]{2}):\s(?P<val>.+)$"
)

def normalize(val):
    return val.strip().strip("'").strip('"')

def dicom_to_text_map(ds):
    values = {}
    for elem in ds.iterall():
        tag = elem.tag
        if is_group_length(tag) or is_pixel_data(tag) or is_file_meta(tag):
            continue
        try:
            values[tag] = normalize(str(elem.value))
        except Exception:
            pass
    return values

def load_edited_text(txt_path):
    edits = {}
    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            m = LINE_RE.search(line)
            if not m:
                continue

            tag = Tag(
                int(m.group("group"), 16),
                int(m.group("elem"), 16)
            )

            if is_group_length(tag) or is_pixel_data(tag) or is_file_meta(tag):
                continue

            edits[tag] = normalize(m.group("val"))

    return edits

def apply_dicom_changes(ds, original_map, edited_map):
    for tag, new_val in edited_map.items():
        if tag not in ds:
            continue

        old_val = original_map.get(tag)

        if old_val == new_val:
            continue

        elem = ds[tag]

        # never allow invalid UI
        if elem.VR == "UI" and not re.match(r"^\d+(\.\d+)*$", new_val):
            continue

        elem.value = new_val



def redact_dicom(dicom_path, edited_txt_path, output_path):
    ds = dcmread(dicom_path)
    # extracting original values
    original_map = dicom_to_text_map(ds)
    edited_map = load_edited_text(edited_txt_path)
    apply_dicom_changes(ds, original_map, edited_map)

    ds.save_as(output_path)
    print(f"Saved DICOM to: {output_path}")

#image/PDF
def insert_from_json(image_path, json_path, output_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tokens = data.get("tokens", [])

    try:
        img = Image.open(image_path).convert("RGB")
    except Exception as e:
        print(f"Error: {image_path}, {e}")
        return

    draw = ImageDraw.Draw(img)

    try:
        font_path = 'fonts/arial.ttf'
        base_font = ImageFont.truetype(font_path, size=10)
    except Exception:
        base_font = ImageFont.load_default()

    for token in tokens:
        original_text = token.get("text")
        replacement_text = token.get("replacement")

        if replacement_text == original_text:
            continue

        x, y = token.get("left"), token.get("top")
        w, h = token.get("width"), token.get("height")

        if replacement_text == "*":
            draw.rectangle([x, y, x + w, y + h], fill="black")
            continue

        draw.rectangle([x, y, x + w, y + h], fill="white")

        font_size = max(1, int(h * 1.3))
        font = base_font

        try:
            font = ImageFont.truetype(font_path, size=font_size)
            while font.getbbox(replacement_text)[2] > w and font_size > 2:
                font_size -= 1
                font = ImageFont.truetype(font_path, size=font_size)
        except Exception:
            pass

        bbox = draw.textbbox((0, 0), replacement_text, font=font)
        text_height = bbox[3] - bbox[1]
        y_offset = y + (h - text_height) // 2 - h * 0.15

        draw.text((x, y_offset), replacement_text, font=font, fill="black")

    img.save(output_path)
    print(f"Saved to: {output_path}")

#Main

def main():
    input_path = sys.argv[1]
    data_path = sys.argv[2]

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    extension = os.path.splitext(input_path.strip())[1].lower()

    # DICOM
    if extension == ".dcm":
        output_file = os.path.join(OUTPUT_DIR, f"{base_name}_deid.dcm")
        redact_dicom(input_path, data_path, output_file)
        return

    # Images
    if extension in [".png", ".jpg", ".jpeg"]:
        output_file = os.path.join(OUTPUT_DIR, f"{base_name}_deid.png")
        insert_from_json(input_path, data_path, output_file)
        return

    # PDFs
    if extension == ".pdf":
        pdf_output_dir = os.path.join(OUTPUT_DIR, base_name)
        os.makedirs(pdf_output_dir, exist_ok=True)

        pages = convert_from_path(input_path, dpi=300)
        deid_images = []

        for idx, page_img in enumerate(pages, start=1):
            page_file = os.path.join(pdf_output_dir, f"{base_name}_page{idx}.png")
            page_img.save(page_file)

            json_file = os.path.join(data_path, f"{base_name}_page{idx}_ocr.json")
            if not os.path.isfile(json_file):
                continue

            output_file = os.path.join(pdf_output_dir, f"{base_name}_page{idx}_deid.png")
            insert_from_json(page_file, json_file, output_file)

            deid_images.append(Image.open(output_file).convert("RGB"))

        if deid_images:
            pdf_output_path = os.path.join(pdf_output_dir, f"{base_name}_deid.pdf")
            deid_images[0].save(
                pdf_output_path,
                save_all=True,
                append_images=deid_images[1:]
            )
            print(f"Saved PDF to: {pdf_output_path}")

if __name__ == "__main__":
    main()
