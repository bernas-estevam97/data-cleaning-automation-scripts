import pandas as pd
import os
import sys
from pathlib import Path
import textwrap
from argparse import ArgumentParser, HelpFormatter

class RawFormatter(HelpFormatter):
    def _fill_text(self, text, width, indent):
        return "\n".join([textwrap.fill(line, width) for line in textwrap.indent(textwrap.dedent(text), indent).splitlines()])

program_descripton = f'''
    TXT to excel automation tool

    This is the help screen for txt_to_excel v1.0!

    -This function receives the absolute path of a folder to work on given by the user.

    -This folder is then shown in the command line as Folder Selected.

    -After successful folder input it will convert any txt files in the supplied folder to excel format.

    -The newly created excel files will be saved on the supplied folder to save.'''

parser = ArgumentParser(description=program_descripton, epilog="""Run python <script_name> -h to see this help screen again.""", formatter_class=RawFormatter)
args = parser.parse_args()


def txt_to_excel_function():
    #try:
    folder_input = input('Which folder has your txt files? ')
    if os.path.isdir(folder_input):
        print('Folder selected: ', folder_input)
    elif folder_input == "":
        print("You didn't input any path. Try again")
        txt_to_excel_function()
    else:
        print('Invalid path input. Try again.')
        txt_to_excel_function()
        
    folder_to_save = input('In which folder do you want to save the excel files (press enter if you want to be the same folder as your txt files)? ')
    if os.path.isdir(folder_to_save):
        print('Folder selected: ', folder_to_save)
    elif folder_to_save == "":
        folder_to_save = folder_input
        print('Folder is the same as your txt files. --> ', folder_to_save)
    else:
        print('Invalid path input. Try again.')
        txt_to_excel_function()
        
    #except Exception as e:
    #    sys.stderr.write(e)
    #    txt_to_excel_function()
    txt_files = os.listdir(folder_input)
    txt_to_excel = []
    for file in txt_files:
        if os.path.splitext(file)[1] == '.txt':
            txt_to_excel.append(file)
        else:
            pass
    print(txt_to_excel)
    if len(txt_to_excel) > 0:
        print(f'There are {len(txt_to_excel)} txt files in your supplied folder.')
        for txt in txt_to_excel:
            df = pd.read_csv(os.path.join(folder_input,txt), sep='\t')
            with pd.ExcelWriter(os.path.join(folder_to_save,os.path.splitext(txt)[0]+'.xlsx')) as writer:
                df.to_excel(writer, sheet_name=os.path.splitext(txt)[0], index=False)
        print('All txt files have been successfully converted to Excel format.')
    else:
        print('Your folder has no txt files')
        print('Restarting function... Press Ctrl+C to exit at any point')
        txt_to_excel_function()





if __name__ == '__main__':
    try:
        txt_to_excel_function()
    except KeyboardInterrupt: 
        sys.stderr.write("\n--------------------------\nProgram terminated by user\n")
        exit(2)  