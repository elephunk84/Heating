#v0.0.1
#!/bin/python3
import os, os.path, sys, subprocess, socket, sqlite3, threading, re
import math, glob
import datetime, time
import RPi.GPIO as GPIO
from netdisco.discovery import NetworkDiscovery
from app import app

workingdir='/media/Backup/GitRepo/Heating'
scheduleDB=workingdir+'/app/database/schedule.db'
lib_path = os.path.abspath(os.path.join(workingdir, 'lib'))
sys.path.append(lib_path)


temperatures=['19.999', '21.999']
daytime=['08:00:00', '17:00:00']

detectDevices=['192.168.0.10', '192.168.0.11', '192.168.0.25', '192.168.0.26']

dataTables=['temps', 'override', 'time']

onCommand="ssh osmc@192.168.0.130 'sudo gpio write 8 0'"
offCommand="ssh osmc@192.168.0.130 'sudo gpio write 8 1'"

manualOverride='OFF'
advancedOverride='OFF'
occupiedIain='NO'
occupiedElora='NO'
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

def dateTime():
    global dateTimeLIST, yesterday, now
    now=datetime.datetime.now()
    dateTimeLIST=[]
    yesterday=datetime.datetime.now() - datetime.timedelta(days=1)
    yesterday=yesterday.strftime("%A %d/%B/%Y %H:%M")
    dateTimeLIST.append(now.strftime("%A"))
    dateTimeLIST.append(now.strftime("%d/%B/%Y"))
    dateTimeLIST.append(str(now.strftime("%H:%M:%S")))
    dateTimeLIST.append(str(now.strftime("%H:%M")))
    dateTimeLIST.append(yesterday)
    dateTimeLIST.append(now.strftime("%d"))
    dateTimeLIST.append(now.strftime("%B"))
    dateTimeLIST.append(now.strftime("%Y"))
    
    
    
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
    temp=temp-4
    
def checkforDB():
    global todaysDB
    todaysDB=(workingdir+"/app/database/templogs/"+dateTimeLIST[7]+"/"+dateTimeLIST[6]+"/"+dateTimeLIST[5]+".db")
    DBdir=os.path.dirname(todaysDB)
    if os.path.isfile(todaysDB) and os.access(todaysDB, os.R_OK):
        pass
    else:
        print("Creating "+todaysDB)
        try:
            os.stat(workingdir+"/app/database/templogs/"+dateTimeLIST[7])
        except:
            os.mkdir(workingdir+"/app/database/templogs/"+dateTimeLIST[7])
        try:
            os.stat(workingdir+"/app/database/templogs/"+dateTimeLIST[7]+"/"+dateTimeLIST[6])
        except:
            os.mkdir(workingdir+"/app/database/templogs/"+dateTimeLIST[7]+"/"+dateTimeLIST[6])
        subprocess.call(['touch', todaysDB])
        with sqlite3.connect(todaysDB) as tempconn:
            curs=tempconn.cursor()
            tempTableCheck='create table if not exists ' + dataTables[0] + '(timestamp DATETIME, temp NUMERIC, occupiedIain text, occupiedElora text, manualOverride text, advancedOverride DATETIME, STATUS text, setTemp NUMERIC,schedule TEXT);'
            curs.execute(tempTableCheck)
            curs.execute("INSERT INTO " + dataTables[0] + " values (?, ?, ?, ?, ?, ?, ?, ?, ?);",  (dateTimeLIST[2], temp, occupiedIain, occupiedElora, manualOverride, advancedOverride, STATUS, setTemp, schedule) )
            overrideTableCheck='create table if not exists ' + dataTables[1] + '(timestamp DATETIME, temp NUMERIC, manualOverride text, advancedOverride NUMERIC);'
            curs.execute(overrideTableCheck)
            curs.execute("INSERT INTO " + dataTables[1] + " values (?, ?, ?, ?);", (dateTimeLIST[4], temp, manualOverride, advancedOverride))
            overrideTableCheck='create table if not exists ' + dataTables[2] + '(day DATETIME, date DATETIME, timeBIG DATETIME, timeSMALL DATETIME, yesterday DATETIME);'
            curs.execute(overrideTableCheck)
            curs.execute("INSERT INTO " + dataTables[2] + " values (?, ?, ?, ?, ?);", (dateTimeLIST[0], dateTimeLIST[1], dateTimeLIST[2], dateTimeLIST[3], dateTimeLIST[4]))
            tempconn.commit()
    
