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

# bbox helpers:
def same_line(t1, t2, tolerance=0.6):
    return abs(t1["top"] - t2["top"]) <= t1["height"] * tolerance 
    #can change tolerance to troubleshoot bbox line issues

def is_left_jump(curr, nxt, slack=2):
    return nxt["left"] < curr["left"] - slack

def is_empty(token):
    return not token.get("replacement") or token.get("replacement").strip() == ""


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

    skipped = set()

    i = 0
    while i < len(tokens):
        if i in skipped:
            i += 1
            continue

        token = tokens[i]
        replacement_text = token.get("replacement")
        original_text = token.get("text")

        if not replacement_text or replacement_text == original_text:
            i += 1
            continue

        # base bounding box
        x = token["left"]
        y = token["top"]
        w = token["width"]
        h = token["height"]

        x_left = x
        x_right = x + w
        y_top = y
        y_bottom = y + h

        j = i + 1

        #checking boxes to add to final bbox size calculation
        while j < len(tokens):
            next_token = tokens[j]

            # stop if non-empty
            if not is_empty(next_token):
                break

            # stop if different line
            if not same_line(token, next_token):
                break

            # stop if box is to the left
            if is_left_jump(token, next_token):
                break


            skipped.add(j)

            nx, ny, nw, nh = (
                next_token["left"],
                next_token["top"],
                next_token["width"],
                next_token["height"],
            )

            x_left = min(x_left, nx)
            x_right = max(x_right, nx + nw)
            y_top = min(y_top, ny)
            y_bottom = max(y_bottom, ny + nh)

            j += 1

        # final box bbox dimensions
        x = x_left
        y = y_top
        w = x_right - x_left
        h = y_bottom - y_top

        # redaction
        if replacement_text == "*":
            draw.rectangle([x, y, x + w, y + h], fill="black")
            i += 1
            continue

        draw.rectangle([x, y, x + w, y + h], fill="white")
        font_size = max(1, int(h * 1.3))
        font = base_font

        try:
            font = ImageFont.truetype(font_path, size=font_size)
            while font.getbbox(replacement_text)[2] > w and font_size > 15:
                font_size -= 1
                font = ImageFont.truetype(font_path, size=font_size)
            # optional string split and new line 
            if font.getbbox(replacement_text)[2] > w:
                length = len(replacement_text)
                replacement_text = replacement_text[:length//2]+'-\n'+ replacement_text[length//2:]
        except Exception:
            pass

        bbox = draw.textbbox((0, 0), replacement_text, font=font)
        text_height = bbox[3] - bbox[1]
        y_offset = y + (h - text_height) // 2 - h * 0.15

        draw.text((x, y_offset), replacement_text, font=font, fill="black")
        i+=1

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
