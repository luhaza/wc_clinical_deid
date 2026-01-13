import sys
import os
import pydicom

output_directory = "dicom_output"

# extracting metadata from dicom file
def main():
    if len(sys.argv) < 2:
        print("Check arguments: python dicom.py <dicom_file>")
        sys.exit(1)

    input_path = sys.argv[1]
    base_name = os.path.splitext(os.path.basename(input_path))[0]

    os.makedirs(output_directory, exist_ok=True)

    try:
        ds = pydicom.dcmread(input_path) # checking if input is valid dicom
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    # extracting metadata
    metadata_text = str(ds)
    output_file = os.path.join(output_directory, f"{base_name}_metadata.txt")
    with open(output_file, "w", encoding="utf-8") as out:
        out.write(metadata_text)
    print(f"output saved to {output_file}")


if __name__ == "__main__":
    main()
