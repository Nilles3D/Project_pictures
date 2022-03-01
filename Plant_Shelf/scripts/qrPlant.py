#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  qrPlant.py
#  
#  Copyright 2020  <an@AndrewRPi3B>
#  
#  Using single-row QR codes as signals for controlling the shelf
#  
'''
Inputs:
 none
Outputs:
 none
'''
#  
# Credits:
#https://docs.opencv.org/3.4/de/dc3/classcv_1_1QRCodeDetector.html
#https://pypi.org/project/pyzbar/
#https://www.pyimagesearch.com/2018/05/21/an-opencv-barcode-and-qr-code-scanner-with-zbar/
#https://www.geeksforgeeks.org/python-opencv-cv2-polylines-method/
#https://numpy.org/doc/stable/reference/generated/numpy.reshape.html
#https://github.com/jrosebr1/imutils/blob/master/imutils/video/videostream.py
#https://picamera.readthedocs.io/en/release-1.13/fov.html

#modules
import cv2
from pyzbar import pyzbar
import numpy as np
import time
import imutils
import camPlant
import hardware as hw

#variables
qr=cv2.QRCodeDetector()
#dimensions
picPercent=.1 #total center location tolerance (fraction)
picWidth=0
#other
drawColor=(125,255,60)

#turn flash on
hw.led(hw.pinFlash,1)


#Take image data and return all code data deciphered within it
def qrCompile(imageData, markup=False, centerAxis=0): #np array, bool, int
    #print('Compiling list of codes')
    # find the barcodes in the image and decode each of the barcodes
    barcodes = pyzbar.decode(imageData)
    if len(barcodes)==0:
        #print('No QR or bar code could be found')
        hw.led(hw.pinLED,False)
        return None
    else:
        qrList=[]
        hw.led(hw.pinLED,True)
    
    # loop over the detected barcodes
    for barcode in barcodes:
        #print(barcode)
        
        #VARIOUS ITEMS OMITTED FOR SPEED
        # extract the bounding box location of the barcode and draw the bounding box surrounding the barcode on the image
        #(x, y, w, h) = barcode.rect
        #cv2.rectangle(imageData, (x, y), (x + w, y + h), (0, 125, 255), 2)
        
        #find corners of code, not bounding box
        barPoints=np.array(barcode.polygon,np.int32)
        barPoints=barPoints.reshape((-1,1,2))
        #print(barPoints)
        
        #mark and save center of polygon
        barCenter=np.mean(barPoints,centerAxis)
        barCenter=np.around(barCenter).astype(int)
        cx=barCenter[0][0]
        cy=barCenter[0][1]
        barCenter=barCenter.reshape(-1,1,2)
        #print(barCenter)
        
        # convert bytes object to a string
        barcodeData = barcode.data.decode("utf-8")
        #barcodeType = barcode.type
        qrList.append([barcodeData,cy if centerAxis==0 else cx])
        
        # draw the barcode data and barcode type on the image
        if __name__=='__main__' or markup:
            #demarkations
            cv2.polylines(imageData,[barPoints],True,drawColor,2)
            cv2.polylines(imageData,barCenter,True,drawColor,5)
            #enumeration
            text = "{} ({},{})".format(barcodeData,cx,cy)
            cv2.putText(imageData, text, (cx-70, cy-10), cv2.FONT_HERSHEY_SIMPLEX, 0.66, drawColor, 2)
            print(text)
    
    return imageData,qrList


#Find codes within the center range
def findCenterQ(bigList,errBar=picPercent): #qr detect output (integer tuple), allowable off-center (float)
    #print('Finding centered codes')
    #setup
    centerRange=[(.5-errBar/2),(.5+errBar/2)] #acceptable center location of qr code
    centerLimits=[picWidth*c for c in centerRange]
    qCenter=[]
    #divide and conquer
    for qrFound in bigList:
        pnt=qrFound[1]
        if centerLimits[0]<=pnt and pnt<=centerLimits[1]:
            qCenter.append(qrFound[0])
            #print('fOuND 1! '+str(pnt))
        #else:
            #print('Center off by '+str(pnt-np.mean(centerLimits)))
    return np.flipud(qCenter) #in reading order


#Display image data in window
def showPic(imageData,imageName='Image'): #np array, string
    keyPressed=[]
    if __name__ == '__main__' and (imageData is not None):
        #print('Displaying image')
        #print(type(imageData))
        cv2.imshow(imageName, imageData)
        keyPressed=cv2.waitKey(1) #effective pause, milliseconds
    return keyPressed
    

#Static image detect, decode, and return values near horizontl centerline
#input: full path name of image
#output: list of qr code values
def qrStatic(imgPath): #full path string
    print('Starting static QR search')
    qString=[]
    
    # load the input image
    image = cv2.imread(imgPath)
    if image is None:
        print('  QR ERR: No image was loaded')
        return None
    #print(image.shape)
    global picWidth
    picWidth=image.shape[0]
    
    #make list and marked-up image
    try:
        imageMarked, qString = qrCompile(image,True)
    except TypeError:
        print('  QR ERR: There was no code in that image')
        return None
    except Exception as e:
        print(e)
        print('  QR ERR: Something went wrong in compiling the QR image')
        return None
    #retain the centered codes' values
    qFinds=findCenterQ(qString,errBar=1.5*picPercent)
    print('Centered items '+str(qFinds))
    
    #display and overwrite save
    showPic(imageMarked,'Static All')
    outBool=cv2.imwrite(imgPath,imageMarked)
    
    return qFinds


