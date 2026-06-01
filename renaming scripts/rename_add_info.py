import os
import sys
from pathlib import Path
import textwrap
from argparse import ArgumentParser, HelpFormatter

class RawFormatter(HelpFormatter):
    def _fill_text(self, text, width, indent):
        return "\n".join([textwrap.fill(line, width) for line in textwrap.indent(textwrap.dedent(text), indent).splitlines()])

program_descripton = f'''
    RAI tool v1.0 (short for renaming adding tool)

    This is the help screen for rename_add_info v1.0!

    -This function receives the absolute path of a folder to work on given by the user.

    -This folder is then shown in the command line as Folder Selected.

    -After successful folder input it asks for the text to add 
    at the end of each file name in that folder.

    -You can choose wether to add text in the beggining or the end of the filename. Type "start" for beggining and "end" for the end of the filename.

    -After confirming (with either yes or y) the text to be added the files are automatically renamed.'''

parser = ArgumentParser(description=program_descripton, epilog="""Run python <script_name> -h to see this help screen again.""", formatter_class=RawFormatter)
args = parser.parse_args()

def rename_function():
    print("-------------------------------------------------------------------------------\vWelcome this is a function to rename all files in one folder given by the user. \nPress Ctrl + C to exit this function at any time. \v\vIf you need help add the -h in front of the python command line function: \n" +  r'⚙️  ▶️ python .\rename_add_info.py -h')
    try:
        dir_path=input("\vPass the path of the folder to change names: ")
        os.listdir(dir_path)
        print("\vFolder selected: " + Path(dir_path).parts[-1])
    except FileNotFoundError:
        sys.stderr.write("\vFolder not found check your full path again\nRestarting function...\n")
        rename_function()

    
    def confirmation_function():
        text_to_add = input("\vWhat text you want to add to your file names? Pass it here -> ")
        where_to_add = input('\vWhere to add the text? ')
        confirmation = input("\v"+text_to_add + " is the correct text you want to add? ")
        files = os.listdir(dir_path)
        if confirmation.lower() == "yes" or confirmation.lower() == "y":
            for idx, file in enumerate(files):
                #Rename at the end
                if where_to_add.lower() == "start":
                #os.rename(os.path.join(dir_path, file), os.path.join(dir_path, os.path.splitext(file)[0] + "_" + text_to_add + os.path.splitext(file)[1]))
                #Rename at the beginning
                    os.rename(os.path.join(dir_path, file), os.path.join(dir_path, text_to_add + "_" + os.path.splitext(file)[0]  + os.path.splitext(file)[1]))
                elif where_to_add.lower() == "end":
                    os.rename(os.path.join(dir_path, file), os.path.join(dir_path, os.path.splitext(file)[0] + "_" + text_to_add + os.path.splitext(file)[1]))
                else:
                    print("Please input either 'start' or 'end' depending on where you want the text to be added. Restarting...\n")
                    return
            print("All files renamed successfully!")
            sys.exit(1)
        else:
            print('Type yes or y for confirmation. If you want to leave this function press Ctrl + C\n------------------------------------------------------------')
            confirmation_function()

    return confirmation_function()

try:
    rename_function()
except KeyboardInterrupt: 
    sys.stderr.write("\n--------------------------\nProgram terminated by user\n")
    exit(2)





if __name__ == '__main__':
    rename_function()