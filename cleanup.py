import os
import shutil
import glob
import time

def cleanup_files():
    archive_dir = 'archive'
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)

    # Files to move
    files_to_move = glob.glob('*.json') + glob.glob('*.csv')
    
    for f in files_to_move:
        # Skip package-lock or other config jsons if any (not present here based on history)
        if f == 'package.json': continue 
        
        try:
            shutil.move(f, os.path.join(archive_dir, f))
            print(f"Moved {f}")
        except Exception as e:
            print(f"Skipped {f}: {e}")

    # Move directory
    if os.path.exists('test_crops'):
        try:
            target = os.path.join(archive_dir, 'test_crops')
            if os.path.exists(target):
                shutil.rmtree(target) # Remove old if exists
            shutil.move('test_crops', archive_dir)
            print("Moved test_crops/")
        except Exception as e:
            print(f"Skipped test_crops/: {e}")

    # Create .gitignore
    gitignore_content = """
# Data archives
archive/
images/
test_crops/

# Logs
*.log

# Python
__pycache__/
*.pyc
venv/
"""
    with open('.gitignore', 'w') as f:
        f.write(gitignore_content)
    print("Created .gitignore")

if __name__ == "__main__":
    cleanup_files()
