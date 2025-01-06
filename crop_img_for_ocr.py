from PIL import Image
import os
import glob

def crop_image(image_path, output_folder, coordinates, region_name):
    """
    Crops a specified rectangular region from an image and saves the cropped image to an output folder.
    Args:
        image_path (str): The file path to the input image.
        output_folder (str): The folder where the cropped image will be saved.
        coordinates (tuple): A tuple of four integers specifying the left, upper, right, and lower pixel coordinate.
        region_name (str): Name of the region being cropped (used in filename)
    Returns:
        None
    """
    # Open the image
    image = Image.open(image_path)
    
    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Crop the image to the specified rectangle
    cropped_image = image.crop(coordinates)

    # Generate output filename based on input filename and region
    base_name = os.path.basename(image_path)
    cropped_path = os.path.join(output_folder, f"{region_name}_{base_name}")
    
    # Save the cropped image
    cropped_image.save(cropped_path)
    print(f"Cropped {region_name} image saved at: {cropped_path}")

# Input and output paths
screenshots_path = r"S:\Steam\userdata\40101941\760\remote\2507950\screenshots"
output_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workflow')

# Define regions with their coordinates
regions = {
    'scoreboard': (337, 177, 1886, 1042), # top-left, bottom-right
    'general_information': (700, 27, 1221, 85)  # top-left, bottom-right
}

# Process all image files
image_patterns = ['*.jpg', '*.jpeg', '*.png']
for pattern in image_patterns:
    for image_path in glob.glob(os.path.join(screenshots_path, pattern)):
        try:
            for region_name, coordinates in regions.items():
                crop_image(image_path, output_folder, coordinates, region_name)
        except Exception as e:
            print(f"Error processing {image_path}: {e}")
