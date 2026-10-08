import os

def find_avi_files_in_directory(directory, txt_file, extensions):
    """Rename matched files to add _not_processed before their extension."""
    try:
        with open(txt_file, 'r') as f:
            filenames_to_find = [line.strip() for line in f.readlines() if line.strip()]

        files_in_directory = set(os.listdir(directory))

        for idx, filename in enumerate(filenames_to_find):
            for ext in extensions:
                full_filename = f"{filename}{ext}"
                if full_filename in files_in_directory:
                    # Build the new filename: keep original extension, add prefix before it
                    new_filename = full_filename.rsplit('.', 1)[0] + '_not_processed.' + ext
                    src = os.path.join(directory, full_filename)
                    dst = os.path.join(directory, new_filename)
                    os.rename(src, dst)
                    print(f'  [{idx+1}] {full_filename} → {new_filename}')
                else:
                    print(f'  [{idx+1}] NOT FOUND: {full_filename}')

    except FileNotFoundError:
        print(f"The txt file not found: '{txt_file}'")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    folder = input('Directory you want to search in? ')
    txt_file = input('Path to the text file with filenames? ')
    extensions_to_check = ['.avi']

    find_avi_files_in_directory(folder, txt_file, extensions_to_check)