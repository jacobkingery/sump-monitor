#!/usr/bin/python2

import RPi.GPIO as GPIO
import plotly.plotly as py
from plotly.graph_objs import Scatter, Data
import datetime as dt
import time, subprocess

def pinSetup(rP, wPs):
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(readPin, GPIO.IN)
    for pin in wPs:
        GPIO.setup(pin, GPIO.OUT, initial=0)

def getLevel(rP, wPs):
    for i in range(len(wPs))[::-1]:
        GPIO.output(wPs[i], 1)
        time.sleep(.01)
        connected = not GPIO.input(rP)
        GPIO.output(wPs[i], 0)
        if connected:
            return i+1
        if not i:
            return 0

def streamData(id, ts, lvl):
    data = {'x':ts, 'y':lvl}

    # Try streaming to server; ignore if it fails
    try:
        s = py.Stream(id)
        s.open()
        s.write(data)
        s.close()
    except:
        pass

def logData(bl):
    trace = Scatter(
        x = bl['x'],
        y = bl['y']
    )
    data = Data([trace])

    # Try sending data to server; clear backlog if it works
    try:
        url = py.plot(data, filename='sump-monitor-archive', fileopt='extend', auto_open=False)
        return {'x':[], 'y':[]}
    except:
        return bl

def postData(ts, lvl):
    strts = ts.strftime('%m/%d/%y %H:%M:%S')
    atmpt = 5
    while atmpt:
        try:
            subprocess.call(['curl', 'http://sump.herokuapp.com/update',
                '-d', 'timestamp={0}'.format(strts),
                '-d', 'level={0}'.format(lvl)
            ])
            return
        except:
            atmpt -= 1
            time.sleep(5)

def sendSMS(no, lvl, last):
    now = dt.datetime.now()
    delta = now - last

    # If it has been enough time since the last SMS, try to send the warning up to 5 times
    if delta.total_seconds() > 3600:
        atmpt = 5
        while atmpt:
            try:
                subprocess.call(['curl', 'http://textbelt.com/text',
                    '-d', 'number={0}'.format(no),
                    '-d', "message=Water in sump hole has reached level {0}.".format(lvl)
                ])
                return now
            except:
                atmpt -= 1
                time.sleep(10)
    return last

try:
    GPIO.setwarnings(False)
    readPin = 7
    writePins = [11, 12, 13, 15, 16, 18, 22]    # From lowest to highest (physically)
    pinSetup(readPin, writePins)

    try:
        with open('/root/sump-monitor/phonenumber.txt') as f:
            phoneNo = f.readline().strip()
    except:
        phoneNo = 0

    lastMsg = dt.datetime.min

    try:
        with open('/root/sump-monitor/streamID.txt') as f:
            streamID = f.readline().strip()
    except:
        streamID = 0

    backlog = {'x':[], 'y':[]}

    while 1:
        level = getLevel(readPin, writePins)
        timestamp = dt.datetime.now()

        if level >= 6 and phoneNo:
            lastMsg = sendSMS(phoneNo, level, lastMsg)

        # send every data point to stream
        # disabling because it wasn't working
        # if streamID:
        #     streamData(streamID, timestamp, level)

        # POST data to status site
        postData(timestamp, level)

        # send every 10 data points to archive
        backlog['x'].append(timestamp)
        backlog['y'].append(level)
        if len(backlog['x']) >= 10:
            backlog = logData(backlog)

        time.sleep(60)

except:
    GPIO.cleanup()
