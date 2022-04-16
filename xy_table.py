##**************************************************
## FILE:        xy_table.py
## PROJECT:     XY Table/2020 Spring Co-op
## DATE:        Jan-13-2020
## AUTHOR:      Drew Bowler
## PHONE #:     (978) 763-5124
## EMAIL:       drewbowl2016@gmail.com
##
## PURPOSE:     Interfacing with xy_table.lua for
##              use with the 3-axis CNC machine at
##              Geophysical Survey Systems, Inc.
##              in Nashua, NH.
##
## INPUT:       GCode, .dxf, .txt (see README)
## OUTPUT:      XY Table motor control
##
## REVISED:     Jun-24-2020
##
## COMMENT:     Refactoring to decrease latency and
##              make code more readable
##**************************************************


import os
import time
import socket
import pyautogui
import subprocess
from datetime import datetime
import matplotlib.pyplot as plt


## This automates opening Mach 4 and the Lua script for convenience.  Girst it opens the Mach 4 exe with the "mill"
## argument, then waits, then opens ZeroBrane which is what Mach 4 uses as a Lua IDE.
def startup_routine():
    mach4path = r'C:\Mach4Hobby\Mach4GUI.exe /p Mach4Mill'
    mach4luapath = r'C:\Mach4Hobby\ZeroBraneStudio\zbstudio.exe C:\Mach4Hobby\Profiles\XYTable\Modules\xy_table.lua'

    try:                            # Opens Mach4 and launches with the Mill profile
        subprocess.Popen(mach4path, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        print('Mach4 is loading...')
        time.sleep(8)               # Time delay to allow Mach 4 screens to load
    except Exception as error:                         # Needed if Mach 4 is already running
        error_log(error)
        pass
    
    # Launches the Zerobrane Lua IDE and the script to run the GCode
    print('Launching Lua script...')
    print('(If the script doesn\'t automatically run, highlight the ZeroBrane IDE and press \'F6.\')')
    
    try:
        subprocess.Popen(mach4luapath, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        time.sleep(4)               # Time delay to allow Lua IDE to load
        pyautogui.press('f6')       # Simulates a keypress soon after the IDE loads to run the script
    except Exception as error:                         # Exception if Lua is running/another error
        error_log(error)
        pass


## Several hard-coded routines here: home, absolute, pulse x/y, scandxf, viewpath
def __gcode__(gcode, feedrate, record):

    # Sends the table to (0, 0)
    if gcode.lower() == 'home':
        gcode = 'G90 G0 X0 Y0'
        
    # Changes the coordinate system from "relative" to "absolute"
    elif gcode.lower() == 'absolute':
        gcode = 'G90'
        
    # Steps each axis incrementally
    elif 'pulse x' in gcode.lower():
        # NOTE: Pulse is dependent on the motor resolution
        gcode = 'G91 G1 X50 F' + gcode[7:]
    elif 'pulse y' in gcode.lower():
        gcode = 'G91 G1 Y50 F' + gcode[7:]

    # Converts .dxf files to GCode .txt files
    elif 'scandxf' in gcode.lower():
        try:
            open(gcode[8:], 'r')
        except Exception as error:
            error_log(error)
            return 'G0'

        # This section creates a .txt with the same name and sends its path to the Lua script
        txt = '.dxf'
        txt = gcode[8:].replace(txt, '') + '.txt'
        dxf_to_gcode(gcode[8:], txt, feedrate)
        gcode = txt

    elif 'viewpath' in gcode.lower():
        path = gcode[9:]
        if not '.txt' in path:
            path = path + '.txt'
        try:
            with open(path, 'r') as graph:
                lines = graph.readlines()
                x = [float(line.split()[0]) for line in lines]
                y = [float(line.split()[1]) for line in lines]
                plt.axis('equal')
                plt.plot(x, y)
                plt.show()
        except Exception as error:
            error_log(error)
            return 'G0'
    return gcode


## Clears the DOS terminal (purely visual)
def clear():
    os.system('cls')


## This function converts .dxf files to GCode .txt files by looking for "AcDbLine"
## objects in the .dxf fle and converting them to equivalent GCode commands
def dxf_to_gcode(openfilepath, savefile, feedrate):
    # Based on code from: https://sites.google.com/site/richardcncprojects/
    qty         = 1000	        # Quantity of memory to be used
    r           = 2 	        # Round off to decimal places
    text 	    = ''
    error	    = ''
    linecount	= 1
    count       = 0
    feedflag    = 0
    xmax        = 0
    xmin        = 0
    ymax        = 0
    ymin        = 0
    xstart      = [0 for i in range(qty)]
    ystart      = [0 for i in range(qty)]
    xend        = [0 for i in range(qty)]
    yend        = [0 for i in range(qty)]
    file = open(openfilepath, 'r')

    # DXF read loop
    while True:
        text = file.readline()
        text = text.strip()
        print(text)

        if text == 'EOF':
            break
        
        if text.lower() == 'acdbline':
            while True:
                text = file.readline()
                text = text.strip()
                
                if text == '10':
                    text = file.readline() # X start position
                    text = text.strip()
                    xstart[linecount] = float(text)
                    text = 'nothing'
                
                if text == '20':
                    text = file.readline() # Y start position
                    text = text.strip()
                    ystart[linecount] = float(text)
                    text = 'nothing'
                
                if text == '11':
                    text = file.readline() # X end position
                    text = text.strip()
                    xend[linecount] = float(text)
                    text = 'nothing'
                
                if text == '21':
                    text = file.readline() # Y end position
                    text = text.strip()
                    yend[linecount] = float(text)
                    text = 'nothing'
                
                if text == '0': # End of data
                    if ystart[linecount] > ymax: ymax = ystart[linecount]
                    if ystart[linecount] < ymin: ymin = ystart[linecount]
                    if yend[linecount] > ymax: ymax = yend[linecount]
                    if yend[linecount] < ymin: ymin = yend[linecount]
                    if xstart[linecount] > xmax: xmax = xstart[linecount]
                    if xstart[linecount] < xmin: xmin = xstart[linecount]
                    if xend[linecount] > xmax: xmax = xend[linecount]
                    if xend[linecount] < xmin: xmin = xend[linecount]
                    linecount = linecount + 1
                    break
                            
            if linecount >= qty:
                error = error + 'Error: ran out of dimentioned line arrey. Increase qty value.\n'
                text = 'EOF'
                break

    file.close	
            
    # GCode generator
    gcode = 'G90 G17 G21\n'

    for i in range(1, linecount):
        if xstart[i] != xend[i - 1] or ystart[i] != yend[i - 1]:
            gcode = gcode + 'G1 X' + str(round(xstart[i], r)) + ' Y' + str(round(ystart[i], r)) + '\n'
            feedflag = 0
            
        gcode = gcode + 'G1 X' + str(round(xend[i], r)) + ' Y' + str(round(yend[i], r))
        
        if feedflag == 0:
            gcode = gcode + ' F' + feedrate
            feedflag = 1
        
        gcode = gcode + '\n'
            
    if error != '':
        print(error)

    # Save to .txt
    file = open(savefile, 'w')
    file.write(gcode)
    file.close()


## Logs errors in error_log.txt so the user knows what went wrong
def error_log(err):
    error = datetime.now().strftime('[%m-%d-%y %I:%M:%S %p]') + str(err) + '\n'
    error_history = open('error_log.txt', 'a')
    error_history.write(error)
    error_history.close()



### FUNCTIONS END HERE ###

### MAIN BODY & I/O LOOP OF PROGRAM FOLLOWS ###

clear()

if __name__ == '__main__':
    HOST        = '127.0.0.1'
    PORT        = 2504
    feedrate    = '600'
    repeat      = 0
    record      = ''
    check       = ''
    readout     = [0, 0, 0]

    ## Opens a socket and connects to the Lua script
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()

        startup = input('Launch Mach4? [Y/N]: ')
        if startup.lower() == 'y':
            print('Starting Mach4...')
            startup_routine()

        print('Waiting for connection from Lua script...')
        conn, addr = s.accept()

        with conn:
            while True:
                pos = conn.recv(1024).decode()
                pos = pos.split(',')

                # Latency = current time - time sent from Lua script
                latency = 'Latency: ' + str(abs(time.time() * 1000 - float(pos[3][:13])))[:5]

                # Rrcords the coordinates and POSIX timestamp together
                record = record + '{} {} {} '.format(*pos) + str(datetime.timestamp(datetime.now())) + '\n'

                # Assigns each motor axis/latency to its respective label
                clear()
                readout = [str('{:<8}'.format(pos[i]))[:6] for i in range(3)]
                print('X: {} | Y: {} | Z: {}        {} ms'.format(*readout, latency))

                gcode = input('>>')

                ## A few more hard-coded routines here: delta, save, clear, feedrate
                
                # Set increment, pulse on 'enter'
                if 'delta' in gcode.lower():
                    repeat = 'G91 G0 ' + gcode[6:]
                elif gcode == '' and repeat != 0:
                    gcode = repeat
                    
                # Saves the position data w/ time to a .txt file in the current dir
                elif 'save' in gcode.lower():
                    gcode = gcode[5:]
                    if not '.txt' in gcode:
                        gcode = gcode + '.txt'
                    file = open(gcode, 'w') 
                    file.write(record) 
                    file.close()
                    
                # Clears the coordinate and time history stored in "record"
                elif gcode == 'clear':
                    record = ''

                # Defines feedrate for .dxf scanning
                elif 'feedrate' in gcode.lower():
                    feedrate = feedrate[9:]

                # Sends whichever GCode/commands have been inputted
                try:
                    conn.send(bytes(__gcode__(gcode, feedrate, record) + '\n', 'utf8'))
                except Exception as error:
                    error_log(error)

                clear()

                # Lua appeds an extra space (" ") to indicate when the motors have stopped
                while not ' ' in pos:
                    pos = conn.recv(1024).decode()

                    # If the time has updated since the last check, add the coordinates to the record
                    if check != str(datetime.timestamp(datetime.now())) and check != '':
                        record = record + '{} {} {} '.format(*pos.split(',')) + check + '\n'

                    check = str(datetime.timestamp(datetime.now())) # Updates time check
                    latency = 'Latency: ' + str(abs(time.time() * 1000 - float(pos.split(',')[3][:13])))[:5]

                    ## Performs a similar operation as the main print, but "pos" needs to stay intact for the main loop
                    ## so this loop modifies the string rather than modifying "pos."
                    readout = [str('{:<8}'.format(pos.split(',')[i])[:6]) for i in range(3)]
                    print('X: {} | Y: {} | Z: {}        {} ms'.format(*readout, latency), end='\r')

                    ## This section uses "end='\r'" instead of "clear()" because the former is quicker in this case
                    ## and "clear()" causes flickering.