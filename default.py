#v0.0.1
#!/bin/python

day_temp=19.999
night_temp=23.999
daytime=['00:00' '17:00']

detectIP=['192.168.0.25', '192.168.0.26']

onCommand="ssh osmc@192.168.0.130 'sudo gpio write 8 0'"
offCommand="ssh osmc@192.168.0.130 'sudo gpio write 8 1'"

import os, sys, subprocess, socket, __builtin__, sqlite3
import math, glob
import datetime, time
from flask import Flask, render_template, request, redirect
import wiringpi as wiringpi
import RPi.GPIO as GPIO

workingdir='/media/Backup/GitHub/'
lib_path = os.path.abspath(os.path.join(workingdir, 'lib'))
sys.path.append(lib_path)

templog='resources/database/templog_'
datalog='resources/database/datalog.db'
status='resources/variables/status'
manual='resources/variables/manual'
wintermode='resources/variables/winter'
advance='resources/variables/advance'

wiringpi.wiringPiSetup()
wiringpi.pinMode(0, 1)
wiringpi.pinMode(2, 1)
GPIO.setmode(GPIO.BCM)
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP)

hostname=socket.gethostname()
now = datetime.datetime.now()
__builtin__.callback = ''
__builtin__.chon=''
ch_status=''
time_now=''
date=''

