from doctr.io import DocumentFile
from doctr.models import ocr_predictor
import os
from pathlib import Path

# Initialize the OCR predictor
predictor = ocr_predictor(det_arch='fast_base', reco_arch='crnn_vgg16_bn', pretrained=True) #Fast_base is the best detector in my tests

# Modify the binarization threshold and the box threshold (optional)
#predictor.det_predictor.model.postprocessor.bin_thresh = 0.3
#predictor.det_predictor.model.postprocessor.box_thresh = 0.1

# Define the input folder path
input_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workflow')

# Process all images in the folder
for image_path in Path(input_folder).glob('*.jpg'):  # Add more extensions if needed: '*.png', etc.
    # Load and process the image
    img = DocumentFile.from_images(str(image_path))
    result = predictor(img)
    
    # Extract the text
    text_output = result.render()
    
    # Create output filename based on input filename
    output_path = str(image_path).replace('.jpg', '_ocr.txt') # Output folder = input folder
    
    # Save the text to a .txt file
    with open(output_path, 'w', encoding='utf-8') as file:
        file.write(text_output)

    # Debug: Show the result
    result.show()
    
    print(f"Processed: {image_path}")