import os

def rename_files_recursively(folder_path, new_prefix):
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_dir, file_name = os.path.split(file_path)
            new_name = new_prefix + file_name
            new_path = os.path.join(file_dir, new_name)
            os.rename(file_path, new_path)