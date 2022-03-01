#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  hardware.py
#  
#  Manipulate pins for apparatus
'''
Inputs: none
Outputs: none
'''
# Credit
#https://gpiozero.readthedocs.io/en/stable/api_input.html
#
# Parts
#ADC https://www.mouser.com/ProductDetail/Microchip-Technology/MCP3008-I-P?qs=AF%252BffTaPb30XZ0OdV6HdVg%3D%3D
#H-bridge https://www.mouser.com/ProductDetail/Texas-Instruments/SN754410NEE4?qs=CyooD0rhQjnvsC%2F8JC7BnA%3D%3D


#modules
import gpiozero as gp
import time
import statistics as st
import math

#variables
tol=.2 #fraction
mega=pow(10,8) #inf resistance
referee=5100 #ohm reference resistor
maxR=pow(10,6) #biggest single resistor
#Integer reference
motorStairs=0
motorWalk=1
motorShoulder=2
#Timeout limits (seconds)
timeOutWalk=4
timeOutStairs=18
#BCM numbering
#Relays for motor+directions
pinA1=17 #stairs up
pinA2=12 #stairs down
pinB1=18 #walk right
pinB2=23 #walk left
pinShoulder=13 #servo
pinPump=27 #solenoid
#Manual notification/override switch
pinSwitch=24
#Limit switches
pinStairsLimitHi=6
pinStairsLimitLo=5
pinWalkLimitHi=25
pinWalkLimitLo=19
pinIndicator=16
#Information station
pinOhm=4
pinLED=20
pinDrvErr=21
pinFlash=26

#Full-scope definitions
#driver board
drvA1=gp.DigitalOutputDevice(pin=pinA1)
drvA2=gp.PWMOutputDevice(pin=pinA2)
drvB1=gp.PWMOutputDevice(pin=pinB1)
drvB2=gp.DigitalOutputDevice(pin=pinB2)
drvErr=gp.Button(pin=pinDrvErr,pull_up=True)
#switches (fet, bjt) all tied to ground
relayPump=gp.PWMLED(pinPump)#gp.OutputDevice(pin=pinPump)
switchStairsHi=gp.Button(pin=pinStairsLimitHi,pull_up=True)
switchStairsLo=gp.Button(pin=pinStairsLimitLo,pull_up=True)
switchWalkHi=gp.Button(pin=pinWalkLimitHi,pull_up=True)
switchWalkLo=gp.Button(pin=pinWalkLimitLo,pull_up=True)
switchIndicator=gp.Button(pin=pinIndicator,pull_up=True)
#servo
servo=gp.Servo(pinShoulder,min_pulse_width=(20-2.5)/1000,max_pulse_width=(20-0.5)/1000,initial_value=None)
#other
meter=gp.MCP3008(channel=pinOhm)
ledGen=gp.LED(pinLED)
ledFlash=gp.LED(pinFlash)
#motor positions
timeAsk=[0,0]
timeFirstAsk=[False,False]
dirPrevious=[0,0]
timePosition=[0,0]


