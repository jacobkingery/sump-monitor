# adapted from https://github.com/adafruit/Adafruit_Learning_System_Guides/tree/master/Raspberry_Pi_DS18B20_Temperature_Sensing

sensor_fn = '/sys/bus/w1/devices/{}/w1_slave'
sensor_ids = [
    '28-01144878b1aa',
    '28-011447ed91aa',
    '28-011447e3f7aa',
    '28-0114485821aa',
    '28-011448155aaa',
]

def read_temps_raw():
    readings = []
    for id in sensor_ids:
        try:
            with open(sensor_fn.format(id), 'r') as f:
                readings.append(f.readlines())
        except:
            readings.append([])
    return readings

def read_temps():
    temps = []
    readings = read_temps_raw()
    for reading in readings:
        try:
            assert reading[0].strip()[-3:] == 'YES'
            t_pos = reading[1].find('t=')
            assert t_pos != -1
            temp_string = reading[1][t_pos+2:]
            temp = float(temp_string) / 1000.0 * 9 / 5 + 32
            temps.append(round(temp, 1))
        except:
            temps.append(-1)
    return temps

if __name__ == '__main__':
    import time
    while 1:
        print read_temps()
        time.sleep(1)
