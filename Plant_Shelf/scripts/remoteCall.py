#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  remoteCall.py
#  Starting point for the PlantShelf project
"""
Inputs:
    none
Outputs:
    none
"""
# Credit:
#https://stackoverflow.com/questions/23364096/how-to-write-output-of-terminal-to-file#23364428
#https://www.howtogeek.com/437958/how-to-use-the-chmod-command-on-linux/
#https://stackoverflow.com/questions/44207531/why-am-i-not-able-to-use-python-3-in-a-crontab
#https://stackoverflow.com/questions/5326112/how-to-round-each-item-in-a-list-of-floats-to-2-decimal-places
#https://stackoverflow.com/questions/8194156/how-to-subtract-two-lists-in-python
#https://stackoverflow.com/questions/14550370/compare-list-in-python-to-detect-an-equality
#https://numpy.org/doc/stable/reference/generated/numpy.any.html

#modules
import os
import sys
import time
import fileLogger
import sqlPlant
#import emailOne
import emailDir
import hardware as hw
import qrPlant as qP
import numpy as np
#import wifiCheck as wf
import camPlant as cam
import gpiozero as gp

#variables
mailA='nilles.rpi@gmail.com'
allGood=True
mS=hw.motorStairs
mW=hw.motorWalk
deadPlant=0.001 #ndvi

#init
#6 18 * * * /usr/bin/python3 /home/an/Documents/PlantShelf/remoteCall.py
print('BEGIN')



#-----------
#FUNCTION LIST

#dates and times
def curDate():
    return time.strftime("%Y-%m-%d")
def curTime():
    return time.strftime("%H:%M:%S")

#subtract today's date from given date
def dateAddNow(potPlanted): #YYYY-MM-DD
    potPlanted=time.strptime(potPlanted,'%Y-%m-%d')
    potP0=potPlanted.tm_year*365+potPlanted.tm_yday
    potObserved=time.strptime(curDate(),'%Y-%m-%d')
    potP1=potObserved.tm_year*365+potObserved.tm_yday
    return potP1-potP0 #int positive if date has past

#check if a directory exists and is accessible, make one if not
#returns valid path of directory
def makeDir(newPath):
    if not os.access(newPath,os.F_OK):
        os.mkdir(newPath)
    return newPath+'/'

#executes move command in terminal
#input: two full paths
#output: nothing
def fileMV(src,dest): #str, str
    cmd="mv '"+src+"' '"+dest+"'"
    os.system(cmd)
    return True

#analyze given code at given location
#return ndvi single value, ndvi average for that code, and bool for water
def remoteAnalyze(shelf, pot, iPlant, qrTitle): #int, int, str, str
    print('\n----ANALYZE----')
    print('Analyzing',shelf,pot,iPlant,qrTitle)
    print('\n----SQL PLANT----')
    #update database
    lineBasic=sqlPlant.updatePot(shelf, pot, iPlant)
    if lineBasic is None:
        addLog('Code '+iPlant+' at '+str(shelf)+', '+str(pot)+' was invalid. Skipping')
        fail.add('Code '+iPlant+' at ('+str(shelf)+', '+str(pot)+') caused SQL errors.')
        return [None,None,False]
    myID=lineBasic[0][0]
    myName=lineBasic[0][2]
    #add log and increment
    imgName=myName+' '+str(myID)+' ('+str(shelf)+', '+str(pot)+')'
    imgName+=qrTitle[len(qrTitle)-qrTitle[::-1].find('.')-1:len(qrTitle)]
    addLog('Saving image of '+imgName)
    
    print('\n----CAMERA----')
    #save image for records
    recordImage=newDay+imgName
    #recordImage=cam.photo(recordImage) #renaming instead
    mvBool=fileMV(qrTitle,recordImage)
    
    #check if it is in its lifecycle
    potMaturity=int(lineBasic[0][7])#number of days
    potLife=dateAddNow(lineBasic[0][3])#str YYYY-MM-DD -> num days
    if potLife>.2*potMaturity:
        addLog(' This '+myName+' is past its germination date')
        getNDVI=True
    elif potLife>.1*potMaturity:
        addLog(' This '+myName+' might be past its germination date')
        getNDVI=True
    else: #assume it needs water
        addLog(' This '+myName+' has '+str(round(0.2*potMaturity-potLife,0))+' days til germination')
        print('Pot skipped since it has not sprouted yet')
        getNDVI=False
        watTF=True
    
    #calculate and record health if necessary
    ndviAvg=np.mean(sqlPlant.readLast3(myID)) #float
    if getNDVI:
        #Calculate the health via near-infrared light emission
        iGather=cam.ndviCalc(recordImage) #ndvi
        if iGather is not None:
            addLog(' it has an ndvi='+str(iGather))
            #Record the finding
            print('\n----SQL PLANT----')
            #return to database
            lineHistory=sqlPlant.makeHist(shelf, pot, iGather, iPlant)
            if lineHistory is None:
                fail.add('History could not be made for '+str(iPlant))
        else:
            iGather=np.mean(sqlPlant.readLast3(myID))
            addLog(' and something went wrong with the mask. Assuming average of '+str(round(iGather,3)))
    else:
        iGather=None
    
    #Deactivate dead plants
    if (iGather is not None) and iGather<deadPlant:
        watTF=False
        addLog(" and it's probably dead")
        #compare last three days' readings to inactivate
        if ndviAvg<deadPlant and ndviAvg!=0:
            pGone=sqlPlant.killPlant(myID)
            addLog(" and now it's inactivated")
            global listDead
            listDead+=str(ndviAvg)+' '+imgName+'\n'
        else:
            global listDying
            listDying+=str(ndviAvg)+' '+imgName+'\n'
    else:
        watTF=True
    
    return iGather, ndviAvg, watTF

