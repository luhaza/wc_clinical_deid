# Dependencies: Tessaract (on PATH), pytesseract, Pillow
import sys
import os
from PIL import Image
import pytesseract
from pdf2image import convert_from_path


output_directory = "ocr_output"

def main():
    # checking for command line arguments
    if len(sys.argv) < 2:
        print("check arguments: python run_ocr.py <input_file>")
        sys.exit(1)

    input_path = sys.argv[1]
    extension = os.path.splitext(input_path)[1].lower()
    
    images = [] #stores image/pdf page images to convert to PIL

    # open the image --> converting to Pillow img object to pass to tess
    # (raw image data)

    #check if input is a pdf first (needs conversion)
    if extension == ".pdf":
        try:
            images = convert_from_path(input_path, dpi=300) # converts each page to PIL
        except Exception as e:
            print(f"Error converting PDF '{input_path}': {e}")
            sys.exit(1)

    else:
        try:
            image = Image.open(input_path)
            images = [image]
        except Exception as e:
            print(f"Error opening image '{input_path}': {e}")
            sys.exit(1)

    # performing OCR on each image
    os.makedirs(output_directory, exist_ok=True) # checking output directory exists, creating output file
    base_name = os.path.splitext(os.path.basename(input_path))[0]

    page_num = 1 # starting page count w/ 1

    for image in images:
        text = pytesseract.image_to_string(image)

        if len(images)>1:
            output_file = f"{base_name}_page{page_num}.txt"
        else:
            output_file = f"{base_name}.txt"
        

        output_file_path = os.path.join(output_directory, output_file)

        # writing resutls to output file
        with open(output_file_path, "w", encoding="utf-8") as out:
            out.write(text)

        page_num += 1

    print(f"Results saved to ocr_output")

if __name__ == "__main__":
    main()
