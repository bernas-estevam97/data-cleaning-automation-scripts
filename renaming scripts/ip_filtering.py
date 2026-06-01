import os
import sys
import textwrap
from argparse import ArgumentParser, HelpFormatter
import re
from socket import inet_aton
import struct

class RawFormatter(HelpFormatter):
    def _fill_text(self, text, width, indent):
        return "\n".join([textwrap.fill(line, width) for line in textwrap.indent(textwrap.dedent(text), indent).splitlines()])

program_descripton = f'''
    IP filtering tool v1.0

    This is the help screen for ip_filtering v1.0!

    -This function filters ips in log files or any files with repeated ips.

    -For this function to work the ips need to be at the beggining of each line of the file.
    (this can be easily improved for other instances of IP filtering)

    -If the file format is correct, the function will return a python set with all the ips.
    '''

parser = ArgumentParser(description=program_descripton, epilog="""Run python <script_name> -h to see this help screen again.""", formatter_class=RawFormatter)
args = parser.parse_args()



def ip_filtering():
    all_ips = []
    pattern_ip = r'\b(?:[0-9]{1,3}\.){3}[0-9]'
    try:
        file_input = input('Pass the name of the file for analysis and filtering: ')
        file_path = os.path.abspath(file_input)
        if not os.path.isdir(file_path):
            with open(file_path, 'r') as f:
                file = f.readlines()
                for line in file:
                    ip_column = line.split()[0]
                    if re.match(pattern_ip, ip_column):
                        if ip_column not in all_ips:
                            all_ips.append(ip_column)
                        else:
                            pass
                    else:
                        pass
                ips = sorted(all_ips, key=lambda ip: struct.unpack("!L", inet_aton(ip))[0])
                set(ips)
                ips_to_document = []
                with open('all_ips_sorted.txt', 'w') as wf:         
                    for idx, ip in enumerate(ips):
                        ip_line = f'IP {idx+1}: {ip}\n'
                        ips_to_document.append(ip_line)
                    wf.writelines(ips_to_document)     

        else:
            print('The name you supplied is not a valid file, it could be a folder or a file with an invalid extension for reading.')
    except FileNotFoundError:
        sys.stderr.write("\n--------------------------\nFile not found check your full path again\nRestarting function...\n")
        ip_filtering()
    




if __name__ == '__main__':
    ip_filtering()