#Forward, backward, reverse, or stop a motor; return switch status
def motorCtl(motorRef, direction, spd=1, posOnly=False): #int, str, float, bool
    #board always on. SLP tied to 3.3V
    #position setup
    def timeUpdate():
        #velocity scaled across PWM values to be consistent with
        # time-distance traveled with walking motor at full speed
        s=abs(dirPrevious[motorRef])
        velocityFactor=max(0,1.5440*pow(s,3)-3.8819*pow(s,2)+3.5434*pow(s,1)-0.20199*pow(s,0))
        direction=math.copysign(1,dirPrevious[motorRef])
        timeDiff=time.time()-timeAsk[motorRef]
        timeDist=velocityFactor*direction*timeDiff
        '''print('s=',s)
        print('vf=',round(velocityFactor,4))
        print('direct=',direction)
        print('timeBtwn=',round(timeDiff,3))
        print('timeDist=',round(timeDist,4))
        #'''
        return timeDist
    if not timeFirstAsk[motorRef]:
        timeFirstAsk[motorRef]=True
        timeAsk[motorRef]=time.time()
    if posOnly:
        return timePosition[motorRef]+timeUpdate()
    #direction
    if direction=='f': #forward
        relValA=1
        relValB=0
    elif direction=='b': #backward
        relValA=0
        relValB=1
    elif direction=='r': #reverse
        if motorRef==motorStairs: #vertical
            relValA=drvA1.value*-1+1
            relValB=drvA2.value*-1+1
        elif motorRef==motorWalk: #horizontal
            relValA=drvB1.value*-1+1
            relValB=drvB2.value*-1+1
    elif direction=='s': #stop
        relValA=0
        relValB=0
    elif direction=='l': #lock
        relValA=1
        relValB=1
    else:
        print('Motor direction '+str(direction)+' undefined')
    #pwm adjustment
    if ((motorRef==motorStairs and direction=='f') or (motorRef==motorWalk and direction=='b')) and spd!=1: #non-PWM pins
        spd=round(spd)
        print('Speed rounded to '+str(spd))
    spd=max(0,min(spd,1))
    relValA*=spd
    relValB*=spd
    #motor selection
    if motorRef==motorStairs: #vertical
        drvA1.value=relValA
        drvA2.value=relValB
    elif motorRef==motorWalk: #horizontal
        drvB1.value=relValA
        drvB2.value=relValB
    else:
        print('Motor '+str(motorRef)+' undefined')
        return None
    #motor position by timing (positive forward)
    '''
    print(motorRef)
    print('timePosition before '+str(timePosition[motorRef]))
    print('dirPrevious before '+str(dirPrevious[motorRef]))
    print('timeAsk before '+str(timeAsk[motorRef]))
    #'''
    timePosition[motorRef]+=timeUpdate()#dirPrevious[motorRef]*(time.time()-timeAsk[motorRef])
    #update for next time, pun intended
    timeAsk[motorRef]=time.time()
    dirPrevious[motorRef]=relValA-relValB
    '''
    print('timePosition after '+str(timePosition[motorRef]))
    print('dirPrevious after '+str(dirPrevious[motorRef]))
    print('timeAsk after '+str(timeAsk[motorRef]))
    #'''
    #finally
    print('Motor '+str(motorRef)+' going '+str(direction)+', rate '+str(round(spd,2))+', pos '+str(round(timePosition[motorRef],3)))
    return round(timePosition[motorRef],3)


#hold the walkway with the shoulder at a shelf
def motorHold(tf): #boolean
    if tf:
        servo.value=-.05
        print('Shoulder holding')
    elif tf is None:
        servo.value=None
        print('Shoulder deactivated')
    else:
        servo.value=-.9
        5
        print('Shoulder released')
    return servo.value
    

#read resistor value through an ADC channel
def readRes(accurate,verbose=True): #int, bool
    resVal=[]
    if accurate:
        timeLimit=time.time()+1
        while time.time()<=timeLimit:
            resVal.append(meter.value)
            time.sleep(.05)
        resRead=st.mean(resVal)
        print('Smoothed measurement')
    else:
        resRead=meter.value
    resV=max(0, resRead)
    resR=referee/(max(1/resV-1,1/mega)) #required voltage divider on reference 5.1k in series
    if verbose: print('Resistor on ch:'+str(pinOhm)+' = '+str(round(resR,2)))
    #time.sleep(1.5) #testing only
    return resR


#loop until change in readings are found, return search time
def findChange(limit): #defined pin for end of search range
    time0=time.time()
    #cnt=0
    r1=readRes(False)
    print('Finding change from '+str(round(r1,2)))
    rChange=0
    rThresh=100
    time.sleep(0.75) #bogus/debounce deadtime
    while abs(rChange)<rThresh and not readSwitch(limit): #ohms, bool
        #print(cnt)
        r2=readRes(False)
        rChange=r2-r1
        if r1>=maxR and r2>=maxR: #it's a bogus reading
            rchange=rThresh-1
        elapsedTime=time.time()-time0
        #print(elapsedTime)
        time.sleep(0.1) #for stability
        if elapsedTime>20:# or r2>referee*mega:
            print("Ya'll need to move faster")
            break
        #cnt+=1
    if readSwitch(limit):
        print('End of search range reached')
    else:
        print('Change found ~ '+str(round(rChange,2)))
    return elapsedTime


