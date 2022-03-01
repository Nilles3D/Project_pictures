#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  wifiCheck.py
#  
#  Checks for internet connection and reboots if there is none
#  
'''
Inputs:
  crontab
  1,3 18 * * * /usr/bin/python3 /home/an/Documents/PlantShelf/wifiCheck.py > /home/an/Documents/PlantShelf/setup/wifiLog.log 2>&1
Outputs:
  none
'''
#Credits
#https://medium.com/better-programming/how-to-check-the-users-internet-connection-in-python-224e32d870c8


#modules
import requests
import subprocess
import os

#variables
url='https://mail.google.com/mail/u/0/#inbox'
timeout=3

def wafu():
    #single run
    try:
        #r = requests.get(url, timeout=timeout)
        r = requests.head(url, timeout=timeout)
        print('Connection available to '+url)
    except requests.ConnectionError as ex:
        print(ex)
        print('Connection unavailable at '+url)
        #subprocess.run("sudo shutdown -r 1 'Sys reboot'",shell=True)
        os.system('sudo reboot')

if __name__=="__main__":
    wafu()
