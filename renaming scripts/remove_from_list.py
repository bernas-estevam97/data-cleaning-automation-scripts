import os

# Function to search for files with multiple extensions matching the list in the text file and delete them
def find_and_delete_files_with_extensions(directory, txt_file, extensions):
    try:
        # Read filenames from the txt file
        with open(txt_file, 'r') as f:
            filenames_to_find = [line.strip() for line in f.readlines()]

        # Get the list of all files in the specified directory
        files_in_directory = os.listdir(directory)

        # Search for files with the given extensions that match those in the txt file
        for filename in filenames_to_find:
            for ext in extensions:
                # Construct the full filename with extension
                file_with_extension = f"{filename}{ext}"
                if file_with_extension in files_in_directory:
                    file_path = os.path.join(directory, file_with_extension)  # Full path to the file
                    os.remove(file_path)  # Delete the file
                    print(f"Deleted: {file_with_extension}")
                    break  # No need to check other extensions once the file is found
            else:
                print(f"Not Found: {filename}")

    except FileNotFoundError:
        print(f"The file '{txt_file}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Define the folder to search and the path to the text file
directory_to_search = r'path\to\your\folder'  # Replace with your folder path
txt_file_path = r'path\to\your\filelist.txt'  # Replace with your txt file path

# Define the extensions to check for (e.g., .avi, .mp4, .mov)
extensions_to_check = ['.avi', '.smp', '_out.smp']  # Add more extensions as needed

# Run the function
find_and_delete_files_with_extensions(directory_to_search, txt_file_path, extensions_to_check)