#Video decoding codes, return value list when code(s) approaches center
#input: time to search, motor speed control, motor reference
#output: list of qr codes near centerline, adjusted motor speed control, final motor position
def qrDynamic(timeout, motSpeed=0, motInt=hw.motorWalk): #float (seconds), float (0-1), int
    #motor control
    if motInt==hw.motorWalk:
        motChoice=hw.motorWalk#1
        motSpeed=max(0,min(motSpeed,1))
        motTime=hw.timeOutWalk
        motPin=hw.pinWalkLimitHi
        centerAxis=0
    else:
        motChoice=hw.motorStairs#0
        motSpeed=1
        motTime=hw.timeOutStairs
        motPin=hw.pinStairsLimitHi
        centerAxis=1
    walk0=hw.motorCtl(motChoice,'s') if motSpeed>0 else 0
    #print(walk0)
    
    print('\nStarting dynamic QR search')
    #conditionals
    time0=time.time()
    qFound=[]
    #setup
    vs=camPlant.startVidjo()
    # while time.time()<time0+timeout:
        # showPic(vs.read(),'hooh')
    if vs is None:
        print('  QR ERR: Try again in a second')
        return 'ERR:RESOURCES',motSpeed,walk0
    global picWidth
    picWidth=vs.read().shape[centerAxis]
    #print(picWidth)
    
    #ignore any codes that are already at center
    initialFind=qrCompile(vs.read())
    initialQR=initialFind[1][0] if initialFind is not None else None
    getCenter=True if initialQR is None else False
    print('getCenter=',getCenter)
    
    #big 'ol loop
    walk0=hw.motorCtl(motChoice,'f',spd=motSpeed) if motSpeed>0 else 0
    limiter=False
    while time.time()<time0+timeout and (not limiter):
        #time1=time.time() #debug speed shot
        #view through camera
        frame = vs.read()
        #make list
        qrBundle=qrCompile(frame, centerAxis=centerAxis)
        #take only when one or more codes appear
        if qrBundle is not None:
            frameMarked=qrBundle[0]
            qrString=qrBundle[1]
            #print('qrString='+str(qrString))
            #continue with non-zero-length codes
            if len(qrString)>0:
                qFound=findCenterQ(qrString)
                #only keep the centered codes
                if len(qFound)>0:
                    frameMarked=cv2.putText(frameMarked, "CENTERED", (20,20), cv2.FONT_HERSHEY_SIMPLEX, 0.66, drawColor, 2)
                    '''component testing
                    print('elements found')
                    print(qFound)
                    print(initialQR)
                    if initialQR is not None:
                        print('elements compared')
                        print(qFound[0])
                        print(initialQR[0])
                    #'''
                    #return when centered
                    if getCenter:
                        break
                        pass #kept in testing
                    else:
                        if (initialQR is not None) and qFound[0]!=initialQR[0]: break
                        print('Confirm: leaving ',qFound)
                        time.sleep(2*.03)#wait a couple frames to slow terminal log down
                '''useless statement
                else:
                    #change policy when leaving initial centered codes
                    if not getCenter:
                        #print(hw.motorCtl(motChoice,'f',posOnly=True)-walk0)
                        if motSpeed>0 and hw.motorCtl(motChoice,'f',posOnly=True)-walk0>.2:
                            getCenter=True
                            print('Liftoff: codes are no longer present')
                            #time.sleep(0.1) #wobble error
                        else:
                            #print('Confirm: still leaving')
                            pass
                            #'''
        #skip when no codes appear
        else:
            qFound=None
            frameMarked=frame
        #update display
        showPic(frameMarked,'Dynamo')
        
        #check motor's path limit
        if motSpeed>0:
            limiter=hw.readSwitch(motPin)
            #print(limiter)
            walk1=hw.motorCtl(motChoice,'f',posOnly=True)
            #print('\t',round(walk1,4))
            if walk1>0.85*motTime and motSpeed<.45: #near end and pulley is getting tight
                motSpeed=.45
                walk1=hw.motorCtl(motChoice,'f',spd=motSpeed)
                print('Walk speed increased to ',round(motSpeed,3),' near end of shelf.')
        #print(round(time.time()-time1,3)) #debug speed shot
    
    #cleanup
    walk2=hw.motorCtl(motChoice,'s')
    vs.stop()
    time.sleep(0.03)
    try:
        vs.update()
    except ValueError:
        time.sleep(0.03)
        vs.update()
    cv2.destroyAllWindows()
    
    #Returning
    print('Sending back:')
    #errors
    if limiter:
        print('  limit hit')
        qFound='ERR:LIMIT'
    elif not time.time()<time0+timeout:
        print('  search time exceeded')
        qFound='ERR:TIME'
    else:
        print('  qFound:',qFound)
    #answers
    print('  motSpeed:',round(motSpeed,2))
    print('  walk2:',round(walk2,3))
    
    return qFound, motSpeed, walk2 #most recent centered list, final motor speed, final motor position



