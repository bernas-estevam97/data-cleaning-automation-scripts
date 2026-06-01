import os
import shutil
from pathlib import Path
from collections import defaultdict

def organize_files_by_name(target_directory):
    # Convert string path to a Path object
    path = Path(target_directory)
    
    # Check if directory exists
    if not path.exists():
        print(f"Error: The directory '{target_directory}' does not exist.")
        return

    # Dictionary to group files: Key = Filename (no extension), Value = List of full file paths
    # defaultdict(list) automatically creates a new list if the key doesn't exist
    grouped_files = defaultdict(list)

    print(f"Scanning directory: {path.resolve()}\n")

    # 1. Scan and Group Files
    for file_path in path.iterdir():
        # We only care about files, not existing folders
        # We also skip this script itself if it's placed inside the target folder
        if file_path.is_file() and file_path.name != os.path.basename(__file__):
            # 'stem' gives the filename without the extension (e.g., 'photo.jpg' -> 'photo')
            filename_stem = file_path.stem
            grouped_files[filename_stem].append(file_path)

    # 2. Process Groups
    files_moved_count = 0
    
    for name, files in grouped_files.items():
        # logic: Only act if there is at least one file. 
        # (If you want to STRICTLY only move if there are 2+ files with different extensions, 
        # change the line below to: if len(files) > 1:)
        if len(files) > 0:
            
            # Define the new folder path
            new_folder = path / name
            
            # Create the folder (exist_ok=True prevents error if folder already exists)
            try:
                new_folder.mkdir(exist_ok=True)
            except OSError as e:
                print(f"Error creating folder {new_folder}: {e}")
                continue

            # Move the files
            for file in files:
                destination = new_folder / file.name
                
                # Check if file already exists in destination to prevent overwriting
                if not destination.exists():
                    shutil.move(str(file), str(destination))
                    print(f"Moved: {file.name} -> /{name}/")
                    files_moved_count += 1
                else:
                    print(f"Skipped: {file.name} (File already exists in '{name}' folder)")

    if files_moved_count == 0:
        print("\nNo matching files found to organize.")
    else:
        print(f"\nSuccess! Moved {files_moved_count} files.")

if __name__ == "__main__":
    # You can hardcode the path below, or keep input() to ask every time
    user_path = input("Enter the full path of the folder to organize (or press Enter for current folder): ")
    
    # If user presses Enter, use the current working directory
    if not user_path.strip():
        target_dir = "."
    else:
        target_dir = user_path.strip()

    organize_files_by_name(target_dir)