#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  sqlPlant.py
#  
# modifying the plant shelf database 
"""
Inputs:
    none
Outputs:
    none
"""
# Credit
# https://docs.python.org/3/library/sqlite3.html
# https://thejeshgn.com/2018/08/23/using-sqlite-with-libreoffice-base-on-linux/
# https://stackoverflow.com/questions/3247183/variable-table-name-in-sqlite
# https://ask.libreoffice.org/en/question/139052/base-how-to-connect-to-an-sqlite-database/
# https://ask.libreoffice.org/en/question/190869/cannot-create-or-read-records-in-a-sqlite-over-odbc-database/
# https://stackoverflow.com/questions/18420126/select-last-3-rows-of-sql-table
# https://pythonguides.com/python-check-if-the-variable-is-an-integer/


#modules
import sqlite3 as sql
import os
import sys
import time
import csvTool as csv

#variables
datFolder=os.path.split(os.path.abspath(__file__))[0]+'/databases/'
datFile=datFolder+'plantInfo.db'
latch=sql.connect(datFile)
db=latch.cursor()
today=time.strftime("%Y-%m-%d")
datLegend=datFolder+'plantLegend.csv'
plantLegend=csv.csvReadAll(datLegend) #resistor value, name, maturity, library code

#create tables
def makeTables():
    try:
        db.execute('''CREATE TABLE basics (
                        id integer PRIMARY KEY, 
                        active integer, 
                        name text, 
                        planted text,
                        harvested text, 
                        shelf integer, 
                        pot integer, 
                        maturity integer)''')
        latch.commit()
    except sql.OperationalError:
        print('Basics table exists')
    else:
        try:
                  #id(XX##)  active  name  planted  harvested  shelf  pot  maturity
            plants=[(101, 1, 'radish', today, '-', 0, 0, 28),
                    (201, 1, 'kale', today, '-', 0, 1, 65),
                    (301, 1, 'brussel', today, '-', 1, 0, 100),
                    (401, 1, 'spinach', today, '-', 1, 1, 48)
                    ]
            db.executemany('INSERT INTO basics VALUES (?,?,?,?,?,?,?,?)',plants)
            latch.commit()
        except sql.IntegrityError:
            print('  SQL ERR: Cannot duplicate a primary key')
    try:
        db.execute('''CREATE TABLE history (
                        id integer PRIMARY KEY,
                        plantID integer,
                        date text,
                        nvdi real)''')
        latch.commit()
    except sql.OperationalError:
        print('History table exists')
    #latch.close()
    print('tables made')

#read general entry
def readLine(tab, lineID): #str, int
    if lineID is None:
        return None
    pLine=db.execute('SELECT * FROM '+tab+' WHERE id=:lineID',{'lineID': lineID})
    pLine=db.fetchall() 
    #latch.close()
    return pLine #[*]

#read general item
def readItem(tab, lineID, itmName): #str, int, str
    if lineID is None:
        return
    iLine=db.execute('SELECT '+itmName+' FROM '+tab+' WHERE id='+str(lineID))
    iLine=db.fetchall()
    readVal=retStrip(iLine)
    #latch.close
    return readVal #*

#parse single returned item
def retStrip(val): #[[*]]
    if len(val)==0:
        return
    val=val[0]
    val=val[0]
    return val #*
    
#find basic plant
def getPlantID(shelf, pot, qrID=False): #integer, integer, string (...####)
    if qrID:
        if isinstance(qrID,str):
            try:
                pID=int(qrID[len(qrID)-4:len(qrID)])
            except ValueError:
                print('  SQL ERR: Value '+qrID+' was not a valid code')
                return None
        else:
            return qrID
    else:
        pID=db.execute('SELECT id FROM basics WHERE shelf=:v1 and pot=:v2 and active=1',{'v1': shelf, 'v2': pot})
        pID=db.fetchall()
        pID=retStrip(pID) if len(pID)>0 else None
    return pID #int

#find end of table in 1-index
def getLastLine(tableName): #str
    rc=db.execute('SELECT * FROM '+tableName)
    rc=len(db.fetchall())
    return rc #int

