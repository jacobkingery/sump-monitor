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
        url = py.plot(data, filename='test plot', fileopt='extend', auto_open=False)
        return {'x':[], 'y':[]}
    except:
        print len(bl['x'])
        return bl

def sendSMS(no, lvl, last):
    now = dt.datetime.now()
    delta = now - last

    # If it has been enough time since the last SMS, try to send the warning up to 5 times
    if delta.total_seconds() > 7200:
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
    readPin = 7
    writePins = [11, 12, 13, 15, 16, 18, 22]    # From lowest to highest (physically)
    pinSetup(readPin, writePins)

    try:
        with open('phonenumber.txt') as f:
            phoneNo = f.readline().strip()
    except:
        phoneNo = 0

    lastMsg = dt.datetime.min

    try:
        with open('streamID.txt') as f:
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
        if streamID:
            streamData(streamID, timestamp, level)

        # send every <x> data points to archive
        backlog['x'].append(timestamp)
        backlog['y'].append(level)
    
        if len(backlog['x']) > 5:
            backlog = logData(backlog)

        time.sleep(5)

except:
    GPIO.cleanup()
    sent = 0
    while not sent:
        try:
            print 'Attempting to send text message...'
            subprocess.call(['curl', 'http://textbelt.com/text', 
                '-d', 'number={0}'.format(phoneNo), 
                '-d', "message=An error occurred"
            ]) 
            sent = 1   
        except:
            time.sleep(30)
            