def findDevices():
    global occupiedIain
    global occupiedElora
    occupiedIain="NO"
    occupiedElora="NO"
    for ip in detectDevices:
        response = os.system("ping -c 1 " + ip + " > /dev/null")
        if response == 0:
            if ip is detectDevices[0] or detectDevices[1]:
                occupiedIain="YES"
            if ip == detectDevices[2]:
                occupiedElora="YES"
        
def manOverride():
    global manualOverride, advancedOverride, advTime
    with sqlite3.connect(todaysDB) as stateconn:
        curs=stateconn.cursor()
        curs.execute("SELECT * FROM " + dataTables[1] + " ORDER BY ROWID DESC LIMIT 1")
        lastRow=curs.fetchone()
    timeSmall=str(now.strftime("%H:%M"))
    advTime=lastRow[3]
    try:
        time.strptime(advTime, "%H:%M")
        if (str(advTime) == timeSmall):
            advancedOverride='OFF'
            manualOverride='OFF'
            with sqlite3.connect(todaysDB) as stateconn:
                curs=stateconn.cursor()
                curs.execute("INSERT INTO " + dataTables[1] + " values (?, ?, ?, ?);", (dateTimeLIST[4], temp, manualOverride, advancedOverride))
                tempconn.commit()
        else:
            advancedOverride=row3
            manualOverride='ON'
            with sqlite3.connect(todaysDB) as stateconn:
                curs=stateconn.cursor()
                curs.execute("INSERT INTO " + dataTables[1] + " values (?, ?, ?, ?);", (dateTimeLIST[4], temp, manualOverride, advancedOverride))
                tempconn.commit()
    except:
        if lastRow[2] == 'OFF' or None or '':
                manualOverride='OFF'
        if lastRow[2] == 'ON':
            manualOverride='ON'
        if lastRow[3] == 'OFF' or None or '':
            advancedOverride='OFF'
    return manualOverride, advancedOverride

def checkSchedule():
    global setTemp, chSTATUS, schedule
    global manualOverride, advancedOverride
    today=now.strftime("%A")
    chSTATUS='OFF'
    schedule='OFF'
    if ((dateTimeLIST[3] > daytime[0]) and (dateTimeLIST[3] < daytime[1])):
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
            if ( timeNow == progON ) and ( manualOverride == 'ON' ):
                manualOverride='OFF'
                advancedOverride='OFF'
                with sqlite3.connect(todaysDB) as stateconn:
                    curs=stateconn.cursor()
                    curs.execute("INSERT INTO override values (?, ?, ?, ?);", (dateTimeLIST[4], temp, manualOverride, advancedOverride))
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
    try:
        time.strptime(advTime, '%H:%M')
        advancedOverride=advTime
    except ValueError:
        advancedOverride='OFF'
    with sqlite3.connect(todaysDB) as tempconn:
        curs=tempconn.cursor()
        curs.execute("INSERT INTO " + dataTables[0] + " values (?, ?, ?, ?, ?, ?, ?, ?, ?);",  (dateTimeLIST[2], temp, occupiedIain, occupiedElora, manualOverride, advancedOverride, STATUS, setTemp, schedule) )
        curs.execute("INSERT INTO " + dataTables[2] + " values (?, ?, ?, ?, ?);", (dateTimeLIST[0], dateTimeLIST[1], dateTimeLIST[2], dateTimeLIST[3], dateTimeLIST[4]))
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