#testing
if __name__ == '__main__':
    qq='/home/an/Documents/PlantShelf/daily/qr_test SIZES.jpg'
    
    ''' STATIC ID TEST
    tn=qrStatic(qq)
    print(tn)
    print(len(tn))
    #'''
    
    ''' CENTERING CODES TEST
    cr=[picWidth*c for c in centerRange]
    print(cr)
    for qrFound in tn:
        dat=str(qrFound[0])
        pnt=qrFound[1]
        if cr[0]<=pnt and pnt<=cr[1]:
            print(str(qrFound)+' centered!')
        else:
            print(str(qrFound)+' off by '+str(pnt-picWidth/2))
    #'''
    
    ''' PHOTO DRAWING TEST
    op=[[694 ,729], [1053,  732], [1055,  379], [701,  376]]
    myA=np.array(op,np.int32)
    #print(myA)
    myA=myA.reshape(-1,1,2)
    #myA=np.arange(8).reshape(4,1,2)*100
    print(myA)
    myC=np.mean(myA,0)
    print(myC)
    myC=np.around(myC).astype(int)
    print(myC)
    myC=myC.reshape(-1,1,2)
    print(myC)
    myim=cv2.imread(qq)
    cv2.polylines(myim,[myA],True,(125,255,60),5)
    cv2.polylines(myim,myC,True,(125,255,60),5)
    cv2.imshow("Image", myim)
    cv2.waitKey(0)    
    #'''
    
    ''' ARRAY MANIPULATION
    ua=np.arange(8).reshape(4,1,2)
    au=np.flipud(ua)
    print(ua)
    print(au)
    #'''
    
    ''' STAIR POSITION & SEEK TEST
    print('-homing stairs')
    hw.goHome(hw.motorStairs)
    print('-raising stairs')
    hw.motorCtl(hw.motorStairs,'f')
    time.sleep(2.75)
    hw.motorCtl(hw.motorStairs,'l')
    print('-homing walk')
    hw.goHome(hw.motorWalk)
    print('-running walk')
    hw.motorCtl(hw.motorWalk,'f',0.2)
    print(qrDynamic(5,.2))
    hw.motorCtl(hw.motorWalk,'s')
    print('-homing walk')
    #hw.goHome(hw.motorWalk)
    print('-homing stairs')
    #hw.goHome(hw.motorStairs)
    #'''
    
    bb='/home/an/Documents/PlantShelf/daily/qr_test barcode (1).jpg'
    #print(camPlant.photo(bb,focusTime=6))
    #print(qrStatic(bb))
    
    #print(showPic(None))
    
    '''STAIRS POSITION TEST
    hw.goHome(hw.motorStairs)
    hw.motorCtl(hw.motorStairs,'f')
    time.sleep(1.0)
    hw.motorCtl(hw.motorStairs,'s')
    print(hw.goHome(hw.motorStairs))
    #'''
    '''WALK POSITION TEST
    hw.goHome(hw.motorWalk)
    pau=0.5
    for k in range(2):
        hw.motorCtl(hw.motorWalk,'f',spd=.3)
        time.sleep(pau)
        print('\nstop=',hw.motorCtl(hw.motorWalk,'s'))
        time.sleep(pau)
    print('\n')
    print('homedTime=',hw.goHome(hw.motorWalk))
    #'''
    
    '''LIGHT TESTING
    #hw.motorCtl(hw.motorWalk,'f',0.8)
    hw.led(hw.pinFlash,True)
    print(qrDynamic(5,motSpeed=.2))
    time.sleep(1)
    hw.led(hw.pinFlash,False)
    hw.goHome(hw.motorWalk)
    #'''
    
    #ww='/home/an/Documents/PlantShelf/daily/2020-12-31/qr [0,0:0.747] .jpg'
    #print(qrStatic(ww))
    
    ''' CONTROLLED DYNAMIC TEST
    hw.goHome(hw.motorWalk)
    print(qrDynamic(12,motSpeed=0.18))
    time.sleep(5)
    #print(qrDynamic(12,0.2))
    hw.goHome(hw.motorWalk)
    #'''
    
    #xx='/home/an/Documents/PlantShelf/daily/2021-01-07/qr [0,0:0.916].jpg'
    #print(qrStatic(xx))
    
    #''' FREE DYNAMIC TEST
    print(hw.goHome(hw.motorStairs))
    print(hw.goHome(hw.motorWalk))
    #time.sleep(6)
    #hw.led(hw.pinFlash,False)
    print(qrDynamic(14, motInt=0))
    time.sleep(0.75)
    print(qrDynamic(7,motSpeed=.18))
    hw.led(hw.pinFlash,False)
    #print(hw.goHome(hw.motorStairs))
    #'''
    
