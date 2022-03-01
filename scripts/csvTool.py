#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  csvTool.py
#  
# Manipulate CSV files
"""
Inputs:
    fullPath, string, file name with .csv
Outputs:
    per function
"""
# Credit
# httsp://docs.python.org/3/library/csv.html
# https://stackoverflow.com/questions/16108526/count-how-many-lines-are-in-a-csv-python


#modules
import csv

#variables


#create new
def csvCreate(fullPath):
    print(fullPath)
    try:
        myCSV=open(fullPath,'x')
    except FileExistsError:
        print('File '+fullPath+' already exists')
        return 0
    else:
        myCSV.close
        nameSplit=fullPath.split('/')
        return nameSplit[-1]

#write to
def csvWrite(fullPath,newArray):
    try:
        myCSV=open(fullPath,'w+',newline='')
    except Exception as e:
        print('Something went wrong writing to '+fullPath)
        print(e)
        return 0
    else:
        myWriter=csv.writer(myCSV,delimiter=',',quotechar='|',quoting=csv.QUOTE_MINIMAL)
        myWriter.writerows(newArray)
        fieldLimit=csv.field_size_limit()
        myCSV.close
        return fieldLimit

#read from
def csvRead(fullPath,thisRow,thatCol):
    try:
        myCSV=open(fullPath,'r')
    except Exception as e:
        print('Something went wrong reading '+str(thisRow)+', '+str(thatCol)+' from '+fullPath)
        print(e)
        return 0
    else:
        myReader=csv.reader(myCSV,delimiter=',',quotechar='|')#,quoting=csv.QUOTE_NONNUMERIC)
        #check number of rows
        row_count = sum(1 for row in myReader)-1
        if thisRow > row_count:
            myCSV.close
            return ('Error: row > {}'.format(row_count))
        #retrieve this row
        i=0
        myCSV.seek(0)
        for rowFind in myReader:
            #print(rowFind)
            row_retrieve=rowFind
            i+=1
            if i>thisRow:
                break
        #check number of columns in specified row
        #print(row_retrieve)
        col_count=len(row_retrieve)-1
        if thatCol > col_count:
            myCSV.close
            return ('Error: column > {}'.format(col_count))
        readVal=row_retrieve[thatCol]
        myCSV.close
        return readVal
        
#obtain full contents
def csvReadAll(fullPath):
    try:
        myCSV=open(fullPath,'r')
    except Exception as e:
        print('Something went wrong reading from '+fullPath)
        print(e)
        return 0
    else:
        myReader=csv.reader(myCSV,delimiter=',',quotechar='|')#,quoting=csv.QUOTE_NONNUMERIC)
        fileBlast=[]
        for row in myReader:
            fileBlast.append(row)
        myCSV.close
        return fileBlast
        
#delete contents
def csvClear(fullPath):
    csvWrite(fullPath,[])
    print(fullPath+' cleared')
    return


#test values
#numArr=[(1,2,3),(4,5,6),(7,8,9),(10,11,12)]
#locArr=[1,2]
#fPath='/home/an/Documents/PlantShelf/databases/plantLegend.csv'
#print(csvCreate(fPath))
#print(csvWrite(fPath, numArr))
#print(csvRead(fPath,locArr[0],locArr[1]))
#print(csvReadAll(fPath))
#print(csvRead(fPath,1,1))
#csvClear(fPath)

