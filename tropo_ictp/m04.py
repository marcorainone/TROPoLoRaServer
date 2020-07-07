#!/usr/bin/python3
# ====================================================================================================
# test acquisizione mosquitto da fonti multiple
# nota:
# test soluzione:
# https://gist.github.com/sebclaeys/1232088
# SEMBRA FUNZIONI !!!!!
# nota: ricordarsi di verificare se mosquitto_sub e' in esecuzione prima di eseguire il resto.
# Infatti il programma lancia una serie di mosquitto_sub processi che possono rimanere in piedi se il programma viene interrotto con ctrl-c.
# Per il kill vedere:
# https://stackoverflow.com/questions/2940858/kill-process-by-name
#
import os
import io
import time
import calendar
import datetime
import shutil
import json
import requests
import maya
import copy
import geopy.distance

# psutil utilizzato per kill process
# pip install psutil
# https://stackoverflow.com/questions/2940858/kill-process-by-name
import psutil

# da https://gist.github.com/sebclaeys/1232088
import fcntl
import os
from subprocess import *


from os.path import basename
# https://pymotw.com/2/zipfile/
import zipfile
try:
    import zlib
    zip_compression = zipfile.ZIP_DEFLATED
except:
    zip_compression = zipfile.ZIP_STORED

zip_modes = { zipfile.ZIP_DEFLATED: 'deflated',
          zipfile.ZIP_STORED:   'stored'
          }

# pacchetti da installare
# sudo apt-get install build-essential
# sudo apt-get install python3-dev
# pip3 install maya

import config                   # configuration data

# note:
# https://stackoverflow.com/questions/2956886/python-calendar-timegm-vs-time-mktime
# time.mktime() assumes that the passed tuple is in local time, calendar.timegm() assumes it's in GMT/UTC
#

# --------------------------- epoch functions
# convert date string UTC (ex: "2019-08-01T11:50:14.881632602Z") to epoch
def strDateTimeUTCToEpoch(strDateTime):
    dt = maya.parse(strDateTime).datetime()
    ValEpoch = calendar.timegm(dt.timetuple())          # USE THIS: time is in UTC
    return(ValEpoch)

# convert local date time string (ex: "2019-08-01T11:50:14.881632602") to epoch
def strDateTimeToEpoch(strDateTime):
    dt = maya.parse(strDateTime).datetime()
    ValEpoch = time.mktime(dt.timetuple())              # time is in local time
    return(ValEpoch)

# return difference in seconds from two UTC string datetime
def deltaSecDateTime(strTm1, strTm2):
    ep1 = strDateTimeUTCToEpoch(strTm1)
    ep2 = strDateTimeUTCToEpoch(strTm2)
    return (ep2 - ep1)

# --------------------------- str time functions
def getStrDate(strDateTime):
    sTime = int(strDateTimeUTCToEpoch(strDateTime))     # utc seconds
    str_time = time.strftime('%Y%m%d', time.gmtime(sTime))
    return(str_time)