#add history line
def makeHist(shelf, pot, datPnt, qrID=False): #int, int, float, str (...####)
    #plant ID prefix
    datID=getPlantID(shelf, pot, qrID)
    #history ID
    histID=max(getLastLine('history'),1)+1
    #combine identifiers
    #print('datPnt=',datPnt)
    datArr=[histID]+[datID]+[today]+[round(datPnt,3)]
    print('datArr=',datArr)
    #convert to executable string
    datNew=str(datArr).replace('[','(')
    datNew=datNew.replace(']',')')
    #add to table
    print('\nMaking history:',datNew)
    try:
        newHist=db.execute('INSERT INTO history VALUES '+datNew)
        latch.commit()
        lineNum=getLastLine('history')
    except Exception as e:
        print('  SQL ERR: History table did not accept this')
        print(e)
        return None
    #print('Added to history: ',datArr)
    #latch.close
    return lineNum
    
#add new pot (with plant)
def makePot(shelf, pot, newLine):
    #newLine=[ID, plant name, maturity date]
    if (newLine is None) or (newLine[0] is None): #blank or bad code
        print('  SQL ERR: New pot not made at ('+str(shelf)+', '+str(pot)+') because no new information was provided.')
        return None
    potNew=[(newLine[0],1,newLine[1],today,'-',shelf,pot,newLine[2])]
    print('\nMaking a pot:',potNew)
    try:
        db.executemany('INSERT INTO basics VALUES (?,?,?,?,?,?,?,?)',potNew)
    except sql.IntegrityError:
        print('  SQL ERR: ID '+str(newLine[0])+' already exists in Basics')
        return 0
    latch.commit()
    return readLine('basics',newLine[0])

#get clean values from resistor reading
def getFromRes(resVal): #float or string (P####)
    tol=.2
    #qr-code sequence
    if isinstance(resVal,str):
        try:
            libEnt=int(resVal[1:3]) #class code of plant
        except:
            print('  SQL ERR: There was an error reading library entry '+resVal)
            return None
        plantInfo=None
        #generic info for that class code
        for e in range(len(plantLegend)):
            if plantLegend[e][3]==str(libEnt):
                plantInfo=plantLegend[e]
    #resistor value library
    else: 
        for i in range(len(plantLegend)):
            legendRes=plantLegend[i][0]
            try:
                legendRes=int(legendRes)
                if (1-tol)*legendRes<=resVal and resVal<=(1+tol)*legendRes:
                    plantInfo=plantLegend[i]
            except:
                if legendRes!='resistor value':
                    print('  SQL ERR: ',str(legendRes),' refuses')
    return plantInfo #[res val, name, maturity, library code]

#update missing plant as harvested
def harvestPlant(shelf, pot, qrID=False): #integer, integer, string
    plantSpot=getPlantID(shelf, pot, qrID)
    if plantSpot is None:
        return
    db.execute("UPDATE basics SET active=0, harvested='"+today+"' WHERE id="+str(plantSpot)+" and active=1")
    latch.commit()
    return readLine('basics',plantSpot)

