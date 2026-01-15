# Dependencies: Tessaract (on PATH), pytesseract, Pillow
import sys
import os
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import pydicom
import matplotlib.pyplot as plt


output_directory = "ocr_output"

def main():
    # checking for command line arguments
    if len(sys.argv) < 2:
        print("check arguments: python run_ocr.py <input_file>")
        sys.exit(1)

    input_path = sys.argv[1]
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    extension = os.path.splitext(input_path)[1].lower()
    os.makedirs(output_directory, exist_ok=True)

    # case 1: check for dicom file
    if extension == ".dcm":
        print("filetype: DICOM")
        try:
            ds = pydicom.dcmread(input_path)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

        # save dicom metadata
        metadata_text = str(ds)
        metadata_path = os.path.join(output_directory, f"{base_name}_metadata.txt")

        with open(metadata_path, "w", encoding="utf-8") as out:
            out.write(metadata_text)

        print(f"Metadata saved to {metadata_path}")

        # check for pixel data
        if "PixelData" not in ds:
            print("No pixel data found in DICOM (skip OCR)")
            sys.exit(0)

        # extract pixel data
        try:
            pixel_array = ds.pixel_array
        except Exception as e:
            print(f"Error extracting pixel data: {e}")
            sys.exit(1)

        # show image preview
        # print("Image preview:")

        # plt.figure(figsize=(6, 6))
        # if len(pixel_array.shape) == 3:
        #     plt.imshow(pixel_array)
        # else:
        #     plt.imshow(pixel_array, cmap="gray")

        # plt.title("DICOM Preview (inspect for text)")
        # plt.axis("off")
        # plt.show()

        # ask user whether to run OCR
        # user_input = input("Contains text? Run OCR? (y/n): ").strip().lower()

        # if user_input != "y":
        #     print("OCR was skipped")
        #     sys.exit(0)

        # convert pixel data to PIL image
        try:
            if len(pixel_array.shape) == 3:
                image = Image.fromarray(pixel_array)
            else:
                image = Image.fromarray(pixel_array).convert("L")
        except Exception as e:
            print(f"Error converting pixel data to image: {e}")
            sys.exit(1)

        # run OCR (and check for non whitespace text)
        text = pytesseract.image_to_string(image).strip()
        if len(text) > 0:
            ocr_path = os.path.join(output_directory, f"{base_name}_ocr.txt")
            with open(ocr_path, "w", encoding="utf-8") as out:
                out.write(text)
            print(f"OCR results saved to {ocr_path}")
        else:
            print("No text detected through OCR (no ocr output saved)")
        sys.exit(0)
    

    #msecond case, check for PDf
    images = [] #stores image/pdf page images to convert to PIL

    # open the image --> converting to Pillow img object to pass to tess
    # (raw image data)

    if extension == ".pdf":
        print("filetype: PDF")
        try:
            images = convert_from_path(input_path, dpi=300) # converts each page to PIL
        except Exception as e:
            print(f"Error converting PDF '{input_path}': {e}")
            sys.exit(1)

    else:
        print("filetype: image")
        try:
            image = Image.open(input_path)
            images = [image]
        except Exception as e:
            print(f"Error opening image '{input_path}': {e}")
            sys.exit(1)

    # performing OCR on each image
    

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
