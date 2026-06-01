import os
#import glob

def find_and_rename_files(directory, text_to_search, text_to_add):
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
        new_file_name = f"{os.path.splitext(old_file)[0]}_{text_to_add}{file_extension}"
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
    print(f"📂 Files in directory: {all_files}")

    text_to_search = input("What text the file name must contain: ")

    # Filter files containing the search string
    matched_files = [file for file in all_files if text_to_search in file]
    print(f"✅ Matched files: {matched_files}")

    text_to_add = input("Enter the text to add in the filename: ")
    find_and_rename_files(directory, text_to_search, text_to_add)