#moving item is still near the expected value
def inTol(myVal,myReading=0,myTol=tol): #float, float as fraction
    if (myReading==0): myReading=readRes(False,False)
    lowerBound=(1-myTol)*myVal
    upperBound=(1+myTol)*myVal
    print('\tinTol? ['+str(int(lowerBound))+', '+str(int(myReading))+', '+str(int(upperBound))+']')
    return (lowerBound<=myReading and myReading<=upperBound)


#control a certain LED
def led(ledNum,HiLo): #1 high, 0 low
    #sanitization
    if HiLo==True or HiLo>=.5:
        HiLo=1
    else:
        HiLo=0
    #fake dictionary
    if (ledNum==pinLED):myLED=ledGen
    elif(ledNum==pinFlash):myLED=ledFlash
    else: myLED=gp.LED(ledNum)
    #action
    myLED.value=HiLo
    #time.sleep(2)
    
    
#read the status of given switch
def readSwitch(pin):
    #dictionary method did not allow for objects to be passed succinctly
    if (pin==pinStairsLimitHi):sw=switchStairsHi
    elif (pin==pinStairsLimitLo):sw=switchStairsLo
    elif (pin==pinWalkLimitHi):sw=switchWalkHi
    elif (pin==pinWalkLimitLo):sw=switchWalkLo
    elif (pin==pinIndicator):sw=switchIndicator
    elif (pin==pinDrvErr):sw=drvErr
    else: sw=gp.Button(pin=pin,pull_up=True)
    return sw.is_pressed


#send a motor down or left, return time it took to do so
def goHome(motor): #integer
    #choose limits
    if motor==motorStairs:
        pinLimitLo=pinStairsLimitLo
        pinLimitHi=pinStairsLimitHi
        timePlus=timeOutStairs
        #be certain of where the servo's arm is
        #sArm=motorHold(False)
        #time.sleep(.2/60*90) #sec/degree
        #sArm=motorHold(None)
    else:
        pinLimitLo=pinWalkLimitLo
        pinLimitHi=pinWalkLimitHi
        timePlus=timeOutWalk
    #define time and speed
    print('Homing motor '+str(motor))
    time0=time.time()
    timeOut=time0+timePlus
    #spdlmt=0.501 #speed limit for Stairs
    motHoming=motorCtl(motor,'b')#,spdlmt)
    #send backwards
    while not readSwitch(pinLimitLo) and time.time()<timeOut:
        time.sleep(.05) #slows pin log down
    #stop and report
    motHoming=motorCtl(motor,'s')
    time1=time.time()
    if time1<=timeOut:
        print('Motor is home')
    else:
        print('!!! Home for motor '+str(motor)+' could not be found')
    print('Motor position as calculated: '+str(round(motHoming,2)))
    timePosition[motor]=0 #reset
    return round(time1-time0,2)


#increment forward and collect resistors at each point, return collected list
def goCollect(motor): #int
    if motor==motorStairs:
        pinLimitLo=pinStairsLimitLo
        pinLimitHi=pinStairsLimitHi
    else:
        pinLimitLo=pinWalkLimitLo
        pinLimitHi=pinWalkLimitHi
    print('\nCollecting through motor '+str(motor))
    time0=time.time()
    #start from bottom of stairs OR left of shelf
    mot=goHome(motor)
    #loop up until limit switch
    time1=time.time()+15
    newList=[]
    while time.time()<time1 and not readSwitch(pinLimitHi):
        upGo=motorCtl(motor,'f')
        #continue until change in reading is found
        motTime=findChange(pinLimitHi)
        #stop to collect
        mot=motorCtl(motor,'s')
        if not readSwitch(pinLimitHi):
            newPoint=readRes(True)
            newList.append([newPoint,mot]) #value, position
            #pause with indicator
            led(pinLED,1)
            time.sleep(max(newPoint/5000,1))
            led(pinLED,0)
    if time.time()>=time1:
        print('!!! Motor collection may have timed out')
    #loop back for walk
    if motor==motorWalk:
        goHome(motor)
    else:
        justStop=motorCtl(motor,'s')
    #lock it in place
    #shldr=motorHold(True)
    return newList


