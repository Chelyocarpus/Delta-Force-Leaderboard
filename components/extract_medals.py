import os
from PIL import Image

def check_pixels(image_path, pixel_checks):

    image = Image.open(image_path)
    pixels = image.load()
    
    results = []
    for (x, y), (r_thresh, g_thresh, b_thresh) in pixel_checks:
        r, g, b = pixels[x, y]
        if r >= r_thresh and g >= g_thresh and b >= b_thresh:
            results.append(True)
        else:
            results.append(False)
    
    return results

def get_highest_rank_medals(image_path, pixel_checks, medals):
    results = check_pixels(image_path, pixel_checks)
    categories = ["Combat", "Capture", "Logistics", "Intelligence"]
    highest_rank_medals = []

    for i, category in enumerate(categories):
        for j in range(2, -1, -1):  # Check Gold, Silver, Bronze in that order
            if results[i * 3 + j]:
                highest_rank_medals.append(medals[i * 3 + j])
                break

    return highest_rank_medals

def process_images_in_folder(folder_path, pixel_checks, medals):
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_path = os.path.join(folder_path, filename)
            highest_rank_medals = get_highest_rank_medals(image_path, pixel_checks, medals)
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workflow')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"medals_{os.path.splitext(filename)[0]}.txt")
            with open(output_path, 'w') as f:
                for medal in highest_rank_medals:
                    f.write(f"{medal}\n")

# Example usage
if __name__ == "__main__":
    pixel_checks = [
        # Combat Medal
        ((130, 358), (230, 230, 230)), # Bronze Medal
        ((200, 358), (230, 230, 230)), # Silver Medal
        ((270, 358), (230, 230, 230)), # Gold Medal
        # Capture Medal
        ((130, 560), (230, 230, 230)), # Bronze Medal
        ((200, 560), (230, 230, 230)), # Silver Medal
        ((270, 560), (230, 230, 230)), # Gold Medal
        # Logistics Medal
        ((130, 764), (230, 230, 230)), # Bronze Medal
        ((200, 764), (230, 230, 230)), # Silver Medal
        ((270, 764), (230, 230, 230)), # Gold Medal
        # Intelligence Medal
        ((130, 967), (230, 230, 230)), # Bronze Medal
        ((200, 967), (230, 230, 230)), # Silver Medal
        ((270, 967), (230, 230, 230)), # Gold Medal
    ]
    medals = [
        "Combat Bronze Medal", "Combat Silver Medal", "Combat Gold Medal",
        "Capture Bronze Medal", "Capture Silver Medal", "Capture Gold Medal",
        "Logistics Bronze Medal", "Logistics Silver Medal", "Logistics Gold Medal",
        "Intelligence Bronze Medal", "Intelligence Silver Medal", "Intelligence Gold Medal"
    ]
    folder_path = r"S:\Steam\userdata\40101941\760\remote\2507950\screenshots"
    process_images_in_folder(folder_path, pixel_checks, medals)
