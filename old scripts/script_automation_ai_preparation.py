import os
import time
import subprocess
import psutil
import sys
from pathlib import Path
import datetime
import pyautogui
import logging

# Set up logging configuration
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def automation_function_ai_preparation():  
    # Folder with all the videos (*.avi) that are to be analysed. 
    folder_input = input(r'Which folder you want prepared for AI analysis (pass in the absolute folder path)?: ')
    if os.path.isdir(folder_input):
        print('Folder selected: ', folder_input)
        print("""
Choices Information\n
0 - Before 22-10-2025 video files not flipped videos.\n
1 - After and including 22-10-2025 dated video files not flipped.\n
2 - Before 22-10-2025 video files and flipped.\n 
3 - After and including 22-10-2025 dated video files and flipped.\n
""") 
        while True:
            try:
                choice_script = int(input('Which script you want to run (0-3)? '))
                if 0 <= choice_script <= 3:
                    break
                else:
                    print("Invalid input! Please enter a number between 0 and 3.")
            except ValueError:
                print("Invalid input! Please enter a valid integer.")
    elif folder_input == "":
        print("You didn't input any path. Try again")
        automation_function_ai_preparation()
    else:
        print('Invalid path input. Try again.')
        automation_function_ai_preparation()
    
        
    def prepare_folder_for_ai_analysis(choice_script):
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
        
        for key in ['shift', 'ctrl', 'alt', 'win']:
            pyautogui.keyUp(key)
        time.sleep(1) 
        pyautogui.click(1364, 685)
        time.sleep(1)
        pyautogui.hotkey('alt', 'd')
        time.sleep(0.5)
        pyautogui.write(r'C:\Users\TSEMotion\Desktop\Template File for AI')
        time.sleep(0.5)
        pyautogui.press('enter')
        time.sleep(1)
        #pyautogui.click(980, 670)
        #time.sleep(0.5)
        #pyautogui.hotkey('ctrl', 'shift', '6') #FORCE DETAILS VIEW FOR EXPLORER
        time.sleep(1)
        pyautogui.press('tab', presses=6)
        time.sleep(1)
        if choice_script == 0:
            pyautogui.write('StandardProject.smp')                   
            time.sleep(1)
            pyautogui.press('enter')
        elif choice_script == 1:
            pyautogui.write('StandardProjectNew.smp')
            time.sleep(1)
            pyautogui.press('enter')
            # NOW THE NEW TEMPLATE IS OPENED
        elif choice_script == 2 or choice_script==3:
            pyautogui.write('StandardProjectFlipped.smp')
            time.sleep(1)
            pyautogui.press('enter')
            # NOW THE NEW TEMPLATE IS OPENED
        else:
            print('You did not input if the choice was new or old for this script!')
            return
            
        # GET VIDEO FILENAMES
        cutoff_date = datetime.datetime(2025, 10, 22)
        video_files = os.listdir(folder_input)
        avi_files = []
        exclusion_list = []
        
        def get_creation_time(path):
            """Cross-platform creation date getter."""
            p = Path(path)
            stat = p.stat()

            if sys.platform.startswith("win"):
                ts = stat.st_birthtime
            else:
                if hasattr(stat, "st_birthtime"):  # macOS, BSD
                    ts = stat.st_birthtime
                else:
                    ts = stat.st_mtime  # fallback on Linux

            return datetime.datetime.fromtimestamp(ts)
        
        
        for file in video_files:
            full_path = os.path.join(folder_input, file)  
            if os.path.splitext(file)[1].lower() == '.avi':
                creation_time = get_creation_time(full_path)
                logging.debug(f'File: {file}, Creation Time: {creation_time}')
                if choice_script == 0: 
                    if creation_time < cutoff_date:
                        avi_files.append(file)
                        continue
                    else:
                        exclusion_list.append(file)
                        continue
                elif choice_script ==1:
                    if creation_time >= cutoff_date:
                        avi_files.append(file)
                        continue
                    else:
                        exclusion_list.append(file)
                        continue
                elif choice_script == 2:
                    if creation_time < cutoff_date and "flip" in os.path.splitext(file)[0]:
                        avi_files.append(file)
                        continue
                    else:
                        exclusion_list.append(file)
                        continue
                elif choice_script == 3:
                    if creation_time >= cutoff_date and "flip" in os.path.splitext(file)[0]:
                        avi_files.append(file)
                        continue
                    else:
                        exclusion_list.append(file)
                        continue
                else:
                    print('You did not input if the choice was new or old for this script!')
                    return
            elif os.path.splitext(file)[1].lower() == '.smp':
                exclusion_list.append(file[:-4] + '.avi')
            
        
        final_list = [ i for i in avi_files if i not in exclusion_list]
        logging.debug(f'Final List: {final_list}')
        sorted_list = sorted(final_list)
        
        for idx, vid in enumerate(sorted_list):
            #16x35 file menu
            #99x218 resource admin
            logging.debug(f'Starting loop iteration for video: {vid}, Index: {idx}')
            if idx == 0:
                time.sleep(1)
                pyautogui.click(16, 35)
                time.sleep(1)
                # THESE COORDS ARE FOR TSE SOFTWARE ----> pyautogui.click(99, 218)
                pyautogui.click(208, 197)
                time.sleep(1)
                pyautogui.doubleClick(1384,448) # ----> These coords work for both programs: TSE and SIMI
                time.sleep(1)
                pyautogui.hotkey('alt', 'd')
                time.sleep(0.5)
                pyautogui.write(folder_input)
                time.sleep(0.5)
                pyautogui.press('enter')
                time.sleep(0.5)
                #pyautogui.click(980, 670)
                #time.sleep(1)
                #pyautogui.hotkey('ctrl', 'shift', '6') #FORCE DETAILS VIEW IN FOLDER EXPLORER
                #time.sleep(1)
                pyautogui.press('tab', presses=6) # Make sure the folders are on the DETAILS view
                time.sleep(0.5)
                pyautogui.write(vid)
                time.sleep(0.5)
                pyautogui.press('enter', presses=2)
                time.sleep(0.5)
                pyautogui.hotkey('ctrl', 'shift', 's')
                time.sleep(0.5)
                pyautogui.hotkey('alt', 'd')
                time.sleep(0.5)
                pyautogui.write(folder_input)
                time.sleep(0.5)
                pyautogui.press('enter')
                time.sleep(0.5)
                pyautogui.press('tab', presses=6) # Make sure the folders are on the DETAILS view
                time.sleep(1)
                pyautogui.write(vid[0:-4])
                time.sleep(0.5)
                pyautogui.press('enter')
                time.sleep(1)
                #check_file = vid[0:-4]+".smp"
                #Stop loop if there was an error creating smp file (missed input from pyautogui is the most plausible cause, this will stop escalating wrong inputs)
                if any(vid[0:-4]+'.smp' in file for file in os.listdir(folder_input)):
                    logging.debug(f'SMP file already exists: {vid[0:-4]+".smp"}')
                    continue #Loop continues if file exists
                else:
                    logging.error(f'SMP file does not exist and was not created: {vid}')
                    break #Loop stops if smp wasnt created after a loop in specified index  
  
            else: 
                time.sleep(1)
                pyautogui.click(16, 35)
                time.sleep(1)
                # THESE COORDS ARE FOR TSE SOFTWARE ----> pyautogui.click(99, 218)
                pyautogui.click(208, 197)
                time.sleep(1)
                pyautogui.doubleClick(1384,448)
                time.sleep(1)
                pyautogui.write(vid)
                time.sleep(0.5)
                pyautogui.press('enter', presses=2)
                time.sleep(0.5)
                pyautogui.hotkey('ctrl', 'shift', 's')
                time.sleep(0.5)
                pyautogui.write(vid[0:-4])
                time.sleep(0.5)
                pyautogui.press('enter')
                time.sleep(1)
                #Stop loop if there was an error creating smp file (missed input from pyautogui is the most plausible cause, this will stop escalating wrong inputs)
                if any(vid[0:-4]+'.smp' in file for file in os.listdir(folder_input)):
                    logging.debug(f'SMP file already exists: {vid[0:-4]+".smp"}')
                    continue #Loop continues if file exists
                else:
                    logging.error(f'SMP file does not exist and was not created: {vid}')
                    break #Loop stops if smp wasnt created after a loop in specified index   
            
        
        # Close the program if needed
        sys.exit('\nProgram finished!')
        #pyautogui.hotkey('alt', 'f4')
        
        
    return prepare_folder_for_ai_analysis(choice_script)    

automation_function_ai_preparation()
