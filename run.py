import os
import subprocess

script_dir = os.path.dirname(os.path.abspath(__file__))

subprocess.run(['python', os.path.join(script_dir, 'components/crop_regions.py')])
subprocess.run(['python', os.path.join(script_dir, 'components/extract_medals.py')])
subprocess.run(['python', os.path.join(script_dir, 'components/extract_team_name.py')])
subprocess.run(['python', os.path.join(script_dir, 'components/batch_ocr_processor.py')])
subprocess.run(['python', os.path.join(script_dir, 'components/process_match_data.py')])

print("All scripts have run successfully.")