#increment stairs down one shelf, return value of read resistor
def goDown(nextShelf): #float
    print('\nGoing down one shelf')
    #from current
    currPoint=readRes(True)
    stairs=motorCtl(motorStairs,'b') #WILL REQUIRE DAMPING
    #to next
    while inTol(currPoint):
        led(pinLED,1)
    led(pinLED,0)
    print('I have left the first shelf\n')
    #pause at next shelf indicator
    stairsTime=findChange(pinStairsLimitLo)
    stairs=motorCtl(motorStairs,'s')
    print('\nI have arrived at the second shelf')
    newPoint=readRes(True)
    #Damping is assumed to make this move accurate enough to not miss a shelf
    return newPoint
    

#increment walk right one pot, return value of read resistor
def goRight(nextPoint): #float
    print('\nGoing right one pot to '+str(round(nextPoint,0)))
    #start from left of shelf
    currPoint=readRes(True)
    walk=motorCtl(motorWalk,'f')
    #leave that point
    rTime=findChange(pinWalkLimitHi)
    print('\nI have left pot 1')
    #loop right until next anticipated point
    led(pinLED,1)
    walkTime=findChange(pinWalkLimitHi)
    led(pinLED,0)
    walk=motorCtl(motorWalk,'s')
    print('\nI have arrived at another pot near '+str(walk)+' sec.')
    newPoint=readRes(True)
    #for the unexpected
    if not inTol(nextPoint,newPoint):
        print('\tPot of '+str(round(nextPoint,0))+' expected,')
        print('\tPot of '+str(round(newPoint,0))+' found instead.')
        #define limits of search
        timeRL=.8*walkTime
        time1=time.time()+timeRL
        print('\t'+str(round(timeRL,0))+' sec. allocated for search')
        #begin search
        walkReversed=False
        while time.time()<time1:
            print('\nNew search is starting:')
            if not walkReversed:
                way1='f'
                way2='b'
                pinLimit=pinWalkLimitLo
            else:
                way1='b'
                way2='f'
                pinLimit=pinWalkLimitHi
            #back away from that point
            walk=motorCtl(motorWalk,way2)
            print('\nBacking away from that pot')
            while inTol(newPoint,myTol=.1):
                blinker=(round(time.time() % 1,1)*10) % 2
                led(pinLED,int(blinker))
            led(pinLED,0)
            print('\nMoving between pot 1 and 2...')
            #find another value
            walkTimeBack=findChange(pinLimit)
            time2=time.time()
            walk=motorCtl(motorWalk,'s')
            #analyze
            newPoint=readRes(True)
            print('\nFound while searching: '+str(round(newPoint,0))+' near '+str(walk)+' sec.')
            if (walkTimeBack>=timeRL or (inTol(currPoint,newPoint) and not inTol(nextPoint,newPoint))): #square 0
                time1=time.time()+2*timeRL
                excess=round(timeRL-walkTimeBack,1)
                print('Movement time of '+str(round(walkTimeBack,1))+' seconds ('+str(excess)+' search time remaining)')
                if walkReversed:
                    print('!!! End of search limit 2, sorry\n')
                    break
                else:
                    walkReversed=True
                    print('End of search limit 1')
            elif not inTol(nextPoint,newPoint): #something else was found
                print('It was not the pot you are looking for')
                #add back lost time and continue
                time1+=time.time()-time2
            else: #that must be it
                print('!!! Pot 2 found !!!\n')
                walk=motorCtl(motorWalk,'s') #just for good measure
                break
            print('\n')
            #time.sleep(1.5) #testing only
        #final measurement, correct or not
        newPoint=readRes(True)
    print('Pot 2 arrival value: '+str(round(newPoint,0)))
    return newPoint
    

