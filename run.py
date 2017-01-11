#v0.0.1
#!/bin/python3
import os, os.path, sys, subprocess, socket, sqlite3, threading, re
import math, glob
import datetime, time
import RPi.GPIO as GPIO
from netdisco.discovery import NetworkDiscovery
from app import app

workingdir='/media/Backup/GitRepo/Heating'
lib_path = os.path.abspath(os.path.join(workingdir, 'lib'))
sys.path.append(lib_path)


temperatures=['17.999', '23.999']
daytime=['00:00', '17:00']

detectDevices=['192.168.0.25', '192.168.0.26']

onCommand="ssh osmc@192.168.0.130 'sudo gpio write 8 0'"
offCommand="ssh osmc@192.168.0.130 'sudo gpio write 8 1'"

scheduleDB=workingdir+'/app/database/schedule.db'
manualOverride='OFF'
advancedOverride='OFF'
occupiedIain=''
occupiedElora=''
STATUS=''
setTemp=''
schedule=''

GPIO.setmode(GPIO.BCM)
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def flaskFRONT():
    app.run('0.0.0.0', 80)

thread = threading.Thread(name='flaskFRONT', target=flaskFRONT)
thread.setDaemon(True)
thread.start()

#app.run('0.0.0.0', 80, debug=True)

def dateTime():
    global dateTimeLIST, yesterday, now
    now=datetime.datetime.now()
    yesterday=datetime.datetime.now() - datetime.timedelta(days=1)
    dateTimeLIST=[]
    dateTimeLIST.append(now.strftime("%a"))
    dateTimeLIST.append(now.strftime("%d"))
    dateTimeLIST.append(now.strftime("%B"))
    dateTimeLIST.append(now.strftime("%Y"))
    dateTimeLIST.append(str(now.strftime("%H:%M:%S")))
            
def getTemp():
    global temp
    devicelist = glob.glob('/sys/bus/w1/devices/28-*')
    w1devicefile = devicelist[0] + '/w1_slave'
    fileobj = open(w1devicefile,'r')
    lines = fileobj.readlines()
    fileobj.close()
    tempstr= lines[1][-6:-1]
    tempvalue=float(tempstr)/1000
    temp=tempvalue
    temp=float(temp)
    temp=math.ceil(temp * 100) / 100.0
    
def checkforDB():
    global todaysDB, todaysStateDB
    todaysDB=(workingdir+"/app/database/templogs/"+dateTimeLIST[3]+"/"+dateTimeLIST[2]+"/"+dateTimeLIST[1]+".db")
    todaysStateDB=(workingdir+"/app/database/templogs/"+dateTimeLIST[3]+"/"+dateTimeLIST[2]+"/"+dateTimeLIST[1]+"_manualOverride.db")
    DBdir=os.path.dirname(todaysDB)
    if os.path.isfile(todaysDB) and os.access(todaysDB, os.R_OK):
        pass
    else:
        print("Creating "+todaysDB)
        try:
            os.stat(workingdir+"/app/database/templogs/"+dateTimeLIST[3])
        except:
            os.mkdir(workingdir+"/app/database/templogs/"+dateTimeLIST[3])
        try:
            os.stat(workingdir+"/app/database/templogs/"+dateTimeLIST[3]+"/"+dateTimeLIST[2])
        except:
            os.mkdir(workingdir+"/app/database/templogs/"+dateTimeLIST[3]+"/"+dateTimeLIST[2])
        subprocess.call(['touch', todaysDB])
        subprocess.call(['touch', todaysStateDB])
        with sqlite3.connect(todaysDB) as tempconn:
            curs=tempconn.cursor()
            tempTable='temps'
            tempTableCheck='create table if not exists ' + tempTable + '(timestamp DATETIME, temp NUMERIC, occupiedIain text, occupiedElora text, manualOverride text, advancedOverride DATETIME, STATUS text, setTemp NUMERIC,schedule TEXT);'
            curs.execute(tempTableCheck)
            curs.execute("INSERT INTO temps values (?, ?, ?, ?, ?, ?, ?, ?, ?);",  (dateTimeLIST[4], temp, occupiedIain, occupiedElora, manualOverride, advancedOverride, STATUS, setTemp, schedule) )
            tempconn.commit()
        with sqlite3.connect(todaysStateDB) as stateconn:
            curs=stateconn.cursor()
            overrideTable='manualOverride'
            overrideTableCheck='create table if not exists ' + overrideTable + '(timestamp DATETIME, temp NUMERIC, manualOverride text, advancedOverride NUMERIC);'
            curs.execute(overrideTableCheck)
            curs.execute("INSERT INTO manualOverride values (?, ?, ?, ?);", (dateTimeLIST[4], temp, manualOverride, advancedOverride))
            tempconn.commit()
    
