#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  camPlant.py
#  
# Capture, save, and analyze images with pi camera
#  
'''
Inputs:
 none
Outputs:
 none
'''
# Credits
#https://projects.raspberrypi.org/en/projects/getting-started-with-picamera
#https://appdividend.com/2019/05/24/how-to-reverse-string-in-python-python-reverse-string-example/
#https://docs.python.org/3/library/os.html
#https://pimylifeup.com/raspberry-pi-opencv/

#modules
import sys
import picamera as pc
from time import sleep
import os
import numpy as np
import cv2
from imutils.video import VideoStream

#variables
hues=120


#must be paired with ".close()" to free resource after use
def startCam():
    try:
        camera=pc.PiCamera()
    except Exception as e:
        print('  CAM ERR: Camera could not be started')
        print(e)
        sys.exit()
    return camera

#from remoteCall
def makeDir(newPath):
    if not os.access(newPath,os.F_OK):
        os.mkdir(newPath)
    return newPath


#Get next name in sequence for file in a directory
def suffix(fullPath,exte): #string, explicit extension
    #string puller functions
    #number to searched character from 0 in given string, found backwards
    def fromBack(t,s): #full string, find string
        return len(t)-t[::-1].find(s)-1
    
    #confirm directory
    curDir=fullPath[0:fromBack(fullPath,'/')+1]
    curDir=makeDir(curDir)
    #isolate the file title
    givenFileName=fullPath[len(curDir):len(fullPath)]
    #givenTitle=givenFileName[0:max(givenFileName.find('('),givenFileName.find(exte))]
    #print('givenFileName before: ',givenFileName)
    
    #splicer function
    def splice(t,c): #filename, count(0-index)
        if t.find('(')>0 and c==0:
            newTit=t[0:t.find('(')+1]+t[fromBack(t,')'):len(t)]
        else:
            spt=fromBack(t,'.')
            newTit=t[0:spt]+' ('+str(c)+')'+t[spt:len(t)]
        #print('n|'+newTit+'|')
        return newTit
    #similitude function
    def unsplice(t): #file name
        t=splice(t,0)
        before=t[0:max(0,t.find('(')+1)]
        #print('b|'+before+'|')
        after=t[max(t.find(')'),0):len(t)]
        #print('a|'+after+'|')
        sameTit=before+after
        #print('s|'+sameTit+'|')
        return sameTit
    
    #begin suffix mod
    #print('search')
    collectedTitles=[]
    #get list of file names and sort
    with os.scandir(curDir) as im:
        for iFile in im:
            if iFile.is_file():
                collectedTitles.append(iFile.name)
    sortedTitles=sorted(collectedTitles)
    #determine number of copies already made
    titleCount=0
    searchTitle=unsplice(givenFileName)
    #print('find')
    for iName in sortedTitles:
        #print('\n'+iName)
        if unsplice(iName)==searchTitle:
            titleCount+=1
            #print(titleCount)
    if titleCount>0:
        givenFileName=splice(givenFileName,titleCount)
        print('\tnow '+givenFileName)
    #print('Dir: ',curDir)
    #print('Num: ',givenFileName)
    fullPath=curDir+givenFileName
    
    return fullPath


#Capture an image and save to full name address + specified extension
def photo(imgName, exte='.jpg',focusTime=2.75,overwrite=False):
    print('\nNew image going to '+imgName)
    camera=startCam()
    try:
        #add file extension if necessary
        if imgName[-len(exte):len(imgName)]!=exte:
            imgName+=exte
        #print('with ext.: ',imgName)
        #get next in line
        imgName=suffix(imgName,exte) if (not overwrite) else imgName
    except Exception as e:
        print(e)
        print('  CAM ERR: Something is wrong with imgName (',str(type(imgName)),'): ',str(imgName))
        return 0
    #test
    #imgF=open(imgName,mode='a+')
    #imgF.close()
    #/test
    try:
        #show image onscreen
        camera.start_preview(alpha=170)
        sleep(focusTime) #delay for camera focus
        camera.stop_preview()
    except Exception as e:
        print(e)
        print('  CAM ERR: Camera could not be initiated')
        return 0
    try:
        camera.capture(imgName)
    except Exception as e:
        print(e)
        print('  CAM ERR: Image could not be taken for ',str(imgName))
        return 0
    #cleanup
    camera.close()
    return imgName


