#!flask/bin/python3
from flask import Flask, render_template, request, redirect
import os, os.path, sys, subprocess, socket, sqlite3, threading
import math, glob
import datetime, time
from app import app

data=[]
dbData=[]
dbData2=[]
timeData=[]
graphDataTEMP=[]
graphDataTIME=[]
indexCSS=['styles/base_style.css', 'styles/index_style.css']
mobileCSS=['styles/base_style.css', 'styles/mobile_style.css']
summerMONTHS=['June', 'July', 'August', 'September']
source='INDEX'

workingdir='/media/Backup/GitRepo/Heating'
lib_path = os.path.abspath(os.path.join(workingdir, 'lib'))
sys.path.append(lib_path)

def dateTime():
    global dateTimeLIST
    now=datetime.datetime.now()
    dateTimeLIST=[]
    dateTimeLIST.append(now.strftime("%A"))
    dateTimeLIST.append(now.strftime("%d"))
    dateTimeLIST.append(now.strftime("%B"))
    dateTimeLIST.append(now.strftime("%Y"))
    dateTimeLIST.append(str(now.strftime("%H:%M:%S")))
    dateTimeLIST.append(now.strftime("%a"))
    
def getData():
    global dbData, dbData2, timeData, graphDataTEMP, graphDataTIME, scheduleRUN, summerTEXT
    dateTime()
    db=(workingdir+"/app/database/templogs/"+dateTimeLIST[3]+"/"+dateTimeLIST[2]+"/"+dateTimeLIST[1]+".db")
    with sqlite3.connect(db) as tempconn:
        curs=tempconn.cursor()
        curs.execute('SELECT * FROM temps ORDER BY ROWID DESC LIMIT 1')
        dbData=curs.fetchone()
        curs.execute('SELECT * FROM override ORDER BY ROWID DESC LIMIT 1')
        dbData2=curs.fetchone()
        curs.execute('SELECT * FROM time ORDER BY ROWID DESC LIMIT 1')
        timeData=curs.fetchone()
        curs.execute('SELECT temp, timestamp FROM temps ORDER BY ROWID ASC LIMIT 10000')
        graphData=curs.fetchall()
        graphData=graphData[::250]
        graphDataTEMP= ( x[0] for x in graphData)
        graphDataTIME= ( x[1] for x in graphData)
    scheduleRUN=dbData[8]
    schedON=scheduleRUN[2:7]
    schedOFF=scheduleRUN[11:16]
    if (scheduleRUN == '') or (scheduleRUN == 'OFF'):
        scheduleRUN='OFF'
    else:
        scheduleRUN=(schedON+' till '+schedOFF)
    if (dbData2[5] == 'ON') and (dbData2[4] == 'OFF'):
        summerTEXT="Manual Summer Mode"
    elif (dbData2[5] == 'ON') and (dbData2[4] == 'ON'):
        summerTEXT="Manual Winter Mode"
    elif (dbData2[4] == 'ON') and (dateTimeLIST[2] in summerMONTHS):
        summerTEXT="Summer Mode Active"
    else:
        summerTEXT=''
        
def manualoverride():
    dateTime()
    db=(workingdir+"/app/database/templogs/"+dateTimeLIST[3]+"/"+dateTimeLIST[2]+"/"+dateTimeLIST[1]+".db")
    with sqlite3.connect(db) as stateconn:
        curs=stateconn.cursor()
        curs.execute('SELECT * FROM override ORDER BY ROWID DESC LIMIT 1')
        lastRow=curs.fetchone()
        if lastRow[2] == 'ON':
            with sqlite3.connect(db) as stateconn:
                curs=stateconn.cursor()
                curs.execute("INSERT INTO override values (?, ?, ?, ?, ?, ?);", (dateTimeLIST[4], '', 'OFF', 'OFF', lastRow[4], lastRow[5]))
                stateconn.commit()
        else:
            with sqlite3.connect(db) as stateconn:
                curs=stateconn.cursor()
                curs.execute("INSERT INTO override values (?, ?, ?, ?, ?, ?);", (dateTimeLIST[4], '', 'ON', 'OFF', lastRow[4], lastRow[5]))
                stateconn.commit()
    
