import os

# Function to search for .avi files matching the list in the text file
def find_avi_files_in_directory(directory, txt_file, extensions):
    try:
        # Read filenames from the txt file
        with open(txt_file, 'r') as f:
            filenames_to_find = [line.strip() for line in f.readlines()]
        # Get the list of all files in the specified directory
        files_in_directory = os.listdir(directory)

        # Search for .avi files that match those in the txt file
        for idx, filename in enumerate(filenames_to_find):
            for ext in extensions:
                file_with_extension = f"{filename}{ext}"
                if file_with_extension in files_in_directory:
                    #RENAMING
                    
                    os.rename(os.path.join(directory_to_search, file_with_extension), os.path.join(directory_to_search, os.path.splitext(file_with_extension)[0] + "_" + 'not_processed' + os.path.splitext(file_with_extension)[1]))
                    print(f'File {idx+1}:{file_with_extension} renamed to --> {file_with_extension}_not_processed.avi')
                    
                    #DELETING
                    
                    #file_path = os.path.join(directory, file_with_extension)  # Full path to the file
                    #os.remove(file_path)  # Delete the file
                    #print(f"Deleted: {file_with_extension}")
                else:
                    print(f"ID: {idx+1} Not Found: {file_with_extension}")

    except FileNotFoundError:
        print(f"The file '{txt_file}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Define the folder to search and the path to the text file
directory_to_search = input('What folder you which to look in? ')  # Replace with your folder path
txt_file_path = input('Which file has your filenames to look into? ')  # Replace with your txt file path

# Define the extensions to check for (e.g., .avi, .mp4, .mov)
extensions_to_check = ['.avi', '.smp', '_out.smp']  # Add more extensions as needed

#C:\Users\berna\Documents\Coding Projects\simi scripts\video_not_run.txt
# Run the function
find_avi_files_in_directory(directory_to_search, txt_file_path, extensions_to_check)