#Take image filepath and return data image of only the hue specified
def maskColor(imgName, myHue): #string, integer
    #https://docs.opencv.org/master/d0/d86/tutorial_py_image_arithmetics.html
    #import cv2
    #import numpy as np
    
    print('\nMasking image '+imgName)
    #read and translate
    BGR=cv2.imread(imgName)
    if BGR is None:
        print('  CAM ERR: There was no image to mask')
        return None
    HSV=cv2.cvtColor(BGR,cv2.COLOR_BGR2HSV)
    
    #color and range as chosen
    pickLo=np.array([myHue-30,33,25])
    pickHi=np.array([myHue+25,255,255])
    
    #mask and reapply
    pickMask=cv2.inRange(HSV,pickLo,pickHi)
    onlyColor=cv2.bitwise_and(BGR,BGR,mask=pickMask)
    
    #test
    #cv2.imshow(str(myHue)+' hue',onlyColor)
    #cv2.waitKey(1000)
    #cv2.destroyAllWindows()
    
    return onlyColor
    

#Analyze for Normalized Difference in Vegetation Index
#Tried:
#https://developers.planet.com/planetschool/calculate-an-ndvi-in-python/
def ndviCalc(imgName):
    #https://stackoverflow.com/questions/59728357/ndvi-value-calculation-and-image-processing
    #import numpy as np
    #import cv2
    
    print('\nCalculating NDVI')
    #define filepaths
    outName=imgName[0:len(imgName)-imgName[::-1].find('.')-1] #everything before file extension
    #-#-#
    #some file names moved to end
    #-#-#
    maskMod=' mask '+str(hues)
    maskLoc=outName+maskMod+imgName[len(outName):len(imgName)] #adding modifier and file extension back on
    print(maskLoc)
    
    #use only green area for consistency across plant sizes
    try:
        maskBool=cv2.imwrite(maskLoc, maskColor(imgName,hues))#60?
    except:
        print('  CAM ERR: The mask could not be created')
        return None

    # Load image and convert to float - for later division
    im = cv2.imread(maskLoc).astype(np.float)
    os.remove(maskLoc)
    BGR=cv2.imread(imgName)
    
    # Split into 3 channels
    NearIR, G, R = cv2.split(im)

    # Compute NDVI values for each pixel
    NDVI = (NearIR - R) / (NearIR + R + 0.001)
    
    #output as single value
    ndvi_single=np.mean(NDVI)
    print('NDVI = '+str(round(ndvi_single,2)))
    
    #create element-wise multiplier
    zeroStack=np.zeros_like(NDVI)
    ndvi3d=np.dstack((zeroStack,zeroStack,NDVI))
    #translate and scale into real region 0-1
    ndvi_overlay=BGR*(ndvi3d+1)/2
    #resize value range to span entire RGB region
    overMax=np.max(ndvi_overlay)
    ndvi_overlay=np.around(ndvi_overlay*255/overMax)
    '''
    #change of color scheme test
    imintep=cv2.imwrite(outLoc,ndvi_overlay)
    imhotep=cv2.cvtColor(cv2.imread(outLoc),cv2.COLOR_BGR2HSV)
    imoutep=cv2.imwrite(outLoc,imhotep)
    outLoc='/home/an/Documents/PlantShelf/daily/2020-07-22/ndviTestG.jpg'
    '''
    #-#-#
    outMod=' ndvi '+str(hues)+' '+str(int(1000*ndvi_single))
    outLoc=outName+outMod+imgName[len(outName):len(imgName)]
    #-#-#
    print(outLoc)
    #output interpretation image
    imwriteBool=cv2.imwrite(outLoc,ndvi_overlay)
    
    return ndvi_single


