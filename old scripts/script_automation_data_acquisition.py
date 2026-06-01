import subprocess
import pyautogui
import win32api
import psutil
import time
import keyboard
import os
import sys
from pathlib import Path
import textwrap
from argparse import ArgumentParser, HelpFormatter
from pynput import keyboard as pynputkeyb
import multiprocessing
import threading


# Mouse locations of interest (PC DO BIOTERIO):
    # 1- Kinematics folder: 54-100 x 214-225
    # 2- Export option: 81-277 x 247-268
    # TAB 12 vezes para export pyautogui.press('tab', presses=12) ou: 1237x955

# Mouse locations of interest (PC ALFASCORE):
    # 1- Kinematics folder: 64-220
    # 2- Export option: 81-277 x 247-268
    # TAB 12 vezes para export pyautogui.press('tab', presses=12) ou: 1237x955

# Multiprocessing function that waits for the abort key

#def listen_for_key(key, stop_event):
#    print(f"Press '{key}' at any time to terminate the program.")
#    keyboard.wait(key)
#    print(f"'{key}' pressed. Terminating the program...")
#    # This will terminate the entire script
#    stop_event.set()


#TEST CASE (BIOTERIO PC): C:\Users\TSEMotion\Desktop\Ladder ai TEST
#def analyse_folder_inputted(folder):


# Open the external program
def automation_function_data_acquisition():
    # Folder with files that the data can be extracted from: *_out.xmp files
    folder_input = input('Which folder you want to get data from (pass in the absolute folder path)?: ')
    if os.path.isdir(folder_input):
        print('Folder selected: ', folder_input)
    elif folder_input == "":
        print("You didn't input any path. Try again")
        automation_function_data_acquisition()
    else:
        print('Invalid path input. Try again.')
        automation_function_data_acquisition()
    # Folder in which you wish to save the extracted data files (*.txt)    
    folder_to_save_input = input('In which folder you wish to save the files in?')
    if os.path.isdir(folder_to_save_input):
        print('Folder selected: ', folder_to_save_input)
    elif folder_to_save_input == "":
        print("You didn't input any path. Try again")
        automation_function_data_acquisition()
    else:
        print('Invalid path input. Try again.')
        automation_function_data_acquisition()
   

    def automation_function_main():
        try:
            #process = subprocess.Popen([r'C:\Program Files (x86)\TSE\Motion 9.2.2\SmMotion'], shell=True)
            process = subprocess.Popen([r'C:\Program Files (x86)\Simi\Motion 10.3.0.25096 beta\SmMotion'], shell=True)
            # Wait for the program to initialize
            time.sleep(5)
            is_running = True

            while is_running:
                # check if the app is running
                is_running = "SmMotion" in (p.name() for p in psutil.process_iter())
                print('Program opening...')

            print('Program opened. Running...')
        except Exception as e:
            sys.exit(e)
        #finally:
        #   print('This program will shutdown')


        # 1. This section bypasses the demand for choosing a file option
        pyautogui.click(2192, 341)
        time.sleep(1)
        keyboard.press_and_release('esc')
        time.sleep(1)

        # --------------------------------------------------------------- #

        
        # Files in input folder section, get only the _out.xmp files
        files = os.listdir(folder_input)
        saved_files = os.listdir(folder_to_save_input)
        out_xmp_files = []
        already_saved_files = []
        for file in files:
            if "_out.xmp" in os.path.basename(file):
                out_xmp_files.append(file)
                # os.startfile(os.path.join(folder_input, os.path.basename(file)))
            else:
                pass
        for sav in saved_files:
            already_saved_files.append(sav[0:-4] + "_out.xmp")
        
        final_list = [ i for i in out_xmp_files if i not in already_saved_files]
        sorted_list = sorted(final_list)
        time.sleep(2)
        for idx, f in enumerate(sorted_list):
        # C:\Users\TSEMotion\Desktop\xmp_test_folder
        # C:\Users\TSEMotion\Documents\Exported data test folder
            if idx == 0:
                pyautogui.hotkey('ctrl', 'o')
                # Pass the folder path from folder_input to windows explorer search bar
                pyautogui.hotkey('alt', 'd')
                time.sleep(0.5)
                pyautogui.write(folder_input)
                time.sleep(0.5)
                pyautogui.press('enter')
                time.sleep(0.5)
                pyautogui.press('tab', presses=6)
                time.sleep(0.5)
                pyautogui.write(f)
                time.sleep(0.5)
                pyautogui.press('enter')
                time.sleep(1)
                # The previous code open the file
                # Now the code for clicking the kinematics folder and exporting
                # !!!!! THIS SECTION ONLY WORKS IN BIOTERIO PC !!!!!
                pyautogui.rightClick(70,220)  # this was a point chosen from the range given at the start of the file
                time.sleep(0.5)
                pyautogui.rightClick(100, 250)  # this was a point chosen from the range given at the start of the file
                time.sleep(0.5)
                pyautogui.press('tab', presses=12)
                time.sleep(0.5)
                pyautogui.press('enter')
                time.sleep(1)
                # Choose folder 
                pyautogui.hotkey('alt', 'd')
                time.sleep(0.5)
                pyautogui.write(folder_to_save_input)
                time.sleep(0.5)
                pyautogui.press('enter')
                time.sleep(0.5)
                pyautogui.press('tab', presses=6)
                # Save only the file name without _out and xmp
                pyautogui.write(f[0:-8])
                time.sleep(0.5)
                pyautogui.press('enter', presses=2)
                time.sleep(0.5)
                pyautogui.press('esc')
            else:
                pyautogui.hotkey('ctrl', 'o')
                # Pass the folder path from folder_input to windows explorer search bar
                pyautogui.hotkey('alt', 'd')
                time.sleep(0.5)
                pyautogui.write(folder_input)
                time.sleep(0.5)
                pyautogui.press('enter')
                time.sleep(0.5)
                pyautogui.press('tab', presses=6)
                time.sleep(0.5)
                pyautogui.write(f)
                time.sleep(0.5)
                pyautogui.press('enter')
                time.sleep(1)
                # The previous code open the file
                # Now the code for clicking the kinematics folder and exporting
                # !!!!! THIS SECTION ONLY WORKS IN BIOTERIO PC !!!!!
                pyautogui.rightClick(70,220)  # this was a point chosen from the range given at the start of the file
                time.sleep(0.5)
                pyautogui.rightClick(100, 250)  # this was a point chosen from the range given at the start of the file
                time.sleep(0.5)
                pyautogui.press('tab', presses=12)
                time.sleep(0.5)
                pyautogui.press('enter')
                time.sleep(1)
                # Choose folder 
                # Save only the file name without _out and xmp
                pyautogui.write(f[0:-8])
                time.sleep(0.5)
                pyautogui.press('enter', presses=2)
                time.sleep(0.5)
                pyautogui.press('esc')
             
                
        # Close the program if needed
        sys.exit('\nProgram finished!')
        
        #pyautogui.hotkey('alt', 'f4')
        
        
    return automation_function_main()




if __name__ == '__main__':
    try:
        automation_function_data_acquisition()
        #stop_event = threading.Event()
        
        # Listen for the termination key
        #listen_thread = threading.Thread(target=listen_for_key, args=('q', stop_event))
        #listen_thread.start()
    
        # Start the task function in a separate thread
        #task_thread = threading.Thread(target=automation_function_data_acquisition, args=(stop_event,))
        #task_thread.start()

        

        # Wait for both threads to complete
        #task_thread.join()
        #listen_thread.join()
    except KeyboardInterrupt: 
        sys.stderr.write("\n--------------------------\nProgram terminated by user\n")
        exit(2)

