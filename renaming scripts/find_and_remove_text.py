import os
#import glob

def find_and_rename_files_remove(directory, text_to_search, text_to_remove):
    directory = os.path.abspath(directory)
    print(f"🔍 Checking directory: {directory}")
    print(f"🔍 Searching for files containing: {text_to_search}")
    

    if not matched_files:
        print("❌ No matching files found.")
        return

    count = 1
    for old_file in matched_files:
        file_path = os.path.join(directory, old_file)
        file_extension = os.path.splitext(old_file)[1]

        #Remve suffix method only removes furthest one
        new_file_name = f"{os.path.splitext(old_file)[0].removesuffix(text_to_remove)}{file_extension}"

        #Replace method
        new_file_name = f"{os.path.splitext(old_file)[0].replace(text_to_remove, "")}{file_extension}"
        new_file_path = os.path.join(directory, new_file_name)

        try:
            os.rename(file_path, new_file_path)
            print(f"✅ Renamed: {old_file} -> {new_file_name}")
        except Exception as e:
            print(f"❌ Error renaming {old_file}: {e}")

        count += 1

if __name__ == "__main__":
    import sys
    # if len(sys.argv) < 3:
    #     print("Usage: python script.py <directory> <text_to_search>")
    #     sys.exit(1)

    # directory = sys.argv[1]
    # text_to_search = sys.argv[2]
    directory = input("Enter the directory you which to work in: ")

    # List all files in the directory for verification
    all_files = os.listdir(directory)
    print(f"📂 Files in directory: {len(all_files)}")

    text_to_search = input("What text the file name must contain: ")

    # Filter files containing the search string
    matched_files = [file for file in all_files if text_to_search in file]
    print(f"✅ Matched files: {len(matched_files)}")

    text_to_remove = input("Enter the text to remove in the filename: ")
    find_and_rename_files_remove(directory, text_to_search, text_to_remove)