#run the length of the shelf and collect all codes available
#return *seen IDs, *ndvi values, *ndvi average histories, and bool critical error
def remoteWalk(shelf, allGood): #int, bool
    print('\n----REMOTE WALK----')
    #motor control
    lowspeed=.18
    mWspeed=lowspeed
    viewEscape=1.1 #seconds
    print('\n----HARDWARE----')
    mW_go=hw.goHome(mW)
    #logistics
    potCount=0
    cycleCount=0
    potPrev=[]
    firstEmpty=True
    #reports
    seenList=[] #active plants
    ndviList=[] #today's values
    ndviAvg=[] #last three runs' values
    
    while (not hw.readSwitch(hw.pinWalkLimitHi)) and allGood:
        print('\n\nStarting finder cycle '+str(cycleCount)+' on shelf '+str(shelf))
        cycleCount+=1
        
        print('\n----QR CODES----')
        #find the corresponding code
        potDyn, mWspeed, mW_stop=qP.qrDynamic(2*hw.timeOutWalk,mWspeed) #list of codes (P####) str, adjusted walk speed
        #reference location
        refLoc='['+str(shelf)+','+str(potCount)+':'+str(mW_stop)+'] '
        addLog('Stopped for a picture of '+str(potDyn)+' at '+refLoc)
        #qrDynamic finder error check
        if isinstance(potDyn,str):
            print('Received:')
            if potDyn.find('LIMIT')>=0:
                print('  returning to home after limit switch hit')
                break
            if potDyn.find('TIME')>=0:
                print('  qrDynamic timeout trigger tripped')
                mWspeed*=1.1
                print('Walk speed +increased to '+str(round(mWspeed,3))+' after timeout')
                continue
            else:
                print('  some other error happened in qrDynamic')
                addLog('CRITICAL: unknown error in qrDynamic receiving')
                fail.add('CRITICAL: unknown error in qrDynamic receiving')
                allGood=False
                break
        else:
            #take big pic and find the code again
            print('\n----CAMERA----')
            mugshot=cam.photo(newDay+'qr '+refLoc[0:len(refLoc)-1])
            print('New image saved to '+mugshot)
            print('\n----QR CODES----')
            pot=qP.qrStatic(mugshot)
        
        #Position error checking
        print('\n----REMOTE----')
        if pot is None: #no codes were found
            if firstEmpty: #first time coming up with nothing in a while
                firstEmpty=False
                print('There were no codes found within a stop at '+refLoc)
                addLog('Check '+mugshot+' for clarity')
            elif abs(mW_stop-mW_go)<=mWspeed*(viewEscape+.25): #somehow we're tripping too frequently
                addLog('Walk did not move much. Increasing motor power '+refLoc)
                mWspeed+=.1
                print('Walk speed ++increased to '+str(round(mWspeed,3))+' after small carriage displacement')
                if mWspeed>1:
                    fail.add(refLoc+'Walk power maxed out. Homing will be attempted')
                    mW_home=hw.goHome(mW)
                    if mW_home>=hw.timeOutWalk:
                        fail.add(refLoc+'Walk homing timed out. Ending.')
                        addLog('CRITICAL: Walk motor could not be homed near '+refLoc)
                        allGood=False
                    break
            else: #this shelf may be empty
                mWspeed*=1.1 #increasing motor speed again
                print('Walk speed *increased to '+str(round(mWspeed,3))+' after multiple empty results')
                fail.add(refLoc+'There is way too much space in this area')
        #Code error checking
        else: #there were one or more codes found
            if not np.any([True for i in pot if i in potDyn]): #it moved or something
                print('Dynamic found '+str(potDyn)+', but Static found '+str(pot))
                fail.add(refLoc+'The camera picked up different center codes between video and static images')
                pot=potDyn
                print('Proceeding with '+str(pot))
            if np.any([True for j in pot if j in potPrev]): #we never left square one
                print('Walk did not leave code '+str(potPrev)+' from set '+str(pot))
                fail.add(refLoc+'A code ('+str(pot)+') near here had a repeat read')
            
            #Good pot analysis
            else: #one or more unique pots were found
                firstEmpty=True
                for iPlant in pot: #sifting through centered codes in image
                    print('\nAnalyzing '+iPlant)
                    #make sure it is a pot
                    if not iPlant[0]=='P':
                        print('That was not a pot. Moving on')
                        continue
                        
                    potPrev=iPlant
                    
                    #check if it is active/new
                    newID=sqlPlant.getPlantID(shelf,potCount,iPlant)
                    if newID is None: #bad code
                        print(' thrown out for being of bad format')
                        continue
                    actStatus=sqlPlant.readItem('basics',str(newID),'active')
                    
                    #Plant recording
                    if actStatus==None or int(actStatus)==1: #new or current
                        seenList.append(newID)
                        ndviS, ndviA, watTF=remoteAnalyze(shelf, potCount, iPlant, mugshot)
                        #on errors, assume a growing pot
                        if ndviS is None:
                            ndviS, ndviA, watTF = [0, 0, True]
                        ndviList.append(round(ndviS,2)) #today's value
                        ndviAvg.append(ndviA) #last three reading's average
                        water.append(watTF) #decision of watering or not
                    else: #there is still an inactive pot here
                        print(' but it is inactive')
                        global listInactive
                        listInactive+=str(newID)+' '+refLoc+'\n'
                    potCount+=1
                    
                #reset for next walk search
                mWspeed=lowspeed
                #end of iPlant list
            
        #motor position check
        if mW_stop>2*hw.timeOutWalk/mWspeed: #the pulley/rope has likely broken
            fail.add(refLoc+'The walk motor spun for '+str(mW_go)+', and I think that is a bit much.')
            addLog('CRITICAL: Walk motor moved out of bounds to '+str(mW_go))
            allGood=False
        
        #reset for next cycle
        mW_go=mW_stop
    
    print('\n----HARDWARE----')
    #return to start
    mW_home=hw.goHome(mW)
    
    return seenList, ndviList, ndviAvg, allGood

