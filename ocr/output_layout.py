import os
import sys
import json
import re
from PIL import Image, ImageDraw, ImageFont
from pdf2image import convert_from_path


OUTPUT_DIR = "deid_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# for image/pdf conversion
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

    # scaling font!!
    try:
        font_path = "arial.ttf"  #works w/ any .ttf font I think
        base_font = ImageFont.truetype(font_path, size=10)
    except Exception:
        base_font = ImageFont.load_default()

    
    # for redacted text the replacement is a numebr of asteristks equal to original length
    for token in tokens:
        original_text = token.get("text")
        replacement_text = token.get("replacement")

        if replacement_text == original_text:
            continue


        x, y = token.get("left", 0), token.get("top", 0)
        w, h = token.get("width", 0), token.get("height", 0)

        org_len = len(original_text)

        if(replacement_text == ("*"*org_len)):
            draw.rectangle([x, y, x + w, y + h], fill="black")
        else:
            draw.rectangle([x, y, x + w, y + h], fill="white")

        # calculate font size
        font_size = max(1, int(h * 1))  # 1:1 w/ box --> change if too big/small!
        try:
            font = ImageFont.truetype(font_path, size=font_size)
        except Exception:
            font = base_font  # fallback font


        bbox = draw.textbbox((0, 0), replacement_text, font=font)
        text_height = bbox[3] - bbox[1]
        y_offset = y + (h - text_height) // 2

        draw.text((x, y_offset), replacement_text, font=font, fill="black")

    img.save(output_path)
    print(f"Saved to: {output_path}")

def main():
    input_path = sys.argv[1]
    data_path = sys.argv[2]
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    extension = os.path.splitext(input_path)[1].lower()

    #handing images
    if extension in [".png", ".jpg", ".jpeg"]:
        output_file = os.path.join(OUTPUT_DIR, f"{base_name}_deid.png")
        insert_from_json(input_path, data_path, output_file)
        return

    # handling PDFs
    if extension == ".pdf":
        pdf_output_dir = os.path.join(OUTPUT_DIR, base_name)
        os.makedirs(pdf_output_dir, exist_ok=True)

        pages = convert_from_path(input_path, dpi=300)
        deid_images = []

        for idx, page_img in enumerate(pages, start=1):
            page_file = os.path.join(pdf_output_dir, f"{base_name}_page{idx}.png")
            page_img.save(page_file)

            # load corresponding json
            json_file = os.path.join(data_path, f"{base_name}_page{idx}_ocr.json")
            if not os.path.isfile(json_file):
                print(f"No JSON for page {idx}, skipping")
                continue

            output_file = os.path.join(pdf_output_dir, f"{base_name}_page{idx}_deid.png")
            insert_from_json(page_file, json_file, output_file)

            # compiling into PDF
            deid_img = Image.open(output_file).convert("RGB")
            deid_images.append(deid_img)


        if deid_images:
            pdf_output_path = os.path.join(pdf_output_dir, f"{base_name}_deid.pdf")
            first_page, rest_pages = deid_images[0], deid_images[1:]
            first_page.save(pdf_output_path, save_all=True, append_images=rest_pages)
            print(f"output PDF saved to {pdf_output_path}")

        print(f"Outputs saved in {pdf_output_dir}")
        return

if __name__ == "__main__":
    main()
