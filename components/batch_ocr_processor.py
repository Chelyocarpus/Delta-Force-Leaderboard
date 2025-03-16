from doctr.io import DocumentFile
from doctr.models import ocr_predictor
import os
from pathlib import Path
from tqdm import tqdm
import sys

def print_with_flush(message):
    """Print a message and flush stdout to ensure it's captured by the parent process."""
    print(message)
    sys.stdout.flush()

# Initialize the OCR predictor
print_with_flush("Initializing OCR predictor...")
predictor = ocr_predictor(det_arch='fast_base', reco_arch='crnn_vgg16_bn', pretrained=True)
print_with_flush("OCR predictor initialized successfully")

# Define the input folder path
input_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workflow')
print_with_flush(f"Looking for images in: {input_folder}")

# Process all images in the folder
image_files = list(Path(input_folder).glob('*.jpg'))  # Convert to list for tqdm
print_with_flush(f"Found {len(image_files)} images to process")

for i, image_path in enumerate(image_files):
    print_with_flush(f"Processing image {i+1}/{len(image_files)}: {image_path.name}")
    
    # Load and process the image
    img = DocumentFile.from_images(str(image_path))
    result = predictor(img)
    
    # Extract the text
    text_output = result.render()
    
    # Create output filename based on input filename
    output_path = str(image_path).replace('.jpg', '_ocr.txt')
    
    # Save the text to a .txt file
    with open(output_path, 'w', encoding='utf-8') as file:
        file.write(text_output)
    
    print_with_flush(f"OCR text saved to: {output_path}")

print_with_flush("OCR processing completed successfully")