#update removed/replanted pot
def updatePot(shelf, pot, newPlant, forceChange=False):#location (integer), location (integer), id (float or string P####), override (bool)
    print('Updating '+newPlant+' at ('+str(shelf)+', '+str(pot)+')')
    #get current plant credentials or create new
    plantInfo=getFromRes(newPlant) #library entry list
    if plantInfo is None: #unknown
        plantInfo=[newPlant, 'unknown', 0, 0]
    print(plantInfo)
    [newRes,newName,newMat,newCode]=plantInfo #vernacular
    #get database plant credentials
    plantSpot=getPlantID(shelf, pot, newPlant) #plant id (gives integer)
    print('plantSpot=',plantSpot)
    oldName=readItem('basics',plantSpot,'name')
    print('oldName=',oldName)
    #update location for list accuracy
    try:
        db.execute('UPDATE basics SET shelf='+str(shelf)+', pot='+str(pot)+' WHERE id='+str(plantSpot))
        latch.commit()
    except:
        print(Exception)
        print('There was an issue updating this location')
    #QR CODE METHOD
    if isinstance(newPlant,str):
        #Rectify error, Add new, or Force a swap
        if (plantSpot is None) or (oldName is None):# or forceChange:
            #oldPlant=harvestPlant(shelf, pot, plantSpot) #activated only on error of name conflict.
            #print('oldPlant',oldPlant)
            #nameCount=db.execute('SELECT * FROM basics WHERE name=:nameType',{'nameType': newName})
            #nameCount=db.fetchall()
            #plantSpot=int(newCode)+len(nameCount)+1
            potMade=makePot(shelf, pot, [plantSpot,newName,newMat,newCode])
            print('potMade=',potMade)
            latch.commit()
            if plantSpot is not None and plantSpot!=0:
                print(newName+' placed in ('+str(shelf)+', '+str(pot)+')')
    #RESISTOR METHOD
    else:
        #'''
        #assumes grid pattern
        #assumes no plant moves
        #Only look at active or new plants
        isActive=readItem('basics',plantSpot,'active')
        if isActive==1 or forceChange:
            #Retire old on change, Add new, or Force a swap
            if newName!=oldName or (plantSpot is None) or forceChange:
                oldPlant=harvestPlant(shelf, pot)
                plantSpot=getLastLine('basics')+1
                potMade=makePot(shelf, pot, [plantSpot,newName,newMat])
                latch.commit()
                print(str(shelf)+', '+str(pot)+' was '+oldName+', now '+newName)
        #'''
    plantLine=readLine('basics',plantSpot)
    #latch.close
    return plantLine

#collect last three lines of plant's health history
def readLast3(pID):
    #I recognize the spelling error, but I'm too lazy to change it
    pHist=db.execute('SELECT nvdi FROM history WHERE plantID='+str(pID)+' ORDER BY date DESC LIMIT 3')
    pHist=db.fetchall()
    for index, val in enumerate(pHist):
        pHist[index]=val[0]
    #pHist.reverse()
    #latch.close()
    pHist=[0] if len(pHist)==0 else pHist
    return pHist #[[float]]
    
#collect ID and name for all active locations or one ID
def readShelfPot(pID=False):#string (X###)
    if pID: #one specific location
        loc=[readItem('basics',pID,'shelf'),readItem('basics',pID,'pot')]
        return loc #[int, int]
    else: #all active locations
        loc=db.execute('SELECT shelf, pot, name, id FROM basics WHERE active=1')
        loc=db.fetchall()
#        print(loc)
        #for index, val in enumerate(loc):
         #   print(val[1])
          #  loc[index]=val[0]
        return sorted(loc) #[[int, int, str, int]]
        
#set plant record to inactive
def killPlant(pID): #int, int, str or int
    k=db.execute("UPDATE basics SET active=0 WHERE id="+str(pID))
    latch.commit()
    return readLine('basics',pID) #[[*]]

#return active IDs that were not in the given list
def getUnseen(seeList): #tuple
    a=db.execute('SELECT id FROM basics WHERE active=1')
    a=db.fetchall()
    nse=[i[0] for i in a if i[0] not in seeList]
    #latch.close()
    return nse
    
#close the database
def closeDB():
    latch.close()
    return


