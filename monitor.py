#!/usr/bin/python2

import RPi.GPIO as GPIO
import plotly.plotly as py
from plotly.graph_objs import Scatter, Data
import datetime as dt
import time
import smtplib
import json
import requests

import temp

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

def getTemps(ts):
    readings = temp.read_temps()
    zone = 1
    temps = []
    for reading in readings:
        temps.append({
            'timestamp': ts,
            'zone': zone,
            'temp': reading,
        })
        zone += 1
    return temps

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
    headers = {'Content-Type': 'application/json'}
    attempt = 5
    while attempt:
        try:
            response = requests.post(url, data=payload, headers=headers)
            assert response.status_code == 200
            assert response.json().get('success', False) is True
            return {'sump': [], 'temp': []}
        except:
            attempt -= 1
            time.sleep(5 - attempt)
    return batch

def sendSMS(fromGmail, fromGmailPassword, toAddr, level, lastTime):
    now = dt.datetime.now()
    delta = now - lastTime

    # Don't send more than one SMS per hour
    if delta.total_seconds() < 3600:
        return lastTime

    message = 'Water in sump hole has reached level {}.'.format(level)
    attempt = 5
    while attempt:
        try:
            emailServer = smtplib.SMTP('smtp.gmail.com', 587)
            emailServer.starttls()
            emailServer.login(fromGmail, fromGmailPassword)
            emailServer.sendmail(fromGmail, toAddr, message)
            emailServer.quit()
            return now
        except:
            attempt -= 1
            time.sleep(5 - attempt)
    return lastTime

try:
    GPIO.setwarnings(False)
    readPin = 10
    writePins = [11, 12, 13, 15, 16, 18, 22]    # From lowest to highest (physically)
    pinSetup(readPin, writePins)

    # Last message was as long ago as possible
    lastMsg = dt.datetime.min

    with open('/root/sump-monitor/config.json') as f:
        config = json.load(f)

    fromGmail = config.get('fromGmail', None)
    fromGmailPassword = config.get('fromGmailPassword', None)
    toAddr = config.get('toAddr', None)
    canSMS = fromGmail and fromGmailPassword and toAddr

    postURL = config.get('postURL', None)

    lastTempHour = -1

    backlog = {'x':[], 'y':[]}
    batch = {'sump': [], 'temp': []}

    while 1:
        timestamp = dt.datetime.now()
        ts_str = timestamp.strftime('%m/%d/%y %H:%M:%S')
        level = getLevel(readPin, writePins)

        # read temps only once an hour
        temps = []
        if timestamp.hour != lastTempHour:
            temps = getTemps(ts_str)
            lastTempHour = timestamp.hour

        # Send warning text message
        if canSMS and level >= 6:
            lastMsg = sendSMS(fromGmail, fromGmailPassword, toAddr, level, lastMsg)

        # POST data to status site every 3 data points
        if postURL:
            batch['sump'].append({
                'timestamp': ts_str,
                'level': level,
            })
            batch['temp'].extend(temps)

            if len(batch['sump']) >= 3:
                batch = postData(postURL, batch)

            # If batch grows too big, drop some
            if len(batch['sump']) > 30:
                batch['sump'] = batch['sump'][-30:]
            if len(batch['temp']) > 10:
                batch['temp'] = batch['temp'][-10:]

        # Send every 10 data points to archive
        backlog['x'].append(timestamp)
        backlog['y'].append(level)
        if len(backlog['x']) >= 10:
            backlog = logData(backlog)
        # If backlog grows too big, drop some
        if len(backlog['x']) > 100:
            backlog['x'] = backlog['x'][-100:]
            backlog['y'] = backlog['y'][-100:]

        time.sleep(60)

except:
    GPIO.cleanup()