#climb to the next shelf is indicated by a QR code marker
#input: anticipated shelf number
#output: shelf number or error string, big conditional trigger
def remoteStairs(shelf):
    print('\n----REMOTE STAIRS----')
    #motInit=hw.goUp() #seconds to first/second shelf
    wHome=hw.goHome(hw.motorWalk)
    #shldr=hw.motorHold(False)
    sFound,sSpeed,sPos=qP.qrDynamic(hw.timeOutStairs,motInt=hw.motorStairs)
    lockS=hw.motorCtl(hw.motorStairs,'l')
    #error check
    if isinstance(sFound,str):
        print('Received:')
        if sFound.find('LIMIT')>=0:
            print('  returning to home after limit switch hit')
            return 'end',True
        if sFound.find('TIME')>=0:
            print('  qrDynamic timeout trigger tripped')
            fail.add('CRITICAL: The Stairs could not find/reach shelf '+str(shelf))
            addLog('CRITICAL: The stairs have timed out')
            return None, False
        else:
            print('  some other error happened in qrDynamic')
            fail.add('CRITICAL: '+str(sFound)+' found by Stairs')
            addLog('CRITICAL: unknown Stair error, '+str(sFound))
            return 'end',False
    #actionable find
    else:
        #shldr=hw.motorHold(True)
        for sQR in sFound:
            if sQR[0]=='S':
                sHere=sqlPlant.getPlantID(shelf,-1,sQR)
                if shelf!=sHere:
                    fail.add('Shelf expected: '+str(shelf)+'\nShelf found: '+str(sHere))
                return sHere, True
        #a plant code got in the way
        print('ERR: code '+str(sFound)+' found instead of shelf')
        return None, True
    #done messed up
    return None, False
        