#Begin video stream object
def startVidjo():
    try:
        vivid=VideoStream(usePiCamera=True, framerate=72).start()
        sleep(1)
    except Exception as e:
        print(e)
        print('  CAM ERR: The video stream could not be started')
        return None
    return vivid


#test values
if __name__=='__main__':
    #tst='https://stackoverflow.com/questions/18420126/select-last-3-rows-of-sql-table'
    #print(photo(tst))
    #print(tst[-4:len(tst)])
    '''rst=tst[::-1]
    print(rst)
    fsla=rst.find('/')
    print(fsla)
    tt=tst[0:len(tst)-fsla]
    print(tt)'''
    ff='/home/an/Documents/PlantShelf/daily/2020-10-02/nofilter.jpg'
    
    '''
    qq='/home/an/Documents/PlantShelf/daily/qr_test ROW (2).jpg'
    camera=startCam()
    camera.start_preview()
    sleep(3)
    print(photo(qq))
    #'''

    '''import numpy as np
    dbg=np.array([[[141, 28, 172],
      [139, 28, 172],
      [137, 26, 170],
      [158, 44, 198],
      [163, 44, 202],
      [162, 43, 201]],

     [[123, 12, 156],
      [125, 15, 157],
      [131, 23, 165],
      [161, 44, 201],
      [166, 47, 205],
      [165, 46, 204]],

     [[121, 13, 155],
      [121, 14, 154],
      [125, 21, 158],
      [172, 53, 211],
      [177, 58, 216],
      [174, 56, 211]]])

    print(dbg.shape)
    print(dbg)
      
    d2arr=np.array([[0,1,2,3,4,5],
      [6,7,8,9,0,10],
      [11,12,13,14,15,16]])
    print(d2arr.shape)
    print(d2arr)

    arrx, arry=d2arr.shape
    d3arr=np.dstack((d2arr,d2arr,d2arr))
    print(d3arr.shape)
    print(d3arr)
    print('calcs')
    drg=dbg*(d3arr+1)/2
    print(drg)
    maxdrg=np.max(drg)
    drg=np.around(drg*255/maxdrg)
    print('refi')
    print(drg)
    '''

    gg='/home/an/Downloads/TensorFlow-2.x-YOLOv3/IMAGES/grinch tree 2009-sm.jpg'
    #print(maskColor(gg,60))
    cc='/home/an/Documents/PlantShelf/setup/maxresdefault color test.jpg'
    #print(maskColor(cc,60))

    #dbg=cv2.imread(ff)
    #print(np.mean(np.mean(dbg,axis=0),axis=0))

    #print(maskColor(ff,150))

    '''
    huehue=range(45,360+5,5)
    for hues in huehue:
        print(ndviCalc(ff))
    '''

    #hues=120
    #print(ndviCalc(ff))
    
    '''
    roo=vidjo()
    u=0
    while u<=100:
        foo=roo.read()
        cv2.imshow("Barcode Scanner", foo)
        cv2.waitKey(1)
        u+=1
    roo.stop()
    #'''
    
    #print(suffix(qq,'.jpg'))
    
    '''
    t='test file.ko'
    x='.ko'
    print(t.find('(')+1)
    before=t[0:max(0,t.find('(')+1)]
    print('|'+before+'|')
    print(t.find(')')+1)
    m=max(t.find(')'),0)
    after=t[m:len(t)]
    print('|'+after+'|')
    #'''
    
    #print(photo('/home/an/Documents/PlantShelf/daily/2021-01-01/overwritetest',overwrite=True))
    
    print(ndviCalc('/home/an/Documents/PlantShelf/daily/2021-02-07/spinach 401 (0, 0).jpg'))
