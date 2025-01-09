from PIL import Image
import os
from pathlib import Path
import glob

# Define crop coordinates as constants
LEFT_TEAM_CROP_COORDS = (370, 135, 625, 170)
RIGHT_TEAM_CROP_COORDS = (1160, 135, 1400, 170)

def search_pixel(image_path):
    image = Image.open(image_path)
    pixels = image.load()
    for x in range(337, 344):
        for y in range(177, 1020):
            r, g, b = pixels[x, y]
            if r >= 230 and g >= 230 and b >= 230:
                return (x, y)
    return None

def crop_image(image_path, output_path):
    image = Image.open(image_path)
    cropped_image = image.crop(LEFT_TEAM_CROP_COORDS)
    cropped_image.save(output_path)

def construct_output_path(image_path):
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workflow')
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.basename(image_path)
    return os.path.join(output_dir, f"team_{os.path.splitext(filename)[0]}.jpg")

def process_all_images(folder_path):
    # Get all jpg files in the folder
    jpg_files = glob.glob(os.path.join(folder_path, "*.jpg"))
    
    for image_path in jpg_files:
        result = search_pixel(image_path)
        output_path = construct_output_path(image_path)
        
        if result:
            crop_image(image_path, output_path)
            print(f"Processing {image_path}: Pixel found at {result}. Using left team region. Saved as {output_path}")
        else:
            image = Image.open(image_path)
            cropped_image = image.crop(RIGHT_TEAM_CROP_COORDS)
            cropped_image.save(output_path)
            print(f"Processing {image_path}: Using right team region. Saved as {output_path}")

if __name__ == "__main__":
    # Update this path to your screenshots folder
    screenshots_folder = r"S:\Steam\userdata\40101941\760\remote\2507950\screenshots"
    process_all_images(screenshots_folder)