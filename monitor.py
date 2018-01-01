#!/usr/bin/python2

import RPi.GPIO as GPIO
import plotly.plotly as py
from plotly.graph_objs import Scatter, Data
import datetime as dt
import time
import subprocess
import json

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
    return 0

def logData(bl):
    trace = Scatter(
        x = bl['x'],
        y = bl['y'],
    )
    data = Data([trace])

    # Try sending data to server; clear backlog if it works
    try:
        url = py.plot(data, filename='sump-monitor-archive', fileopt='extend', auto_open=False)
        return {'x':[], 'y':[]}
    except:
        return bl

def postData(url, batch):
    payload = json.dumps({'readings': batch})
    attempt = 5
    while attempt:
        try:
            subprocess.call(['curl', url,
                '-H', 'Content-Type: application/json',
                '-d', payload,
            ])
            return []
        except:
            attempt -= 1
            time.sleep(5 - attempt)
    return batch

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

    # Last message was as long ago as possible
    lastMsg = dt.datetime.min

    with open('/root/sump-monitor/config.json') as f:
        config = json.load(f)

    try:
        phoneNo = config['phoneNo']
    except KeyError:
        phoneNo = None

    try:
        postURL = config['postURL']
    except KeyError:
        postURL = None

    backlog = {'x':[], 'y':[]}
    batch = []

    while 1:
        level = getLevel(readPin, writePins)
        timestamp = dt.datetime.now()

        # Send warning text message
        if level >= 6 and phoneNo:
            lastMsg = sendSMS(phoneNo, level, lastMsg)

        # POST data to status site every 3 data points
        if postURL:
            batch.append({
                'timestamp': timestamp.strftime('%m/%d/%y %H:%M:%S'),
                'level': level,
            })
            if len(batch) >= 3:
                batch = postData(postURL, batch)

        # Send every 10 data points to archive
        backlog['x'].append(timestamp)
        backlog['y'].append(level)
        if len(backlog['x']) >= 10:
            backlog = logData(backlog)

        time.sleep(60)

except:
    GPIO.cleanup()
