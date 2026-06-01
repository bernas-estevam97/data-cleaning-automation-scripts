import os
import shutil

def flatten_directory(root_dir):
    # Validate that the provided path exists and is a directory
    if not os.path.exists(root_dir) or not os.path.isdir(root_dir):
        print("❌ Error: The specified directory does not exist or is not a folder.")
        return

    print(f"\nScanning: {root_dir}...\n")

    # Walk through the directory tree bottom-up
    for dirpath, _, filenames in os.walk(root_dir, topdown=False):
        # Skip the root directory itself so we don't try to move files to the same place
        if dirpath == root_dir:
            continue 

        for file in filenames:
            source_path = os.path.join(dirpath, file)
            destination_path = os.path.join(root_dir, file)

            # Safety check: avoid overwriting files with the same name
            if os.path.exists(destination_path):
                print(f"⚠️ Conflict: '{file}' already exists in the root. Skipping.")
                continue

            try:
                shutil.move(source_path, destination_path)
                print(f"Moved: {file}")
            except Exception as e:
                print(f"Error moving {file}: {e}")

        # Remove the folder if it's now empty
        if not os.listdir(dirpath):
            try:
                os.rmdir(dirpath)
                print(f"🗑️ Removed empty folder: {dirpath}")
            except Exception as e:
                print(f"Error removing folder {dirpath}: {e}")

if __name__ == "__main__":
    # Ask the user for the directory path
    user_path = input("Enter the full path of the directory you want to flatten: ")
    
    # Strip quotes in case the user drag-and-drops the folder into the terminal
    user_path = user_path.strip('\"\'')
    
    flatten_directory(user_path)
    print("\n✅ Flattening complete!")