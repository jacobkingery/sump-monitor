#!/usr/bin/python2

import RPi.GPIO as GPIO
import plotly.plotly as py
from plotly.graph_objs import Scatter, Data
import datetime as dt
import time, subprocess, traceback

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

try:
    readPin = 7
    writePins = [11, 12, 13, 15, 16, 18, 22]    # From lowest to highest (physically)
    pinSetup(readPin, writePins)

    with open('phonenumber.txt') as f:
        phoneNo = f.readline().strip()

    backlog = {'x':[], 'y':[]}

    while 1:
        level = getLevel(readPin, writePins)
        timestamp = dt.datetime.now()

        # send every data point to stream

        # send every <x> data points to archive
        backlog['x'].append(timestamp)
        backlog['y'].append(level)
    
        if len(backlog['x']) > 5:
            backlog = logData(backlog)

        time.sleep(60)

except:
    GPIO.cleanup()
    traceback.print_exc()
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
            