#test values
if __name__=='__main__':
    #makeTables()
    #print(readLine('basics', 3))
    #print(getPlantID(1,1))
    #print(getLastLine('basics'))
    #print(makeHist(1,0,[.5]))
    #print(readLine('history', getLastLine('history')))
    #print(readItem('basics',2,'maturity'))
    #print(getLastLine('history'))
    #latch.close
    #print(updatePot(1,0,2000,False))
    #db.execute('UPDATE basics SET pot=pot+1 WHERE shelf=1')
    #print(readLine('basics',3))
    # gg=[(4,'a',6),(7,'v',9)]
    # [a,b,c]=gg[1]
    # print(a)
    #for i in range(len(plantLegend)):
    #    print(plantLegend[i])
    '''
    print(int(plantLegend[1][0])+1)
    lineBasic=updatePot(1,0,3000,False)
    print(lineBasic[0][0])
    potMaturity=lineBasic[0][7]#int
    print(potMaturity)
    potPlanted=lineBasic[0][3]#str YYYY-MM-DD
    print(potPlanted)
    potPlanted=time.strptime(potPlanted,'%Y-%m-%d')
    print(potPlanted)
    print(potPlanted.tm_mon)
    potP0=potPlanted.tm_year*365+potPlanted.tm_yday
    todays=time.strptime(today,'%Y-%m-%d')
    potP1=todays.tm_year*365+todays.tm_yday
    print(potP1-potP0)
    if int(potMaturity)<potP1-potP0:
        print('mature')
    else:
        print(int(potMaturity)-(potP1-potP0))
    '''
    #print(readLast3(3))
    #print(plantLegend)
    #print(updatePot(1,0,3000,True))
    
    '''
    l1=[[2,0,'nm1','id1'],[1,1,'nm2','id2'],[1,0,'nm4','id4']]
    l2=[[1,1,'nm3','id3'],[1,0,'nm4','id4'],[0,0,'nm1','id1']]
    #print(sorted(l1))
    #print(sorted(l2))
    l3=[]
    lt='j\ti\tl1n\tl1i\tl2n\tl2i\n'
    s1max=[e[0] for e in l1]
    s2max=[e[0] for e in l2]
    smax=max(max(s1max),max(s2max))
    print(smax)
    p1max=[e[1] for e in l1]
    p2max=[e[1] for e in l2]
    pmax=max(max(p1max),max(p2max))
    print(pmax)
    subA=''
    for j in range(smax+1):
        for i in range(pmax+1):
            sub0=str(j)+'\t'+str(i)+'\t'
            sub1='-\t-'
            sub2=sub1
            print('sub0',sub0)
            dash1=True
            dash2=True
            for p in l1:
                if p[0]==j and p[1]==i:
                    sub1=(str(p[2])+'\t'+str(p[3]))
                    print('sub1',sub1)
                    dash1=False
                    break
            for p in l2:
                if p[0]==j and p[1]==i:
                    sub2=(str(p[2])+'\t'+str(p[3]))
                    print('sub2',sub2)
                    dash2=False
                    break
            sub2+='(!)' if (sub1!=sub2 and (not dash1 and not dash2)) else ''
            subA+=sub0+sub1+'\t'+sub2+'\n'
            print('subA',subA)
    print('fin')
    print(lt+subA)
    #'''
    '''
    for i1 in l1:
        for i2 in l2:
            #print('row')
            #print(i1[0],i2[0])
            if i1[0]==i2[0]:
                #print('col')
                #print(i1[1],i2[1])
                if i1[1]==i2[1]:
                    #print('app')
                    pile=i1
                    pile.extend(i2[2:4])
                    l3+=[pile]
    print(l3)
    for x2 in l2:
        for i3 in l3:
            if x2[0]==i3[0] and x2[1]==i3[1]:
                pass
            else:
                x2.insert(0,'-')
                x2.insert(0,'-')
                print(x2)
                #l3.append([x2])
    
    print(l3)
    #'''
    
    #print(makePot(1,2,[501,'corn',96]))
    #print(readLine('basics',501))
    #print(readItem('basics',None,'planted'))
    #print(getPlantID(0,0,'0501'))
    #print(makeHist(1,2,[2.1]))
    #print(getFromRes('P0501'))
    #print(updatePot(1,2,'P0501'))
    #print(updatePot(1,2,'P0502'))
    #print(harvestPlant(1,23,'0501'))
    #print(readLast3(5))
    #cas=(readShelfPot())
    #print(gardenTable(cas,cas,[[1,2,3],[4,5,6]],[[7,8,9],[10,11,12]]))
    #print(killPlant(502))

    #print(getUnseen([1,2,3,6]))
    
    '''quick one-liner check
    pHist=[1,4,6]
    pHist=[0] if len(pHist)==0 else pHist
    print(pHist)
    #'''