#return the greater count of True/False in a boolean list
def avgBool(tfArr): #tuple of bools
    nt=tfArr.count(True) #or existing, at least
    nf=tfArr.count(False)
    return nt>=nf #bool

#merge and sort garden lists
def gardenTable(l1, l2, v1, v2): #tuples [shelf, pot, name, id], tuples NDVI by current pot
    #1=yesterday
    #2=today
    print('Tabling:')
    print('l1 =')
    print(l1)
    print('l2 =')
    print(l2)
    print('v1 =')
    print(v1)
    print('v2 =')
    print(v2)
    #header row
    titles=['Shelf','Pot','Yest. Name','Yest. ID','Today Name','Today ID','NDVI@IDnow','NDVI avg delta']
    lt='\t'.join(titles)+'\n'
    try:
        #shelf and pot column limits
        s1max=[e[0] for e in l1]
        s2max=[e[0] for e in l2]
        smax=max(max(s1max),max(s2max))
        p1max=[e[1] for e in l1]
        p2max=[e[1] for e in l2]
        pmax=max(max(p1max),max(p2max))
    except Exception as e:
        print(e)
        subA='Something went wrong sifting through the lists'
    else:
        #data offset
        if max(s2max)<smax: #yesterday had another shelf reported
            jO=1 if max(s2max)>0 else 0 #bump up to second row
        else:
            jO=0
        if max(p2max)<pmax: #yesterday had more pots reported
            iO=min(p1max)-min(p2max) #should always be 0, but why not
        else:
            iO=0
        subA=''
        print('(j0, i0)=('+str(jO)+', '+str(iO)+')')
        print('(smax, pmax)=('+str(smax)+', '+str(pmax)+')')
        try:
            for j in range(smax+1):
                for i in range(pmax+1):
                    sub0=str(j)+'\t'+str(i)+'\t'
                    sub1='-\t-'
                    sub2=sub1
                    dash1=True
                    dash2=True
                    #comparing per coordinated pot set
                    for p in l1:
                        if p[0]==j and p[1]==i:
                            sub1=(str(p[2])+'\t'+str(p[3]))
                            dash1=False
                            break
                    for p in l2:
                        if p[0]==j and p[1]==i:
                            sub2=(str(p[2])+'\t'+str(p[3]))
                            dash2=False
                            break
                    sub2+='(!)' if (sub1!=sub2 and (not dash1 and not dash2)) else ''
                    try:
                        sub3=str(round(v1[j+jO][i+iO],3))+'\t'+str(round(v2[j+jO][i+iO],3))+'\n'
                    except Exception as e:
                        print(e)
                        sub3='-\t-\n'
                    subA+=sub0+sub1+'\t'+sub2+'\t'+sub3+'\n'
        except Exception as e:
            print(e)
            subA+='String compilation went wrong'
    return (lt+subA) #text string in table format


#'''
#----------
#LOG MANAGEMENT
#all program interaction saved as text

#define folder structure
curDir=os.path.split(os.path.abspath(__file__))[0]+'/'
#today's records
day2day=makeDir(curDir+'daily')
newDay=makeDir(day2day+curDate())
#general setup
datumDir=makeDir(curDir+'databases')
setupDir=makeDir(curDir+'setup')
reportDir=makeDir(setupDir+'report')

#begin console output log
cronFile=setupDir+'wifiLog.log' #from wifiCheck crontab
termFile=newDay+'terminalLog.txt' #for all other scripts
postFile=newDay+'terminalErr.txt' #for all errors
cmdFile=open(termFile,'w+')
errFile=open(postFile,'w+')
sys.stdout = cmdFile
sys.stderr = errFile
print(curDate())
print(curTime())

#begin procedure log
newLog=newDay+'runLog.txt' #high-level overview
def addLog(newEntry):
    newTime=curTime()+'\t'
    runLog=fileLogger.txtMod(newLog,newTime+newEntry)
addLog('----------')
addLog('remoteCall begin')
fail=set() #list of name-able critical errors

#check internet (already done in crontab)
#wf
#'''

#----------
#'''TESTING

'''ONE POT TEST
shelf=0
pot=1
myQR='P0102'
print(remoteAnalyze(shelf,pot,myQR))
#'''

