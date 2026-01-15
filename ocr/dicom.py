import sys
import os
import pydicom
from PIL import Image
import pytesseract
import matplotlib.pyplot as plt

output_directory = "dicom_output"

def main():
    if len(sys.argv) < 2:
        print("check arguments: python run_dicom.py <dicom_file>")
        sys.exit(1)

    input_path = sys.argv[1]
    base_name = os.path.splitext(os.path.basename(input_path))[0]

    os.makedirs(output_directory, exist_ok=True)

    # open dicom file
    try:
        ds = pydicom.dcmread(input_path)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    # save dicom metadata to txt
    metadata_text = str(ds)
    metadata_path = os.path.join(output_directory, f"{base_name}_metadata.txt")

    with open(metadata_path, "w", encoding="utf-8") as out:
        out.write(metadata_text)

    print(f"Metadata saved to {metadata_path}")

    # check for pixel data
    # possible for text to be embedded in dicom image --> ocr
    if "PixelData" not in ds:
        print("No pixel data found in DICOM (skip OCR)")
        sys.exit(0)

    # extract pixel data 
    try:
        pixel_array = ds.pixel_array
    except Exception as e:
        print(f"Error eextracting pixel data: {e}")
        sys.exit(1)

    print("Image preview:")

    plt.figure(figsize=(6, 6))
    # check if RBG -  (h,w,channel)
    if len(pixel_array.shape) == 3:
        plt.imshow(pixel_array)
    else:
        plt.imshow(pixel_array, cmap="gray")

    plt.title("DICOM Preview (inspect for text)")
    plt.axis("off")
    plt.show()

    # prompts user to confirm whether or not there is text
    user_input = input("Contains text? Run OCR? (y/n): ").strip().lower()

    if user_input != "y":
        print("OCR was skipped")
        sys.exit(0)

    #running ocr
    try:
        if len(pixel_array.shape) == 3:
            image = Image.fromarray(pixel_array)
        else:
            # using 8 bit grayscale
            image = Image.fromarray(pixel_array).convert("L")
    except Exception as e:
        print(f"Error converting pixel data to image: {e}")
        sys.exit(1)


    text = pytesseract.image_to_string(image)
    ocr_path = os.path.join(output_directory, f"{base_name}_ocr.txt")

    with open(ocr_path, "w", encoding="utf-8") as out:
        out.write(text)

    print(f"OCR results saved to {ocr_path}")

if __name__ == "__main__":
    main()