def getStrTimeStart(strDateTime, interval_sec):
    sTime = int(strDateTimeUTCToEpoch(strDateTime))     # utc seconds
    sTime = (sTime // interval_sec) * interval_sec
    str_time = time.strftime('%Y%m%d_%H%M%S', time.gmtime(sTime))
    return(str_time)

# --------------------------- directory functions
# https://www.geeksforgeeks.org/g-fact-41-multiple-return-values-in-python/
# function return tuple with multiple values:
# fCreated: True if the directory is created
# directory: string with full path directory
def setDirectory(base_dir, sub_dir, access_rights):
    fCreated = False
    directory = base_dir + "/" + sub_dir
    if not os.path.exists(directory):
        # create directory
        fCreated = True
        os.mkdir(directory, access_rights)
    return (fCreated, directory)

def appendDataJson(file_json, data):
    # write data to json file
    fOut = open(file_json, 'a+')
    json.dump(data, fOut)
    fOut.write('\n')
    ### with open(file_json, mode='a+', encoding='utf-8') as fOut:
    ###     for dt in data:
    ###         fOut.write(str(dt)+'\n')
    fOut.close()

# store acquisition data in 2 files
def storeAcquisitionJson(base_dir, access_rights, strDateTime, device, strExt, data):
    # divide string date-time
    strDate = getStrDate(strDateTime)
    strTime = getStrTimeStart(strDateTime, config.timeInterval)

    # create tree of directories if not exist. In this case fNewDir=True
    # device
    #    +-- log
    #         +-- strDate
    fNewDir, dir_device = setDirectory(base_dir, device, access_rights)
    fNewDir, dir_log = setDirectory(dir_device, 'log', access_rights)
    fNewDir, dir_date = setDirectory(dir_log, strDate, access_rights)
    # write data in json with time filename 
    OutFileName = dir_date + "/" + strTime + "." + strExt
    appendDataJson(OutFileName, data)

    # write data in json with device filename 
    OutFileName = dir_device + "/" + "dev_" + device + "." + strExt
    appendDataJson(OutFileName, data)

def storeInfoGateway(FileInfoGtw, FileListGtw, dev_id, gtw_data):
    # ---------------------------------------------
    # mod 06/03/2020:
    # if there are no coordinates, read from web the gateway info
    # 
    if ('latitude' not in gtw_data) or ('longitude' not in gtw_data):
        # no coordinates
        # get data from ttn:
        # https://www.thethingsnetwork.org/gateway-data/gateway/[id_gateway]
        idGtw = gtw_data['gtw_id']
        url = 'https://www.thethingsnetwork.org/gateway-data/gateway/' + idGtw
        r = requests.get(url)
        data = json.loads(r.content.decode())
        gtw_data['latitude'] = data[idGtw]['location']['latitude']
        gtw_data['longitude'] = data[idGtw]['location']['longitude']
        if 'altitude' in data[idGtw]['location']:
            gtw_data['altitude'] = data[idGtw]['location']['altitude']
    # ---------------------------------------------
    # continue normally
    
    # get gateway coordinates 
    gwcoords = {}
    gwcoords['latitude'] = gtw_data['latitude']
    gwcoords['longitude'] = gtw_data['longitude']
    if 'altitude' in gtw_data:
        gwcoords['altitude'] = gtw_data['altitude']
    # calc distance from dev_id, gateway
    dev_coords = (config.device[dev_id]['location']['latitude'], config.device[dev_id]['location']['longitude'])
    gtw_coords = (gtw_data['latitude'], gtw_data['longitude'])
    distance = int(geopy.distance.distance(dev_coords, gtw_coords).km)
    
    # prepare gateway data
    info = {}
    info['dev_id'] = dev_id
    info['dev_location'] = config.device[dev_id]['location']
    info['gtw_id'] = gtw_data['gtw_id']
    info['gtw_location'] = gwcoords
    info['distance'] = distance
    
    # create dictionary
    # gtw_info = {}
    # gtw_info[gtw_data['gtw_id']] = info
    # appendDataJson(FileName, gtw_info)
    appendDataJson(FileInfoGtw, info)
    appendDataJson(FileListGtw, info)

# store gateway data
# def storeGatewayJson(base_dir, access_rights, dev_id, strExt, gtw_data):
def storeGatewayJson(base_dir, access_rights, strDateTime, device, gateway, strExt, gtw_data):
    # divide string date-time
    strDate = getStrDate(strDateTime)
    strTime = getStrTimeStart(strDateTime, config.timeInterval)

    # create tree of directories if not exist. In this case fNewDir=True
    # device
    #    +-- gateway
    #           +-- log
    #                +-- strDate
    fNewDir, dir_device = setDirectory(base_dir, device, access_rights)
    fNewDir, dir_gateway = setDirectory(dir_device, gateway, access_rights)
    if fNewDir:
        # created directory gateway
        InfoGtw = dir_gateway + "/" + "inf_" + gateway + "." + strExt
        ListGtw = dir_device + "/" + "lgw_" + device + "." + strExt
        storeInfoGateway(InfoGtw, ListGtw, device, gtw_data)
        
    fNewDir, dir_log = setDirectory(dir_gateway, 'log', access_rights)
    fNewDir, dir_date = setDirectory(dir_log, strDate, access_rights)

    # ---------------------------------------------
    # in gtw_data, clean useless parameters
    gtw_data.pop('gtw_id', None)
    gtw_data.pop('latitude', None)
    gtw_data.pop('longitude', None)
    gtw_data.pop('altitude', None)
    # ---------------------------------------------

    # write gtw_data in json with time filename 
    OutFileName = dir_date + "/" + strTime + "." + strExt
    appendDataJson(OutFileName, gtw_data)

    # write gtw_data in json with gateway filename 
    OutFileName = dir_gateway + "/" + "gtw_" + gateway + "." + strExt
    appendDataJson(OutFileName, gtw_data)
    # update file with list of gateways
    # GwList = dir_device + "/gateways" + "." + strExt
    # if not os.path.exists(GwList):
    #      os.mkdir(directory, access_rights)


# https://pymotw.com/2/zipfile/
# https://stackoverflow.com/questions/30049201/how-to-compress-a-file-with-shutil-make-archive-in-python
# https://codetheory.in/how-to-automatically-zip-your-files-with-python/
def zip_file(dir_zip, access_rights, zip_name, fp_file):
    # create directories if not exist
    if not os.path.exists(dir_zip):
         os.mkdir(dir_zip, access_rights)
    fp_archive = dir_zip + "/" + zip_name
    # writes specified files to a ZIP archive
    zf = zipfile.ZipFile(fp_archive, 'a')
    try:
        zf.write(fp_file, arcname=basename(fp_file), compress_type=zip_compression )
    finally:    
        zf.close()

# save mqtt data
class save_mqtt:
  def __init__(self, base_dir, access_rights, fnExt, dir_zip, zip_name):
    self.base_dir = base_dir
    self.access_rights = access_rights
    self.dir_zip = dir_zip
    
    if not os.path.exists(base_dir):
         os.mkdir(base_dir, access_rights)
    self.fnExt = fnExt
    
    if not os.path.exists(dir_zip):
         os.mkdir(dir_zip, access_rights)
    self.dir_zip = dir_zip
    self.zip_name = zip_name
    
    self.counter = 0
    self.MaxCount = 100                         # 

  def update(self, data):
    if self.counter == 0:
        tm = int(time.time())                    # read actual time
        strTime = time.strftime('%Y%m%d_%H%M%S', time.gmtime(tm))
        # strTime = time.strftime('%Y%m%d_%H%M%S', time.localtime(tm))
        self.FileDest = self.base_dir + "/" + strTime + "." + self.fnExt

    with open(self.FileDest, mode='a+', encoding='utf-8') as fOut:
        fOut.write(data)
    fOut.close()
    self.counter = self.counter + 1
    # print("mqtt data update {}[{}]".format(self.counter, self.FileDest) )
    # # debug
    # zip_file(self.dir_zip, self.access_rights, self.zip_name, self.FileDest)
    # os.remove(self.FileDest)
    
    if self.counter >= self.MaxCount:
        self.counter = 0
        # arrivato al limite, archivia il file
        zip_file(self.dir_zip, self.access_rights, self.zip_name, self.FileDest)
        # remove old dest file
        os.remove(self.FileDest)

# create a class to save original mqtt data
svMqtt = save_mqtt(
    config.PathBaseDir + "/mqtt", 
    config.access_rights, 
    config.strExtension, 
    config.PathBaseDir + "/mqtt", 
    'acqmqtt.zip')

# nome directory creata in funzione dell'ora attuale
act_t = int(time.time())                    # read actual time
strActTime = time.strftime('%Y%m%d_%H%M%S', time.localtime(act_t))

# get time start interval
start_t = act_t
start_upd_json = ((start_t) // config.timeUpdateJson) * config.timeUpdateJson     # calc time start to update json
end_upd_json = start_upd_json + config.timeUpdateJson                # calc end update

start_t = ((start_t) // config.timeInterval) * config.timeInterval;      # time acquisition (use floor division)
end_t = ((start_t + config.timeInterval) // config.timeInterval) * config.timeInterval;      # end time acquisition (use floor division)

# create directory using actual date
strLocDate = time.strftime('%Y%m%d', time.localtime(start_t))
strLocTime = time.strftime('%Y%m%d_%H%M%S', time.localtime(start_t))

# -------------------------------------------------------
# per debug: read data from json file
#### print("Read mqtt00.json")
#### ---- VER01: simula la lettura mqtt leggendo da un file contenente una sequenza di righe json
#### mqttData = [json.loads(line) for line in open('mqtt00.json').readlines()]
####
#### ---- VER02: leggi tutti il file json in formato testo (ok, va bene)
#### https://stackoverflow.com/questions/8369219/how-to-read-a-text-file-into-a-string-variable-and-strip-newlines
#### mqttData = open('mqtt00.json', 'r').read()
#### print("End read mqtt00.json")
#### https://stackoverflow.com/questions/7472839/python-readline-from-a-string
#### json_data = io.StringIO(mqttData)
# -------------------------------------------------------

# -------------------------------------------------
# START MAIN
#
# -----------------------------------------
# global variables
cmd_mosquitto = []                      # list of commands mosquitto
process = []                            # list of processes
nProc = 0
idx = 0
# nCycles = 0
# -----------------------------------------        

# kill process mosquitto_sub
#
def kill_mosquitto_sub():
    proc_name = "mosquitto_sub"
    # psutil can find process by name and kill it
    for proc in psutil.process_iter():
        # check whether the process name matches
        if proc.name() == proc_name:
            proc.kill()

# MODIFICATO INSERENDO QUESTO https://gist.github.com/sebclaeys/1232088
def non_block_read(output):
    fd = output.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    result = ""
    try:
        result = output.read()
    except:
        print("except !!!!")
        result = ""
        pass
    return(result)

# elaborate mqtt data
def process_mqtt_string(mqttData):
    # https://stackoverflow.com/questions/7472839/python-readline-from-a-string
    json_data = io.StringIO(mqttData)
    # -------------------------------------------------------

    line = json_data.readline()
    svMqtt.update(line)
    # print(line)
    if (not line):
        return
    try:
        dt = json.loads(line)
        # dbg: print(line)
    except:
        return
    # -------------------------------------------------------
    # elaborazione dati mosquitto
    # -----------------------------------------
    #
    # check dt['time'] is not empty:
    if not dt['metadata']['time']:
        # the json has not time when the server received the message
        return
    
    # check if dt['dev_id'] is in config dictionary of devices
    if dt['dev_id'] not in config.device:
        return
    
    # remove fields not used
    dt.pop('app_id', None)
    # dt.pop('dev_id', None)
    dt.pop('hardware_serial', None)                                 # In case of LoRaWAN: the DevEUI
    dt.pop('port', None)                                            # LoRaWAN FPort
    dt.pop('counter', None)                                         # LoRaWAN frame counter
    dt.pop('is_retry', None)                                        # Is set to true if this message is a retry (you could also detect this from the counter)
    dt.pop('payload_raw', None)                                     # Base64 encoded payload: [0x01, 0x02, 0x03, 0x04]

    # section: dt['metadata']
    # dt['metadata'].pop('frequency', None)
    dt['metadata'].pop('modulation', None)                          # Modulation that was used - LORA or FSK
    dt['metadata'].pop('airtime', None)                             # Airtime in nanoseconds
    # dt['metadata'].pop('time', None)                              # Time when the server received the message
    dt['metadata'].pop('coding_rate', None)                         # Coding rate that was used

    # section: list ['metadata']['gateways']
    for gw in dt['metadata']['gateways']:
        # gw.pop('gtw_id', None)                # EUI of the gateway 
        gw.pop('timestamp', None)               # Timestamp when the gateway received the message 
        # gw.pop('time', None)                  # Time when the gateway received the message - left out when gateway does not have synchronized time 
        gw.pop('channel', None)                 # Channel where the gateway received the message 
        # gw.pop('rssi', None)                  # Signal strength of the received message 
        # gw.pop('snr', None)                   # Signal to noise ratio of the received message 
        gw.pop('rf_chain', None)                # RF chain where the gateway received the message 
        # gw.pop('latitude', None)              # Latitude of the gateway reported in its status updates 
        # gw.pop('longitude', None)             # Longitude of the gateway 
        # gw.pop('altitude', None)              # Altitude of the gateway 
        gw.pop('gtw_trusted', None)             #
        gw.pop('location_source', None)         # 
        # add data_rate to the gtw data
        gw['data_rate'] = dt['metadata']['data_rate']
        # check the absolute time difference from time when the server received the message 
        # and time when the gateway received the message is less than 3600sec (1 hour). 
        # In this case, the time of gateway is wrong. Use time of server.
        if ( (not gw['time']) or
            (abs(deltaSecDateTime(dt['metadata']['time'], gw['time'])) > 3600) ):
            gw['time'] = dt['metadata']['time']
        
        # ------ work with a copy of gateway data
        gtw_data = copy.deepcopy(gw)
        # ------ add new field: time server rx message
        gtw_data['tmrx_server'] = dt['metadata']['time']
        
        # store gateway data
        storeGatewayJson(config.PathGtwDir, config.access_rights, dt['metadata']['time'], dt['dev_id'], gtw_data['gtw_id'], config.strExtension, gtw_data)
    #
    # end of remove fields
    # -----------------------------------------

    # -----------------------------------------
    # store acquisitions
    storeAcquisitionJson(config.PathAcqDir, config.access_rights, dt['metadata']['time'], dt['dev_id'], config.strExtension, dt)

        
# -----------------------------------------        
# uccidi tutti i processi mosquitto_sub lanciati eventualmente in precedenza
kill_mosquitto_sub()
# -----------------------------------------        
# cmd_mosquitto = []                      # list of commands mosquitto
# process = []                            # list of processes
nProc = 0
for ttnapp_id, ttnapp_pw in config.TTNapplication.items():
    cmd = config.FormCmdMosquitto(ttnapp_id, ttnapp_pw)
    cmd_mosquitto.append(cmd)           # append command to list of commands
    # from: https://gist.github.com/sebclaeys/1232088    
    proc = Popen(cmd, shell=True, stdout=PIPE)      # create process
    process.append(proc)                            # append process to list of processes
    print("Cmd[{}]: [{}]".format(nProc, cmd))
    nProc = nProc + 1

idx = 0
while True:
    # -------------------------------------------------------
    # read data from mosquitto mqtt
    # Execute command mosquitto
    # https://gist.github.com/sebclaeys/1232088
    mqtt_data = non_block_read(process[idx].stdout) # will return '' instead of hanging for ever

    if (mqtt_data):
        # string is not empty
        # elaborazione stringa
        print("mqttData[{}]=[{}]".format(idx, mqtt_data))
        process_mqtt_string(mqtt_data.decode('utf-8'))
    
    ### try:
    ###     mqttData = non_block_read(process[idx].stdout) # will return '' instead of hanging for ever
    ###     if (mqttData):
    ###         # string is not empty
    ###         # elaborazione della stringa mqtt
    ###         print("mqtt_data[{}]=[{}]".format(idx, mqtt_data))
    ###         process_mqtt_string(mqtt_data)
    ### except:
    ###     print("mqtt_data[{}]=[None]".format(idx))
    ###     pass
        
    # increment idx
    idx = idx + 1
    if idx >= nProc:
        idx = 0
    #
    # continue while True
    # ---------------------------------------------