def advancedoverride():
    dateTime()
    db=(workingdir+"/app/database/templogs/"+dateTimeLIST[3]+"/"+dateTimeLIST[2]+"/"+dateTimeLIST[1]+".db")
    with sqlite3.connect(db) as stateconn:
        curs=stateconn.cursor()
        curs.execute('SELECT * FROM override ORDER BY ROWID DESC LIMIT 1')
        lastRow=curs.fetchone()
    advancedOverride=lastRow[3]
    if advancedOverride == 'OFF':
        hourPlus1=datetime.datetime.now() + datetime.timedelta(hours=1)
        advancedOverride=str(hourPlus1.strftime("%H:%M"))
        with sqlite3.connect(db) as stateconn:
                curs=stateconn.cursor()
                curs.execute("INSERT INTO override values (?, ?, ?, ?, ?, ?);", (dateTimeLIST[4], '', 'ON', advancedOverride, lastRow[4], lastRow[5]))
                stateconn.commit()
    else:
        with sqlite3.connect(db) as stateconn:
                curs=stateconn.cursor()
                curs.execute("INSERT INTO override values (?, ?, ?, ?, ?, ?);", (dateTimeLIST[4], '', 'OFF', 'OFF', lastRow[4], lastRow[5]))
                stateconn.commit()

def summermode():
    dateTime()
    db=(workingdir+"/app/database/templogs/"+dateTimeLIST[3]+"/"+dateTimeLIST[2]+"/"+dateTimeLIST[1]+".db")
    with sqlite3.connect(db) as tempconn:
        curs=tempconn.cursor()
        curs.execute('SELECT * FROM override ORDER BY ROWID DESC LIMIT 1')
        lastRow=curs.fetchone()
        if (lastRow[4] == 'ON') and (lastRow[5] == 'OFF'):
            summerOverride='OFF'
            manSumOverride='ON'
        elif (lastRow[4] == 'OFF') and (lastRow[5] == 'OFF'):
            summerOverride='OFF'
            manSumOverride='ON'
        elif (lastRow[4] == 'OFF') and (lastRow[5] == 'ON'):
            summerOverride='ON'
            manSumOverride='ON'
        else:
            summerOverride='OFF'
            manSumOverride='OFF'    
        curs.execute("INSERT INTO override values (?, ?, ?, ?, ?, ?);", (dateTimeLIST[4], lastRow[1], lastRow[2], lastRow[3], summerOverride, manSumOverride))
        tempconn.commit()
    
@app.route('/')
@app.route('/index')
def home():
    global source
    getData()
    source="INDEX"
    return render_template("index.html", source=source, styles=indexCSS, data=dateTimeLIST, dbData=dbData, dbData2=dbData2, summerTEXT=summerTEXT, timeData=timeData, graphDataTEMP=graphDataTEMP, graphDataTIME=graphDataTIME, scheduleRUN=scheduleRUN)

@app.route('/mobile')
def mobile():
    global source
    getData()
    source="MOBILE"
    return render_template("mobile.html", source=source, styles=mobileCSS, data=dateTimeLIST, dbData=dbData, dbData2=dbData2, summerTEXT=summerTEXT, timeData=timeData, graphDataTEMP=graphDataTEMP, graphDataTIME=graphDataTIME, scheduleRUN=scheduleRUN)

@app.route('/manual')
def manual():
    global source
    manualoverride()
    return redirect("/")

@app.route('/advance')
def advance():
    global source
    advancedoverride()
    return redirect("/")

@app.route('/winter')
def winter():
    global source
    wintermode()
    return redirect("/")

@app.route('/mobmanual')
def mobmanual():
    global source
    manualoverride()
    return redirect("/mobile")

@app.route('/mobadvance')
def mobadvance():
    advancedoverride()
    return redirect("/mobile")

@app.route('/mobsummer')
def mobsummer():
    summermode()
    return redirect("/mobile")
    
