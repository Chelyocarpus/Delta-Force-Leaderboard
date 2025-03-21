from PIL import Image
import os
from pathlib import Path
import glob

# Define crop coordinates as constants
LEFT_TEAM_CROP_COORDS = (367, 116, 500, 150)  # top-left, bottom-right
RIGHT_TEAM_CROP_COORDS = (1156, 115, 1300, 150)  # top-left, bottom-right
SEARCH_PIXEL_COORDS = (335, 156, 338, 987)  # top-left, bottom-right

def search_pixel(image_path):
    image = Image.open(image_path)
    pixels = image.load()
    print(f"Searching pixels in region: x({SEARCH_PIXEL_COORDS[0]}-{SEARCH_PIXEL_COORDS[2]}), y({SEARCH_PIXEL_COORDS[1]}-{SEARCH_PIXEL_COORDS[3]})")
    
    # Search from top to bottom, left to right
    for x in range(SEARCH_PIXEL_COORDS[0], SEARCH_PIXEL_COORDS[2]):
        for y in range(SEARCH_PIXEL_COORDS[1], SEARCH_PIXEL_COORDS[3]):
            try:
                r, g, b = pixels[x, y]
                if r >= 230 and g >= 230 and b >= 230:
                    print(f"Found white pixel at ({x}, {y}) with RGB({r}, {g}, {b})")
                    return (x, y)
            except IndexError:
                print(f"Warning: Coordinates ({x}, {y}) out of bounds")
                continue
    print("No white pixel found in search region")
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
            print("Processing {0}: Pixel found at ({1}, {2}). Using left team region. Saved as {3}".format(
                image_path, result[0], result[1], output_path))
        else:
            image = Image.open(image_path)
            cropped_image = image.crop(RIGHT_TEAM_CROP_COORDS)
            cropped_image.save(output_path)
            print("Processing {0}: Using right team region. Saved as {1}".format(image_path, output_path))

if __name__ == "__main__":
    # Update this path to use the environment variable
    screenshots_folder = os.environ.get("DELTA_SCREENSHOTS_PATH", r"S:\Steam\userdata\40101941\760\remote\2507950\screenshots")
    process_all_images(screenshots_folder)