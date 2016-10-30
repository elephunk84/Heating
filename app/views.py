#!flask/bin/python3
from flask import Flask, render_template, request, redirect
import os, os.path, sys, subprocess, socket, sqlite3, threading
import math, glob
import datetime, time
from app import app

def dateTime():
    global dateTimeLIST, dbData
    now=datetime.datetime.now()
    dateTimeLIST=[]
    dateTimeLIST.append(now.strftime("%a"))
    dateTimeLIST.append(now.strftime("%d"))
    dateTimeLIST.append(now.strftime("%B"))
    dateTimeLIST.append(now.strftime("%Y"))
    dateTimeLIST.append(str(now.strftime("%H:%M:%S")))

workingdir='/media/Backup/GitRepo/Heating'
lib_path = os.path.abspath(os.path.join(workingdir, 'lib'))
sys.path.append(lib_path)
        
@app.route('/')
@app.route('/index')
def home():
    dateTime()
    db=(workingdir+"/app/database/templogs/"+dateTimeLIST[3]+"/"+dateTimeLIST[2]+"/"+dateTimeLIST[1]+".db")
    with sqlite3.connect(db) as tempconn:
        curs=tempconn.cursor()
        curs.execute('SELECT * FROM temps ORDER BY ROWID DESC LIMIT 1')
    return render_template("index.html", data=dateTimeLIST, dbData=curs.fetchone())

@app.route('/manual')
def manual():
    dateTime()
    db=(workingdir+"/app/database/templogs/"+dateTimeLIST[3]+"/"+dateTimeLIST[2]+"/"+dateTimeLIST[1]+"_manualOverride.db")
    with sqlite3.connect(db) as stateconn:
        curs=stateconn.cursor()
        curs.execute('SELECT * FROM manualOverride ORDER BY ROWID DESC LIMIT 1')
        lastRow=curs.fetchone()
        if lastRow[2] == 'ON':
            with sqlite3.connect(db) as stateconn:
                curs=stateconn.cursor()
                curs.execute("INSERT INTO manualOverride values (?, ?, ?, ?);", (dateTimeLIST[4], '', 'OFF', 'OFF'))
                stateconn.commit()
        else:
            with sqlite3.connect(db) as stateconn:
                curs=stateconn.cursor()
                curs.execute("INSERT INTO manualOverride values (?, ?, ?, ?);", (dateTimeLIST[4], '', 'ON', ''))
                stateconn.commit()
    return redirect("/")

@app.route('/advance')
def advance():
    dateTime()
    db=(workingdir+"/app/database/templogs/"+dateTimeLIST[3]+"/"+dateTimeLIST[2]+"/"+dateTimeLIST[1]+"_manualOverride.db")
    with sqlite3.connect(db) as stateconn:
        curs=stateconn.cursor()
        curs.execute('SELECT * FROM manualOverride ORDER BY ROWID DESC LIMIT 1')
        lastRow=curs.fetchone()
    advancedOverride=lastRow[3]
    if advancedOverride == 'OFF':
        hourPlus1=datetime.datetime.now() + datetime.timedelta(hours=1)
        advancedOverride=str(hourPlus1.strftime("%H:%M"))
        with sqlite3.connect(db) as stateconn:
                curs=stateconn.cursor()
                curs.execute("INSERT INTO manualOverride values (?, ?, ?, ?);", (dateTimeLIST[4], '', 'ON', advancedOverride))
                stateconn.commit()
    else:
        with sqlite3.connect(db) as stateconn:
                curs=stateconn.cursor()
                curs.execute("INSERT INTO manualOverride values (?, ?, ?, ?);", (dateTimeLIST[4], '', 'OFF', 'OFF'))
                stateconn.commit()
    return redirect("/")

@app.route('/winter')
def winter():
    db=(workingdir+"/app/database/templogs/"+dateTimeLIST[3]+"/"+dateTimeLIST[2]+"/"+dateTimeLIST[1]+".db")
    with sqlite3.connect(db) as tempconn:
        curs=tempconn.cursor()
        curs.execute('SELECT * FROM temps ORDER BY ROWID DESC LIMIT 1')
    return redirect("/")
