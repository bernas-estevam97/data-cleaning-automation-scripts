import os
import sys
from pathlib import Path
def rename_function_full():
    print("Welcome this is a function to fully rename all files in one folder given by the user. Press Ctrl + C to exit this function at any time.")
    try:
        dir_path=input("Pass the path of the folder to change names: ")
        os.listdir(dir_path)
        print("Folder selected: " + Path(dir_path).parts[-1])
    except FileNotFoundError:
        sys.stderr.write("\n--------------------------\nFolder not found check your full path again\nRestarting function...\n")
        rename_function_full()

    
    def confirmation_function():
        text_to_rename = input("Insert the text elements you want your files' name to have. Input it here -> ")
        confirmation = input(text_to_rename + " is the correct text you want to add? ")
        files = os.listdir(dir_path)
        if confirmation.lower() == "yes" or confirmation.lower() == "y":
            for idx, file in enumerate(files):
                os.rename(os.path.join(dir_path, file), os.path.join(dir_path, text_to_rename + "_" + str(idx+1) + os.path.splitext(file)[1]))
            print("All files renamed successfully!")
            sys.exit(1)
        else:
            print('Type yes or y for confirmation. If you want to leave this function press Ctrl + C\n------------------------------------------------------------')
            confirmation_function()

    return confirmation_function()



try:
    rename_function_full()
except KeyboardInterrupt: 
    sys.stderr.write("\n--------------------------\nProgram terminated by user\n")
    exit(2)


if __name__ == '__main__':
    rename_function_full()