'''ONE SHELF TEST
shelf=0
print(remoteWalk(shelf,allGood))
#'''

'''LIST COMPARISON
l0=[]
l1=['rewq']
l2=['asdf','qwer']
l3=['yuio','asdf']
l4=['qwer']
print([x==y for (x,y) in zip(sorted(l2),sorted(l4))])
print(np.any([x==y for (x,y) in zip(sorted(l2),sorted(l4))]))
print(set(l2)&set(l4))
print([True for i in l4 if i in l2])
print(np.any([True for i in l4 if i in l2]))
#'''

'''STAIR CLIMB TEST
print(hw.goHome(hw.motorStairs))
print(hw.goHome(hw.motorWalk))
print(remoteStairs(0))
#time.sleep(1)
water=[]
print(remoteWalk(0,True))
print(hw.goHome(hw.motorStairs))
#'''

'''FILE MOVE TEST
f0='/home/an/Documents/PlantShelf/daily/2021-01-07/'
f1=f0+'qr [0,0:0.865] (1).jpg'
f2=f0+'qr [0,0:0.865] (2).jpg'
print(fileMV(f1,f2))
#'''

#print(fail)
#print(sqlPlant.latch.close())
#'''

#'''
#-----------
#GATHER DATA
#Move motors and take pictures

#first-run prep
print('\n----SQL PLANT----')
sqlPlant.makeTables()

#report prep
newReport='Summary from '+curDate()+'\n\n'
ndviAll=[]
ndviHist=[]
listInactive=''
listDying=''
listDead=''
gardenY=sqlPlant.readShelfPot() #list of all active items from last time
#watering indices
water=[]


#from top left, moving right and down
print('\n----HARDWARE----')
#'''

#VISUAL CODE BASED LOOP
#'''
#go down,
mS_start=hw.goHome(mS)
print(str(mS_start)+' seconds to home Stairs')
if mS_start>=0.1*hw.timeOutStairs:
    fail.add('First Stairs homing took a long time')
mW_start=hw.goHome(mW)
if mW_start>=0.1*hw.timeOutWalk:
    fail.add('First Walk homing took a long time')
#then up
shelf=0
plantsSeen=[]
while shelf<2: #physical limit of built shelf
    #search for shelf
    print('\nBeginning of finding shelf'+str(shelf))
    mS_go, allGood=remoteStairs(shelf)
    #evaluate any errors
    if not allGood:
        fail.add('The Stairs stalled out in round '+str(shelf))
        break
    if mS_go=='end':
        #limit reached
        mS_go=int(hw.motorCtl(hw.motorStairs,'s',posOnly=True))
        break
    elif mS_go is None:
        fail.add('Something got in the way of a shelf code in round '+str(shelf))
        continue
    elif mS_go<shelf:
        fail.add('The Stairs came across a lower value shelf than expected. Trying again.')
        continue
    else:
        #gather the pot contents on that shelf
        shelf+=1
        #give it two chances in case the camera doesn't start up right away
        for u in range(2):
            shelfSeen, ndviList, ndviAvg, allGood=remoteWalk(mS_go, allGood)
            if len(shelfSeen)>0:
                break
        
        #end of pot collection
        if not allGood:
            break
            
        #update ndvi list by shelf
        plantsSeen.extend(shelfSeen)
        ndviAll.append(ndviList)
        ndviHist.append([x1-x2 for (x1, x2) in zip(ndviList,ndviAvg)])
        
    #end shelf list
#any supposedly active plants that were not recorded
listUnseen=sqlPlant.getUnseen(plantsSeen)
#'''

