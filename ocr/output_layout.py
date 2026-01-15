# import layoutparser as lp
# import matplotlib.pyplot as plt
# import pandas as pd
# import numpy as np
# import cv2
# import sys
# import os
# import pydicom
# from PIL import Image
# import pytesseract



# output_directory = "insertion_output"


# def main():
#     if len(sys.argv) < 2:
#         print("check arguments: python output_layout.py <input_file>")
#         sys.exit(1)

#     input_path = sys.argv[1]
#     base_name = os.path.splitext(os.path.basename(input_path))[0]

#     os.makedirs(output_directory, exist_ok=True)
    
#     ocr_agent = lp.TesseractAgent(languages='eng')
#     image = cv2.imread(input_path)
#     plt.imshow(image)
#     plt.axis("off")
#     #plt.show()
#     #sys.exit(0)

#     layout = ocr_agent.detect(image, return_response=False) 

#     # 4. Visualize the results using draw_text
#     # This will create a new image where the text is drawn at the detected locations
#     lp.draw_text(image, layout, font_size=12, text_color=(0, 0, 0), with_box_on_text=True)

        


# if __name__ == '__main__':
#     main()


import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import cv2
import sys
import os
import pydicom
from PIL import Image
import pytesseract
from pytesseract import Output



output_directory = "insertion_output"


def main():
    if len(sys.argv) < 2:
        print("check arguments: python output_layout.py <input_file>")
        sys.exit(1)

    input_path = sys.argv[1]
    base_name = os.path.splitext(os.path.basename(input_path))[0]

    os.makedirs(output_directory, exist_ok=True)

    img = cv2.imread(input_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    d = pytesseract.image_to_data(img, output_type=Output.DICT)
    #print(d.keys())

    n_boxes = len(d['text'])
    detected_words = d['text']
    print(detected_words)
    print_text = ['in']
    for i in range(n_boxes):
        if int(d['conf'][i]) > 60 and (detected_words[i] in print_text):
            (x, y, w, h) = (d['left'][i], d['top'][i], d['width'][i], d['height'][i])
            #img = cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            img = cv2.rectangle(gray, (x, y), (x + w, y + h), (255, 255, 255), -1)
            #x_offset = x + (x//2)
            cv2.putText(gray, detected_words[i], (x, y+20), cv2.FONT_HERSHEY_COMPLEX, 0.9, (0,0,0), 2)

    cv2.imshow('img', gray)
    cv2.waitKey(0)

    sys.exit(0)



    
    


if __name__ == '__main__':
    main()