def findDevices():
    global occupiedIain
    global occupiedElora
    occupiedIain="NO"
    occupiedElora="NO"
    for ip in detectDevices:
        response = os.system("ping -c 1 " + ip + " > /dev/null")
        if response == 0:
            if ip == detectDevices[0]:
                occupiedIain="YES"
            if ip == detectDevices[1]:
                occupiedElora="YES"
        
def manOverride():
    global manualOverride, advancedOverride
    with sqlite3.connect(todaysStateDB) as stateconn:
        curs=stateconn.cursor()
        curs.execute('SELECT * FROM manualOverride ORDER BY ROWID DESC LIMIT 1')
        lastRow=curs.fetchone()
    timeSmall=str(now.strftime("%H:%M"))
    row3=lastRow[3]
    try:
        time.strptime(row3, "%H:%M")
        if row3 == timeSmall or row3 < timeSmall:
            advancedOverride='OFF'
            manualOverride='OFF'
            with sqlite3.connect(todaysDB) as stateconn:
                curs=stateconn.cursor()
                curs.execute("INSERT INTO manualOverride values (?, ?, ?, ?);", (dateTimeLIST[4], temp, manualOverride, advancedOverride))
                tempconn.commit()
        else:
            advancedOverride=row3
            manualOverride='ON'
            with sqlite3.connect(todaysDB) as stateconn:
                curs=stateconn.cursor()
                curs.execute("INSERT INTO manualOverride values (?, ?, ?, ?);", (dateTimeLIST[4], temp, manualOverride, advancedOverride))
                tempconn.commit()
    except:
        if lastRow[2] == 'OFF' or None or '':
                manualOverride='OFF'
        if lastRow[2] == 'ON':
            manualOverride='ON'
        if lastRow[3] == 'OFF' or None or '':
            advancedOverride='OFF'

def checkSchedule():
    today=now.strftime("%A")
    global setTemp, chSTATUS, schedule
    chSTATUS='OFF'
    schedule='OFF'
    dayStart=str(daytime[0])
    dayEnd=str(daytime[1])
    if (str(now) < str(daytime[1])):
        setTemp=temperatures[0]
    else:
        setTemp=temperatures[1]
    with sqlite3.connect(scheduleDB) as schedconn:
        curs=schedconn.cursor()
        query=curs.execute("SELECT * FROM " + today + " ORDER BY ROWID ASC LIMIT 10;")
        colname = [ d[0] for d in query.description ]
        result_list = [ dict(zip(colname, r)) for r in query.fetchall() ]
        curs.close()
        timeNow=str(now.strftime("%H:%M"))
        for prog in result_list:
            progON=prog['ON']
            progOFF=prog['OFF']
            if ( timeNow == progON ) and (manualOverride == 'ON'):
                manualOverride='OFF'
                advancedOverride=''
                with sqlite3.connect(todaysDB) as stateconn:
                    curs=stateconn.cursor()
                    curs.execute("INSERT INTO manualOverride values (?, ?, ?, ?);", (dateTimeLIST[4], temp, manualOverride, advancedOverride))
                    tempconn.commit()
            if (timeNow >= str(progON)) and (timeNow < str(progOFF)):
                schedule=[]
                schedule.append(progON)
                schedule.append(progOFF)
                schedule=str(schedule)
                if (occupiedIain == 'YES') or (occupiedElora == 'YES'):
                    if (str(temp) < str(setTemp)):
                        chSTATUS='ON'
                    else:
                        chSATUS='OFF'
                else:
                    chSATUS='OFF'
            else:
                chSATUS='OFF'
    setTemp=float(setTemp)
    setTemp=math.ceil(setTemp * 100) / 100.0
    
def logic():
    global STATUS
    if (chSTATUS == 'OFF') and (manualOverride == 'ON'):
        subprocess.call(["ssh", "osmc@192.168.0.130", "sh /home/osmc/on.sh"])
        STATUS='ON'
    if (chSTATUS == 'ON') and (manualOverride == 'ON'):
        subprocess.call(["ssh", "osmc@192.168.0.130", "sh /home/osmc/off.sh"])
        STATUS='OFF'
    if (chSTATUS == 'ON') and (manualOverride == 'OFF'):
        subprocess.call(["ssh", "osmc@192.168.0.130", "sh /home/osmc/on.sh"])
        STATUS='ON'
    if (chSTATUS == 'OFF') and (manualOverride == 'OFF'):
        subprocess.call(["ssh", "osmc@192.168.0.130", "sh /home/osmc/off.sh"])
        STATUS='OFF'
    
def logData():
    with sqlite3.connect(todaysDB) as tempconn:
        curs=tempconn.cursor()
        curs.execute("INSERT INTO temps values (?, ?, ?, ?, ?, ?, ?, ?, ?);",  (dateTimeLIST[4], temp, occupiedIain, occupiedElora, manualOverride, advancedOverride, STATUS, setTemp, schedule) )
        tempconn.commit()


if __name__ == "__main__":
    while True:
        dateTime()
        getTemp()
        checkforDB()
        findDevices()
        manOverride()
        checkSchedule()
        logic()
        logData()