#drive stairs upward until shelf indicator is activated
def goUp():
    #release hold on the shelf
    #for s in range(2):
        #stairHeld=motorHold(False)
        #time.sleep(.5)
    #if stairHeld>-.4:
        #print('Shoulder motor could not be retracted')
        #return 's'
    #on belay
    time1=time.time()+timeOutStairs
    while (not readSwitch(pinIndicator)) and time.time()<time1:
        stairCont=motorCtl(motorStairs,'f')
        time.sleep(.5) #time driven by overtravel of limit switch
        if (not readSwitch(pinStairsLimitHi)):
            return None
        if readSwitch(pinDrvErr):
            return 'e'
    #grab hold of the shelf
    #stairHeld=motorHold(True)
    stairCont=motorCtl(motorStairs,'l')
    return stairCont


#move walk right slowly across the board until a code is found
#handled in remoteCall to avoid cross-importation of qrPlant.


def waterPump(t=1): #integer (seconds)
    print('\nWatering for '+str(t)+' seconds')
    #needs independent LED indicator
    relayPump.on()
    motorHold(True)
    time.sleep(t)
    relayPump.off()
    motorHold(False)
    time.sleep(.2/60*90) #sec/degree
    


#test values
if __name__=='__main__':
    # for i in range(4):
        # nt=time.time()
        # print(nt % 1)
        # print((round(nt%1,1)*10))
        # print((round(nt%1,1)*10) % 2)
        # print(int((round(nt%1,1)*10) % 2))
        # time.sleep(.04)
    '''
    yellow=gp.LED(4)
    yellow.on()
    time.sleep(2)
    green=gp.PWMLED(17)
    for i in range(10):
        green.value=i/10
        time.sleep(1)
    yellow.off()
    green.on()
    green.off()
    '''
    #for i in range(16):
    #    time.sleep(0.5)
    #    print(readRes(False))
    #print(readRes(True))
    #print(inTol(1000))
    #print(motorCtl(motorStairs,'f'))
    #time.sleep(3)
    #print(motorHold(True))
    #print(findChange(pinStairsLimitHi))
    #print(led(pinLED,.7))
    print(readSwitch(pinDrvErr))
    #print(goHome(motorStairs))
    #print(goCollect(motorStairs))
    #print(goDown(3200))
    #print(goRight(2700))
    #print(readRes(True,False))
    #print(waterPump(5))
    print(goHome(motorWalk))

    '''motor position testing
    time.sleep(1.5)
    print(motorCtl(motorStairs,'f'))
    time.sleep(2.5)
    print(motorCtl(motorStairs,'s'))
    time.sleep(1.0)
    print(motorCtl(motorStairs,'b'))
    time.sleep(3.0)
    print(motorCtl(motorStairs,'r'))
    time.sleep(1.0)
    print(motorCtl(motorStairs,'s'))
    '''
    '''xy=[[0,1],[2,3]]
    xy.append([4,5])
    print(xy)
    for z in xy:
        print(z)
        u=z[1]
        z=z[0]
        print(u)
        print(z)
    '''
    ''' STAIRS UP TEST
    tim0=time.time()
    mm=motorStairs
    while not readSwitch(pinStairsLimitHi) and time.time()<tim0+timeOutStairs:
        yo=motorCtl(mm,'f',1)
        time.sleep(.25)
        #print(readSwitch(21))
        #print(readSwitch(pinDrvErr))
    oy=motorCtl(mm,'l')
    led(pinLED,1)
    time.sleep(1.5)
    led(pinLED,0)
    #'''
    ''' STAIRS DOWN TEST
    led(pinLED,1)
    mm=motorStairs
    tim1=time.time()
    # and not readSwitch(pinStairsLimitHi)
    while not readSwitch(pinStairsLimitLo) and time.time()<tim1+timeOutStairs:
        ko=motorCtl(mm,'b',.5)
        time.sleep(.25)
        #print(readSwitch(pinDrvErr))
    ok=motorCtl(mm,'s')
    print(ok)
    led(pinLED,0)
    #'''
    ''' WALK SPEED AND POSITION TEST
    led(pinLED,1)
    mm=motorWalk
    print(goHome(mm))
    cc=['f','b']
    for i in range(2):
        gg=cc[i]
        #print(gg)
        tim0=time.time()
        while time.time()<tim0+timeOutWalk/2:
            if gg=='f' and readSwitch(pinWalkLimitHi):
                break
            elif gg=='b' and readSwitch(pinWalkLimitLo):
                break
            yo=motorCtl(mm,gg,.55)
            time.sleep(.25)
            #print(readSwitch(21))
            print(readSwitch(pinDrvErr))
        oy=motorCtl(mm,'s')
    print(oy)
    led(pinLED,0)
    #'''
    
    '''BASIC SERVO
    print(motorHold(True))
    time.sleep(2)
    print(motorHold(False))
    time.sleep(1)
    '''
    
    ''' SERVO TEST
    sval=-1
    while sval<=1:
        servo.value=sval
        time.sleep(0.15)
        sval+=.1
    #'''    
    '''
    servo.value=-.95
    time.sleep(1)
    servo.value=-.15
    time.sleep(1)
    servo.value=.95
    time.sleep(1)
    #'''
    
    '''
    led(pinLED,True)
    time.sleep(1)
    led(pinLED,False)
    led(pinFlash,True)
    time.sleep(3.5)
    led(pinLED,True)
    time.sleep(1)
    led(pinLED,False)
    led(pinFlash,False)
    #'''
    
    #print(readSwitch(pinStairsLimitHi))
    #print(readSwitch(pinStairsLimitLo))
    
    #print(readSwitch(pinWalkLimitHi))
    #print(readSwitch(pinWalkLimitLo))
    
    #print(readSwitch(pinIndicator))
    
    ''' SHAKE TEST
    motorCtl(motorStairs,'b',1)
    for t in range(4):
        time.sleep(0.75)
        motorCtl(motorStairs,'r',1)
    motorCtl(motorStairs,'s')
    #'''
    
    ''' WALK SPEED TEST
    print(goHome(motorWalk))
    tim2=time.time()+timeOutWalk*4
    sp=.18
    while not readSwitch(pinWalkLimitHi) and time.time()<tim2:
        sp*=1.2
        motorCtl(motorWalk,'f',sp)
        time.sleep(0.25)
    print(motorCtl(motorWalk,'s'))
    print(goHome(motorWalk))
    #'''
    
    ''' MORE POSITION TESTING
    print(goHome(motorWalk))
    s=.2
    while s<.3:
        motorCtl(motorWalk,'f',spd=s)
        while not readSwitch(pinWalkLimitHi):
            time.sleep(.01)
        print('\n',s)
        print(round(motorCtl(motorWalk,'f',posOnly=True),4))
        (motorCtl(motorWalk,'s'))
        s+=.1
        time.sleep(.2)
        goHome(motorWalk)
    #'''
    
    ''' CALC TEST
    gspd=-.2
    aspd=abs(gspd)
    vf=1.5440*pow(aspd,3)-3.8819*pow(aspd,2)+3.5434*pow(aspd,1)-0.20199*pow(aspd,0)
    dd=math.copysign(1,gspd)
    print(vf)
    print(dd)
    print(vf*dd*(3.173567))
    #'''
    
    '''STAIRS SPEED TESTING
    print(goHome(motorStairs))
    s=.8
    while s<=1:
        upup=motorCtl(motorStairs,'f')
        time.sleep(2)
        print(goHome(motorStairs))
        s+=.1
    #'''
