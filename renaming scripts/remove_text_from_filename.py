import os
import sys
from pathlib import Path
import textwrap
from argparse import ArgumentParser, HelpFormatter

class RawFormatter(HelpFormatter):
    def _fill_text(self, text, width, indent):
        return "\n".join([textwrap.fill(line, width) for line in textwrap.indent(textwrap.dedent(text), indent).splitlines()])

program_descripton = f'''
    RTFF tool v1.0

    This is the help screen for remove_text_from_filename v1.0!

    -This function receives the absolute path of a folder to work on given by the user.

    -This folder is then shown in the command line as Folder Selected.

    -After successful folder input it asks for the text to remove 
    in each file's name in that folder. Make sure the text you want to remove is repeated
    in all filenames in order to remove it.

    -After confirming (with either yes or y) and if the text to be removed exists in all 
    filenames inside the folder provided the files are automatically renamed.'''

parser = ArgumentParser(description=program_descripton, epilog="""Run python <script_name> -h to see this help screen again.""", formatter_class=RawFormatter)
args = parser.parse_args()

def remove_text_from_filename():
    print("Welcome this is a function to rename all files in one folder given by the user. \nPress Ctrl + C to exit this function at any time\n(If you need help add the -h in front of the python command line function)")
    try:
        dir_path=input("Pass the path of the folder to change names: ")
        os.listdir(dir_path)
        print("Folder selected: " + Path(dir_path).parts[-1])
    except FileNotFoundError:
        sys.stderr.write("\n--------------------------\nFolder not found check your full path again\nRestarting function...\n")
        remove_text_from_filename()

    
    def confirmation_function():
        text_to_remove = input("What text you want to remove from your files' names? Pass it here -> ")
        confirmation = input(text_to_remove + " is the correct text you want to remove? ")
        files = os.listdir(dir_path)
        if confirmation.lower() == "yes" or confirmation.lower() == "y":
            for idx, file in enumerate(files):
                if text_to_remove in os.path.splitext(file)[0]: # Check if text string is in filename. If not this wont work
                    os.rename(os.path.join(dir_path, file), os.path.join(dir_path, os.path.splitext(file)[0].removesuffix(text_to_remove) + os.path.splitext(file)[1]))
                else:
                    pass
                    #sys.exit('------------------------------------------------\nAt least one filename did not have the text given!\nMessage: Function shutdown\nExited')
            
            print("All files renamed successfully!")
            sys.exit(1)    
        else:
            print('Type yes or y for confirmation. If you want to leave this function press Ctrl + C\n------------------------------------------------------------')
            confirmation_function()

    return confirmation_function()

try:
    remove_text_from_filename()
except KeyboardInterrupt: 
    sys.stderr.write("\n--------------------------\nProgram terminated by user\n")
    exit(2)




if __name__ == '__main__':
    remove_text_from_filename()