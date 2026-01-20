import sys
import os
from PIL import Image
import cv2
import numpy as np

# Preprocessing using OpenCV & Pillow
def preprocess_image_cv(input_path, output_path=None, max_size=(2000, 2000), apply_clahe=True):
    try:
        # Read image with OpenCV
        img_cv = cv2.imread(input_path, cv2.IMREAD_COLOR)
        if img_cv is None:
            raise ValueError(f"Failed to read image: {input_path}")
        
        # resizing (if too large))
        h, w = img_cv.shape[:2]
        if max(h, w) > max(max_size):
            scale = min(max_size[0] / w, max_size[1] / h)
            img_cv = cv2.resize(img_cv, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

        # convert to grayscale
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

        # low-impact denoising
        gray = cv2.fastNlMeansDenoising(gray, h=10)

        # optional contrast enhancement
        if apply_clahe:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)

        # convert to PIL Image for Tesseract/saving
        pil_img = Image.fromarray(gray)

        if output_path:
            pil_img.save(output_path)

        return pil_img

    except Exception as e:
        print(f"Error preprocessing image: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("python preprocess_cv.py <image_file>")
        sys.exit(1)

    input_path = sys.argv[1]
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_path = f"{base_name}_processed.png"

    processed = preprocess_image_cv(input_path, output_path=output_path)
    
    if processed:
        print(f"Saved preprocessed image to {output_path}")
