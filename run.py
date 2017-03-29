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


temperatures=['17.999', '20.999', '21.999']
daytime=['08:00:00', '17:00:00', '20:00:00', '23:59:59']
summerMONTHS=['June', 'July', 'August', 'September']
detectDevices=['192.168.0.10', '192.168.0.25', '192.168.0.26']

dataTables=['temps', 'override', 'time']

onCommand="ssh osmc@192.168.0.130 'sudo gpio write 8 0'"
offCommand="ssh osmc@192.168.0.130 'sudo gpio write 8 1'"

STATUS='OFF'
chSTATUS='OFF'
summerOverride='OFF'
manualOverride='OFF'
advancedOverride='OFF'
manSumOverride='OFF'
occupiedIain='NO'
occupiedElora='NO'
setTemp='17.999'
schedule='OFF'

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
            overrideTableCheck='create table if not exists ' + dataTables[1] + '(timestamp DATETIME, temp NUMERIC, manualOverride text, advancedOverride text, summerOverride text, manSumOverride text);'
            curs.execute(overrideTableCheck)
            curs.execute("INSERT INTO " + dataTables[1] + " values (?, ?, ?, ?, ?, ?);", (dateTimeLIST[2], temp, manualOverride, advancedOverride, summerOverride, manSumOverride))
            tempTableCheck='create table if not exists ' + dataTables[2] + '(day DATETIME, date DATETIME, timeBIG DATETIME, timeSMALL DATETIME, yesterday DATETIME);'
            curs.execute(tempTableCheck)
            curs.execute("INSERT INTO " + dataTables[2] + " values (?, ?, ?, ?, ?);", (dateTimeLIST[0], dateTimeLIST[1], dateTimeLIST[2], dateTimeLIST[3], dateTimeLIST[4]))
            tempconn.commit()
    
def findDevices():
    global occupiedIain
    global occupiedElora
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
        curs.close()
    advTime=lastRow[3]
    try:
        time.strptime(advTime, "%H:%M")
        if (str(advTime) == dateTimeLIST[3]):
            advancedOverride='OFF'
            manualOverride='OFF'
            with sqlite3.connect(todaysDB) as stateconn:
                curs=stateconn.cursor()
                curs.execute("INSERT INTO " + dataTables[1] + " values (?, ?, ?, ?);", (dateTimeLIST[4], temp, manualOverride, advancedOverride))
                stateconn.commit()
        else:
            advancedOverride=lastRow[3]
            manualOverride='ON'
    except:
        if lastRow[2] == 'OFF' or None or '':
                manualOverride='OFF'
        if lastRow[2] == 'ON':
            manualOverride='ON'
        if lastRow[3] == 'OFF' or None or '':
            advancedOverride='OFF'
    return manualOverride, advancedOverride

def checkSchedule():
    global dateTimeLIST, summerMONTHS, setTemp, chSTATUS, schedule, manualOverride, advancedOverride, summerOverride, manSumOverride
    if dateTimeLIST[6] in summerMONTHS:
        if manSumOverride == 'OFF':
            summerOverride='ON'
        elif manSumOverride == 'ON':
            summerOverride='OFF'
    if summerOverride == 'ON':
        chSTATUS='OFF'
        return chSTATUS
    if ((dateTimeLIST[3] > daytime[0]) and (dateTimeLIST[3] < daytime[1])):
        setTemp=temperatures[0]
    elif ((dateTimeLIST[3] > daytime[1]) and (dateTimeLIST[3] < daytime[2])):
        setTemp=temperatures[1]
    elif ((dateTimeLIST[3] > daytime[2]) and (dateTimeLIST[3] < daytime[3])):
        setTemp=temperatures[2]
    with sqlite3.connect(scheduleDB) as schedconn:
        curs=schedconn.cursor()
        query=curs.execute("SELECT * FROM " + dateTimeLIST[0] + " ORDER BY ROWID ASC LIMIT 10;")
        colname = [ d[0] for d in query.description ]
        result_list = [ dict(zip(colname, r)) for r in query.fetchall() ]
        curs.close()
        for prog in result_list:
            progON=str(prog['ON'])
            progOFF=str(prog['OFF'])    
            if dateTimeLIST[3] >= progON:
                if dateTimeLIST[3] < progOFF:
                    schedule=[]
                    schedule.append(progON)
                    schedule.append(progOFF)
                    schedule=str(schedule)
                    if (occupiedIain == 'YES'):
                        if str(temp) < str(setTemp):
                            chSTATUS='ON'
                        else:
                            chSATUS='OFF'
                    if (occupiedElora == 'YES'):
                        if str(temp) < str(setTemp):
                            chSTATUS='ON'
                        else:
                            chSATUS='OFF'
                    else:
                        chSATUS='OFF'
            if dateTimeLIST[3] == str(progOFF):
                schedule=str('')
                manualOverride='OFF'
                advancedOverride='OFF'
                chSTATUS='OFF'
                with sqlite3.connect(todaysDB) as stateconn:
                    curs=stateconn.cursor()
                    curs.execute("INSERT INTO override values (?, ?, ?, ?, ?, ?);", (dateTimeLIST[4], temp, manualOverride, advancedOverride, summerOverride, manSumOverride))
                    stateconn.commit()
    setTemp=float(setTemp)
    setTemp=math.ceil(setTemp * 100) / 100.0
                    
                
def logic():
    global chSTATUS, STATUS
    if (chSTATUS == 'OFF'):
        if (manualOverride == 'ON'):
            subprocess.call(["ssh", "osmc@192.168.0.130", "sh /home/osmc/on.sh"])
            STATUS='ON'
        if (manualOverride == 'OFF'):
            subprocess.call(["ssh", "osmc@192.168.0.130", "sh /home/osmc/off.sh"])
            STATUS='OFF'
    if (chSTATUS == 'ON'): 
        if (manualOverride == 'ON'):
            subprocess.call(["ssh", "osmc@192.168.0.130", "sh /home/osmc/off.sh"])
            STATUS='OFF'
        if (manualOverride == 'OFF'):
            subprocess.call(["ssh", "osmc@192.168.0.130", "sh /home/osmc/on.sh"])
            STATUS='ON'
    
def logData():
    global setTemp
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
