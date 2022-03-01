#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  fileLogger.py
#  Write new or append to (text) file
"""
Inputs:
    filePath, string, full file path
    content, string, text to add [ALWAYS ADDS ON NEW LINE]
Output:
    txt, string, all text inside made file
"""
#  

#modules

#variables
txt=''

def txtMod(filePath, content):
    try:
        #append existing or make new
        myFile=open(filePath,mode='a+')
    except OSError:
        print('fileLogger: File could not be opened')
    except ValueError:
        print('fileLogger: Encoding error')
    else:
        #assumes new line
        content='\n'+content
        myFile.write(content)
        myFile.close()
        #re-open to export
        myFile=open(filePath,mode='r')
        txt=myFile.read()
        myFile.close()
        #print('File mod ('+str(content)+') complete')
    finally:
        return txt

#test values
"""
newText='quad/n text'
newFi='/home/an/Documents/PlantShelf/sec.txt'
print(txtMod(newFi, newText))
print('fileLogger done')
"""
