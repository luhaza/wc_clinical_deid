# Dependencies: Tessaract (on PATH), pytesseract, Pillow
import sys
import os
from PIL import Image
import pytesseract


output_directory = "ocr_output"

def main():
    # checking for command line arguments
    if len(sys.argv) < 2:
        print("check arguments: python run_ocr.py <image_file>")
        sys.exit(1)

    image_path = sys.argv[1]

    # open the image --> converting to Pillow img object to pass to tess
    # (raw image data)
    try:
        image = Image.open(image_path)
    except Exception as e:
        print(f"Error opening image '{image_path}': {e}")
        sys.exit(1)

    # performing OCR
    # pytesseract will find Tesseract automatically via PATH
    text = pytesseract.image_to_string(image)

    # checking output directory exists, creating output file
    os.makedirs(output_directory, exist_ok=True)

    # output text file has same name as input image file
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    output_file_path = os.path.join(output_directory, f"{base_name}.txt")

    # writing resutls to output file
    with open(output_file_path, "w", encoding="utf-8") as out:
        out.write(text)

    print(f"Result saved to: {output_file_path}")

if __name__ == "__main__":
    main()