#RESISTOR BASED LOOP
'''
#go to top row
#establish number of shelves
print('Finding shelves')
shelfList=[round(ss, 2) for ss in hw.goCollect(mS)]
shelfList.reverse();
addLog('shelfList='+str(shelfList))
iw=-1
jw=iw
ndviList=[]
for shelf in shelfList:
    shelfPosition=shelf[1]
    shelf=shelf[0]
    thisShelf=hw.goDown(shelf)
    addLog('Shelf: expected='+str(shelf)+'; actual='+str(thisShelf))
    jw+=1
    #run length of row
    #establish number of pots
    potList=hw.goCollect(mW)
    addLog('Pots at '+str(thisShelf)+': '+str(potList))
    for pot in potList:
        print('\n----HARDWARE----')
        potPosition=pot[1]
        pot=pot[0]
        #restart at left of row and increment
        iPlant=hw.goRight(pot)
        iOverride=hw.readSwitch(0)
        print('\n----CAMERA----')
        #take temporary image & analyze
        tempImg=newDay+'temp'
        tempImg=cam.photo(tempImg)
        iGather=cam.ndviCalc(tempImg) #ndvi
        ndviList.append(round(iGather,2))
        os.remove(tempImg)
        print('\n----SQL PLANT----')
        #update database
        lineBasic=sqlPlant.updatePot(shelf, pot, iPlant, iOverride)
        myID=lineBasic[0][0]
        myName=lineBasic[0][2]
        lineHistory=sqlPlant.makeHist(shelf, pot, iGather)
        #add log and increment
        imgName=myName+' '+str(myID)+' ('+str(shelf)+', '+str(pot)+')'
        addLog(imgName)
        #if it needs water
        iw+=1
        water[iw,jw]=True
        #check if it is in its lifecycle
        potMaturity=int(lineBasic[0][7])#number of days
        potPlanted=lineBasic[0][3]#str YYYY-MM-DD
        potPlanted=time.strptime(potPlanted,'%Y-%m-%d')
        potP0=potPlanted.tm_year*365+potPlanted.tm_yday
        potObserved=time.strptime(curDate(),'%Y-%m-%d')
        potP1=potObserved.tm_year*365+potObserved.tm_yday
        if .2*potMaturity<(potP1-potP0):
            addLog(myName,' past germination date')
            if iGather<.1:
                water[iw,jw]=False
                addLog(" and it's probably dead")
                #compare last three days' readings to inactivate
                ndviAvg=sum(sqlPlant.readLast3(myID))/3
                if ndviAvg<.1:
                    pGone=sqlPlant.harvestPlant(shelf, pot)
                    addLog(" and now it's harvested")
            else:
                addLog(' and has an ndvi=',str(iGather))
        #save image for records
        recordImage=newDay+imgName
        recordImage=cam.photo(recordImage)

    print('\n----HARDWARE----')
    hw.led(hw.pinFlash,0)
    mW_time=hw.goHome(mW)
    addLog('Shelf homed in '+str(mW_time))
#'''

#'''
#-----------
#FINAL MOVES
hw.led(hw.pinFlash,0)
#stair homing
mS_time=hw.goHome(mS)
addLog('Stairs homed in '+str(round(mS_go-mS_time,2))+' sec.') if isinstance(mS_go,int) else addLog('Stair homing not attempted due to previous fail')
#Allocate water
if avgBool(water):
    hw.waterPump(t=15)
else:
    fail.add('There were not enough active or healthy pots to warrant water use')
#'''

#'''
#-----------
#WRAP-UP
print('\n----FINAL----')

#report composition
if not allGood:
    newReport+='CRITICAL ERRORS ENCOUNTERED\n'
newReport+='Dying:\n'+str(listDying)+'\n'+'Dead:\n'+str(listDead)+'\n'
newReport+='Seen and inactive:\n'+str(listInactive)+'\n'
newReport+='Active but not seen:\n'+str(listUnseen)+'\n'
newReport+='Errors:\n'+'\n'.join(fail)+'\n\n'
gardenT=sqlPlant.readShelfPot() #[shelf, pot, name, id]
sqlPlant.closeDB()
gardenR=gardenTable(gardenY,gardenT,ndviAll,ndviHist)+'\n'
newReport+='Data:\n'+gardenR+'\n'

#file consolidation
addLog('remoteCall end')
addLog('emailOne begin')
cmdFile.close()
errFile.close()
sys.stdout=sys.__stdout__
sys.stderr=sys.__stderr__
os.system('cp '+cronFile+' '+newDay+'wifiCheck.log') #from wifiCheck
os.system('cp '+termFile+' '+reportDir+'cmdFile.txt') #from cmdFile
os.system('cp '+postFile+' '+reportDir+'errFile.txt') #from errFile
os.system('cp '+newLog+' '+reportDir+'addLog.txt') #from addLog

#email composure
#newAttachment='/home/an/Documents/PlantShelf/setup/wifiLog.log'
newAttachment=reportDir
newBody=newReport+'end of report\n'
#newMsg=emailOne.sendEmail(mailA,'PlantShelf report',newBody,newAttachment)
newMsg=emailDir.sendEmail(mailA,'PlantShelf report for '+curDate(),newBody,newAttachment)

#'''
