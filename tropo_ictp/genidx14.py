#!/usr/bin/python3
# ----------------------------------------------------------------
# genidx11.py: inserito generazione grafici rssi e spreading factor
# genidx13.py: map data tmsnr of single device
# mapDataTmRssi(fullPathReport, deviceID):      function time - rssi
# mapDataTmSnr(fullPathReport, deviceID):       function time - snr
# Come modificare la pagina index per inserire un nuovo report
# La pagina index viene generata attraverso la funzione ReportIndexPage
#
# NOTA IMPORTANTE:
# genidx09.py differisce dalla versione precedente eseguendo il trasferimento dei dati 
# sul server remoto di visualizzazione
#
# MOD 06/4:
# risolto problema riga con caratteri non di testo nel file ./gtw/ggh_roof_omni_small/eui-b827ebfffe58f3ec/log/20200401/20200401_061500.json
# La riga con caratteri binari bloccava la conversione in formato json
# 
import gc
import json
import maya
import os
import io
import sys
# https://stackoverflow.com/questions/5067604/determine-function-name-from-within-that-function-without-using-traceback
import inspect
import subprocess
import urllib
import folium
from folium import plugins
from folium import IFrame

import numpy as np
import numpy.ma as ma
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly
import plotly.graph_objs as go
import plotly.express as px

import base64
from itertools import islice
import time
import calendar
import shutil
import stat

import zipfile
import shutil

import config                   # configuration data

# ------------------------------------------- non volatile parameters

nvm = dict()                                # create dictionary with non volatile parameters

# save state between restart
# https://stackoverflow.com/questions/14183288/python-saving-state-of-a-program-between-restarts

# get the filename with the non volatile parameters
def getNvmFile():
    # https://www.geeksforgeeks.org/python-os-path-splitext-method/
    # Split the path in root and ext pair 
    baseName = os.path.splitext(os.path.basename(sys.argv[0]))[0]   # give the the script name without the .py extension and the extension
    nvmFile = config.PathBaseDir + '/' + baseName + '.cnf'
    return(nvmFile)
    
# create dictionary of non volatile parameters
def iniNVM():
    global nvm                              # dictionary is global

    nvm.clear()                             # initialize dictionary
    # section of device list
    nvm['device'] = {}                      # empty dictionary
    nvm['device']['idx'] = -1               # index. -1 for restart read list of devices
    nvm['device']['count'] = 0              # n. devices
    nvm['device']['id'] = []                # list of device id

# get list of devices actually acquired
def updateAcqDevices():
    global nvm                              # dictionary is global

    # use list slicing to create new list
    nvm['device']['id'].clear()
    nvm['device']['id'] = [f.name for f in os.scandir(config.PathGtwDir) if f.is_dir() ]            # list of devices actually acquired
    nvm['device']['count'] = len(nvm['device']['id'])               # n. devices
    nvm['device']['idx'] = 0                                        # start from first device id

def saveNVM():
    global nvm                              # dictionary is global

    nvmFile = getNvmFile()
    with open(nvmFile, 'w') as f:
        json.dump(nvm, f)

# read the JSON nvm
def loadNVM():
    global nvm                              # dictionary is global

    nvmFile = getNvmFile()
    if os.path.exists(nvmFile):
        with open(nvmFile, 'r') as f:
            nvm = json.load(f)
    else:
        iniNVM()
        updateAcqDevices()
        saveNVM()

# return the name of actual device   
def getActualAcqDevice():
    name = ''
    index = nvm['device']['idx']
    if index < nvm['device']['count']:
        name = nvm['device']['id'][index]
        index = index + 1
        nvm['device']['idx'] = index
    return(name)

def finish():
    saveNVM()
    sys.exit()

# ------------------------------------------- non volatile parameters

# --------------------------- file functions
# write a string to a file (append)
def FWrite(FileName, data):
    with open(FileName,'wb') as fo:
        fo.write(data)
        fo.flush()
        # Close opend file
        fo.close()

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


# https://stackoverflow.com/questions/23020659/fastest-way-to-calculate-the-centroid-of-a-set-of-coordinate-tuples-in-python-wi
# calc centroid in coordinates
def centroidDevices(device, coordName):
    nElem = 0
    centroid_lat = 0.0
    centroid_lon = 0.0
    for i in device:
        # print(i, device[i])
        centroid_lat = centroid_lat + device[i][coordName]['latitude']
        centroid_lon = centroid_lon + device[i][coordName]['longitude']
        nElem = nElem + 1
    centroid_lat = centroid_lat / nElem
    centroid_lon = centroid_lon / nElem
    return (centroid_lat, centroid_lon)

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

# https://stackoverflow.com/questions/1868714/how-do-i-copy-an-entire-directory-of-files-into-an-existing-directory-using-pyth/31039095
def copytree(src, dst, symlinks = False, ignore = None):
  if not os.path.exists(dst):
    os.makedirs(dst)
    shutil.copystat(src, dst)
  lst = os.listdir(src)
  if ignore:
    excl = ignore(src, lst)
    lst = [x for x in lst if x not in excl]
  for item in lst:
    s = os.path.join(src, item)
    d = os.path.join(dst, item)
    if symlinks and os.path.islink(s):
      if os.path.lexists(d):
        os.remove(d)
      os.symlink(os.readlink(s), d)
      try:
        st = os.lstat(s)
        mode = stat.S_IMODE(st.st_mode)
        os.lchmod(d, mode)
      except:
        pass # lchmod not available
    elif os.path.isdir(s):
      copytree(s, d, symlinks, ignore)
    else:
      shutil.copy2(s, d)

# Modify 13/02/2020: used to send data to visualization server
def copyToVisualizationServer(src):
  # copy subdir tropo to /Volumes/ELEARNING/WIRELESS/wireless
  # original:
  # dst = 'mzennaro@140.105.28.91:/Volumes/ELEARNING/WIRELESS/wireless/tropo'
  dst = 'mzennaro@140.105.28.91:/Volumes/ELEARNING/WIRELESS/wireless'
  cmdScp = '/usr/bin/scp -rp {} {}'.format(src, dst)
  print(cmdScp)
  os.system(cmdScp)

# create dictionary of lists of device acquisitions per gateway
# Input:
# base_dir_gtw: base dir with gateway subdirectories
# gateway: gateway name
# strUtcStart: string with uct time start
# strUtcEnd: string with uct time end
# output
# ResultCode: 
#    0: there are no devices with distance greater than specified in config (tropo msg)
#    1: at least one device with distance greater than specified has sent a message to gtw
# gtwData:
#
# from gateway ID, get gateway data from time strUtcStart and strUtcEnd
# NOTE:
# this is the original getGatewayData
# The list of tropo elements include all TROPO connections from device to gateways
#
def getGatewayDataWithAllTropoElements(base_dir_gtw, gateway, strUtcStart, strUtcEnd, deviceID):
# def getGatewayData(base_dir_gtw, gateway):
    dayStart = strUtcStart[:8]
    dayEnd = strUtcEnd[:8]
    fNameStart = strUtcStart + ".json"
    fNameEnd = strUtcEnd + ".json"
    # print("file names:[{}]-[{}]".format(fNameStart, fNameEnd))
    gtwData = {}
    logDevice = {}          # list with log data
    
    # -------------------------------------------
    # init ResultCode:
    # 0: there are no devices with distance greater than specified in config (tropo msg)
    # 1: at least one device with distance greater than specified has sent a message to gtw
    # -------------------------------------------
    ResultCode = 0
    
    print("day start end: [{}][{}]".format(dayStart, dayEnd))
    # https://stackoverflow.com/questions/973473/getting-a-list-of-all-subdirectories-in-the-current-directory
    # subfolders = [f.path for f in os.scandir(folder) if f.is_dir() ]    
    # This will give the complete path to the subdirectory. If you only want the name of the subdirectory use f.name instead of f.path
    devList = [f.name for f in os.scandir(base_dir_gtw) if f.is_dir() ]
    # print(devList)
    # print("||||||||||||||||||||||||||||||||| gateway[{}]".format(gateway))
    # for dev_id in devList:
    dev_id = deviceID
    # check if gateway has received messages from device
    dir_gtw = base_dir_gtw + '/' + dev_id + '/' + gateway
    if not os.path.exists(dir_gtw):
        # the gateway doesn't received data from device with device_id
        return(ResultCode, gtwData)
        
    # print("--------------------- gtw[{}] ha ricevuto device[{}]".format(gateway, dev_id))
    
    fDeviceHasDataValid = False
    
    # -------------------------------------------
    # mod 21/10
    # get gtw info
    gtw_info = {}
    fFullPath = os.path.join( dir_gtw, "inf_" + gateway + ".json" )
    with open(fFullPath, 'r') as fInfo:
        gtw_info = json.loads(fInfo.read())

    # check tropo distance
    fDistanceTropo = False                          # no tropo distance
    if config.EnableCheckTropoDistance:
        # check of config.DistanceLimit is enabled
        if gtw_info['distance'] >= config.DistanceLimit:
            # candidate to tropo phenomenon
            fDistanceTropo = True                       # tropo distance
            ResultCode = 1
    
    # lista di tutti i file contenuti nella sottodirectory log
    dir_log = dir_gtw + '/log'
    for root, dirs, files in os.walk(dir_log):
        # print("root[{}] dirs[{}] files[{}]".format(root, dirs, files))
        dirs.sort()
        # work with directories between dayStart and dayEnd
        for dirname in dirs:
            # dbg print("[{}][{}]".format(dirname, os.path.join(root, dirname)))
            # check distance: if distance (gateway, device) is greater than Tropo distance, insert all data
            if(fDistanceTropo == False):
                # no tropo distance
                # check the directory name is between time limits
                if (dirname<dayStart) or (dirname>dayEnd):
                    # print("[{}][{}][{}](dirname<dayStart) or (dirname>dayEnd)".format(dayStart, dirname, dayEnd) )
                    continue
            base_dir_day = os.path.join(root, dirname)
            # check files in directories
            fileList = [f.name for f in os.scandir(base_dir_day) if f.is_file() ]
            fileList.sort()
            # print("fileList[{}]".format(fileList))
            for fName in fileList:
                if(fDistanceTropo == False):
                    # no tropo distance
                    # check if file name is between time limits
                    if (fName<fNameStart) or (fName>fNameEnd):
                        continue
                    
                # the device has sent messages to the gateway
                if fDeviceHasDataValid == False:
                    # ----------------- initialize the dictionary element
                    # print("fDeviceHasDataValid == False")
                    gtwData[dev_id] = {}
                    gtwData[dev_id]['info'] = {}            # gateway info
                    gtwData[dev_id]['log'] = []             # list of data acquisitions
                    # store info element
                    gtwData[dev_id]['info'] = gtw_info
                    # fFullPath = os.path.join( dir_gtw, "inf_" + gateway + ".json" )
                    # with open(fFullPath, 'r') as fInfo:
                    #     gtwData[dev_id]['info'] = json.loads(fInfo.read())
                    fDeviceHasDataValid = True

                fFullPath = os.path.join(base_dir_day, fName)
                if not os.path.exists(fFullPath):
                    print("getGatewayDataWithAllTropoElements FILE NON ESISTE:[{}]".format(fFullPath))
                    continue
                # qui debug conservare!!!! print("[{}][{}]".format(fName, fFullPath ))
                # print("------------------- [{}]".format(fName))
                with open(fFullPath, 'r') as fData:
                    # https://stackoverflow.com/questions/39332792/python-3-how-to-read-file-json-into-list-of-dictionary
                    # want to extend the grwData with the contents of the json list
                    # gtwData[dev_id]['log'] = gtwData[dev_id]['log'] + ( list(map(json.loads, fData)) )
                    # https://thispointer.com/python-how-to-merge-two-or-more-lists/
                    # dbg print(gtwData[dev_id]['log'])               # e' sempre vuoto !!!!!
                    # with extend, each element of the iterable gets appended onto the list.
                    # Extend is very useful when we want to join two or more lists into a single list. 
                    # ------------- ori
                    ## gtwData[dev_id]['log'].extend( list(map(json.loads, fData)) )
                    # mod 06/04
                    # attenzione: modifica per gestione errori sulla riga json
                    lst_fData = []
                    for line in fData:
                        try:
                            dtl = json.loads(line)
                            lst_fData.append(dtl)
                        except:
                            continue
                    gtwData[dev_id]['log'].extend( lst_fData )
                    fData.close()
                    # end mod 06/04
                    
                    # dbg print(gtwData[dev_id]['log'])
    # if dev_id in gtwData:
    #     print(gtwData[dev_id]['log'])
                        
    # print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    # print(gtwData)
    # print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    return(ResultCode, gtwData)


      
# create dictionary of lists of device acquisitions per gateway
# Input:
# base_dir_gtw: base dir with gateway subdirectories
# gateway: gateway name
# strUtcStart: string with uct time start
# strUtcEnd: string with uct time end
# output
# ResultCode: 
#    0: there are no devices with distance greater than specified in config (tropo msg)
#    1: at least one device with distance greater than specified has sent a message to gtw
# gtwData:
#
# from gateway ID, get gateway data from time strUtcStart and strUtcEnd
# NOTE:
# Mod 21/01/2020: see email MZ:
# all phenomena tropo and not tropo are treated equally
#
def getGatewayData(base_dir_gtw, gateway, strUtcStart, strUtcEnd, deviceID):
# def getGatewayData(base_dir_gtw, gateway):
    dayStart = strUtcStart[:8]
    dayEnd = strUtcEnd[:8]
    fNameStart = strUtcStart + ".json"
    fNameEnd = strUtcEnd + ".json"
    # print("file names:[{}]-[{}]".format(fNameStart, fNameEnd))
    gtwData = {}
    logDevice = {}          # list with log data
    
    # -------------------------------------------
    # init ResultCode:
    # 0: there are no devices with distance greater than specified in config (tropo msg)
    # 1: at least one device with distance greater than specified has sent a message to gtw
    # -------------------------------------------
    ResultCode = 0
    
    print("day start end: [{}][{}]".format(dayStart, dayEnd))
    # https://stackoverflow.com/questions/973473/getting-a-list-of-all-subdirectories-in-the-current-directory
    # subfolders = [f.path for f in os.scandir(folder) if f.is_dir() ]    
    # This will give the complete path to the subdirectory. If you only want the name of the subdirectory use f.name instead of f.path
    devList = [f.name for f in os.scandir(base_dir_gtw) if f.is_dir() ]
    # print(devList)
    # print("||||||||||||||||||||||||||||||||| gateway[{}]".format(gateway))
    # for dev_id in devList:
    dev_id = deviceID
    # check if gateway has received messages from device
    dir_gtw = base_dir_gtw + '/' + dev_id + '/' + gateway
    if not os.path.exists(dir_gtw):
        # the gateway doesn't received data from device with device_id
        return(ResultCode, gtwData)
        
    # print("--------------------- gtw[{}] ha ricevuto device[{}]".format(gateway, dev_id))
    
    fDeviceHasDataValid = False
    
    # -------------------------------------------
    # mod 21/10
    # get gtw info
    gtw_info = {}
    fFullPath = os.path.join( dir_gtw, "inf_" + gateway + ".json" )
    with open(fFullPath, 'r') as fInfo:
        gtw_info = json.loads(fInfo.read())

    # check tropo distance
    fDistanceTropo = False                          # no tropo distance
    if config.EnableCheckTropoDistance:
        # check of config.DistanceLimit is enabled
        if gtw_info['distance'] >= config.DistanceLimit:
            # candidate to tropo phenomenon
            fDistanceTropo = True                       # tropo distance
            ResultCode = 1
    
    # lista di tutti i file contenuti nella sottodirectory log
    dir_log = dir_gtw + '/log'
    for root, dirs, files in os.walk(dir_log):
        # print("root[{}] dirs[{}] files[{}]".format(root, dirs, files))
        dirs.sort()
        # work with directories between dayStart and dayEnd
        for dirname in dirs:
            # dbg print("[{}][{}]".format(dirname, os.path.join(root, dirname)))
            # check distance: if distance (gateway, device) is greater than Tropo distance, insert all data
            if (dirname<dayStart) or (dirname>dayEnd):
                # print("[{}][{}][{}](dirname<dayStart) or (dirname>dayEnd)".format(dayStart, dirname, dayEnd) )
                continue
            # ------------------------------------------
            # here tropo check:
            ### if(fDistanceTropo == False):
            ###     # no tropo distance
            ###     # check the directory name is between time limits
            ###     if (dirname<dayStart) or (dirname>dayEnd):
            ###         # print("[{}][{}][{}](dirname<dayStart) or (dirname>dayEnd)".format(dayStart, dirname, dayEnd) )
            ###         continue
            # ------------------------------------------
            # in time limits
            base_dir_day = os.path.join(root, dirname)
            # check files in directories
            fileList = [f.name for f in os.scandir(base_dir_day) if f.is_file() ]
            fileList.sort()
            # print("fileList[{}]".format(fileList))
            for fName in fileList:
                if (fName<fNameStart) or (fName>fNameEnd):
                    continue
                # ------------------------------------------
                # here tropo check:
                ### if(fDistanceTropo == False):
                ###     # no tropo distance
                ###     # check if file name is between time limits
                ###     if (fName<fNameStart) or (fName>fNameEnd):
                ###         continue
                # ------------------------------------------
                   
                # the device has sent messages to the gateway
                if fDeviceHasDataValid == False:
                    # ----------------- initialize the dictionary element
                    # print("fDeviceHasDataValid == False")
                    gtwData[dev_id] = {}
                    gtwData[dev_id]['info'] = {}            # gateway info
                    gtwData[dev_id]['log'] = []             # list of data acquisitions
                    # store info element
                    gtwData[dev_id]['info'] = gtw_info
                    # fFullPath = os.path.join( dir_gtw, "inf_" + gateway + ".json" )
                    # with open(fFullPath, 'r') as fInfo:
                    #     gtwData[dev_id]['info'] = json.loads(fInfo.read())
                    fDeviceHasDataValid = True

                fFullPath = os.path.join(base_dir_day, fName)
                if not os.path.exists(fFullPath):
                    print("getGatewayData FILE NON ESISTE:[{}]".format(fFullPath))
                    continue
                
                # qui debug conservare!!!! print("[{}][{}]".format(fName, fFullPath ))
                # print("------------------- [{}]".format(fName))
                with open(fFullPath, 'r') as fData:
                    # https://stackoverflow.com/questions/39332792/python-3-how-to-read-file-json-into-list-of-dictionary
                    # want to extend the grwData with the contents of the json list
                    # gtwData[dev_id]['log'] = gtwData[dev_id]['log'] + ( list(map(json.loads, fData)) )
                    # https://thispointer.com/python-how-to-merge-two-or-more-lists/
                    # dbg print(gtwData[dev_id]['log'])               # e' sempre vuoto !!!!!
                    # with extend, each element of the iterable gets appended onto the list.
                    # Extend is very useful when we want to join two or more lists into a single list. 
                    # ------------- ori
                    ## gtwData[dev_id]['log'].extend( list(map(json.loads, fData)) )
                    # mod 06/04
                    # attenzione: modifica per gestione errori sulla riga json
                    lst_fData = []
                    for line in fData:
                        try:
                            dtl = json.loads(line)
                            lst_fData.append(dtl)
                        except:
                            continue
                    gtwData[dev_id]['log'].extend( lst_fData )
                    fData.close()
                    # end mod 06/04
                    
                    # dbg print(gtwData[dev_id]['log'])
    # if dev_id in gtwData:
    #     print(gtwData[dev_id]['log'])
                        
    # print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    # print(gtwData)
    # print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    return(ResultCode, gtwData)

# convert string of spreading factor to value
def strSF2Value(str_sf):
    strSf = ["SF7BW125","SF8BW125","SF9BW125","SF10BW125","SF11BW125","SF12BW125"]
    sf = 7 + strSf.index(str_sf)
    return(sf)

# generate these elements:
# - graph rssi of data
# - spreading factor % of messages
# modify 25/11: return also the last value spreading factor
# modify 06/12: return time last message
def graphRssi(gtw_id, dev_id, gtwDt, percW, percH):

    # -------------------------------------------------
    gcm = gc.collect()
    print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))

    # https://chrisalbon.com/python/data_wrangling/pandas_time_series_basics/
    data = {}
    data.clear()                # initialize dictionary
    data['date'] = []
    data['date'].clear()
    data['rssi'] = []
    data['rssi'].clear()
    # list of messages with spreading factor from SP12 to SF7
    msg_sf = [0, 0, 0, 0, 0, 0]
    NumMsg = 0
    for sample in gtwDt[dev_id]['log']:
        # ---------------------------
        # orig
        # data['date'].append(sample["time"])
        # to get last msg time
        str_last_time = sample["time"]
        data['date'].append(str_last_time)
        # ---------------------------
        data['rssi'].append(sample["rssi"])
        # mod 25/11 get string of spreading factor
        str_spreading_factor = sample["data_rate"]
        # inc element in list of msg with spreading factor
        id_sf = strSF2Value(str_spreading_factor) - 7
        msg_sf[id_sf] = msg_sf[id_sf] + 1
        NumMsg = NumMsg + 1
    df = pd.DataFrame(data, columns = ['date', 'rssi'])
    # df["date"] = pd.to_datetime(df['date'], format="%y/%m/%d %H:%M:%S")
    df["date"] = pd.to_datetime(df['date'])
    df.index = df['date']
    del df['date']
    # print("------------------------------{}  {}".format(gtw_id, dev_id))
    # print(df)
    # print("------------------------------")
    # x = np.linspace(-np.pi, np.pi, 101)
    # sin = np.sin(x)
    # cos = np.cos(x)
    # cos[20:50] = np.NaN
    # return pd.DataFrame(np.asanyarray([sin, cos]).T, columns=['sin', 'cos'], index=x)
    resolution, width, height = 150, 7, 6
    ### resolution, width, height = 75, 21, 9           
    fig, ax = plt.subplots(figsize=(width, height))
    # ax = df.plot(x='date', y='rssi', legend=False)
    # original
    # ax = df.plot(ax=ax, legend=False, marker='o', linestyle='-')
    # mod 26/11: without linestyle
    ax = df.plot(ax=ax, legend=False, marker='o', linestyle=' ')
    # https://matplotlib.org/3.1.1/gallery/text_labels_and_annotations/date.html
    # ax.format_xdata = mdates.DateFormatter('%Y-%m-%d %H:%M:%S')
    # https://scentellegher.github.io/programming/2017/05/24/pandas-bar-plot-with-formatted-dates.html
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
    ax.grid(True)
    # ax = df.plot(x="date", y="rssi")
    ax.set_ylabel('rssi')
    
    # directory to save png files
    directory = config.PathBaseDir + "/rssi"
    if not os.path.exists(directory):
         os.mkdir(directory, config.access_rights)
    directory = directory + "/" + gtw_id
    if not os.path.exists(directory):
         os.mkdir(directory, config.access_rights)
    # full path of rssi png
    pngFile = directory + '/rssi_{}_{}.png'.format(gtw_id, dev_id)
    fig.savefig(pngFile, dpi=resolution)
    # encode a base64 png01
    encodedH64 = base64.b64encode(open(pngFile, 'rb').read())
    htmlImg = ''
    htmlImg = '</br>' + '<img style=\"width:{}%;height:{}%\" src="data:image/png;base64,{}">'.format(percW, percH, encodedH64.decode('UTF-8'))
    htmlImg = htmlImg + '</br>'
    # print(htmlImg)
    sfValue = strSF2Value(str_spreading_factor)
    # https://stackoverflow.com/questions/21884271/warning-about-too-many-open-figures
    plt.close()
    # ---------------------------------------------
    # form table of spreading factors
    tblSf = ''                              # empty table
    timeLastMsg = ''                        # time of last message
    if NumMsg:
        # there are messages
        # calc % of spreading factors. 1 decimal place
        sum = 0
        for i in range(5):
             value = (msg_sf[i] * 1000) / NumMsg
             sum = sum + value
             msg_sf[i] = value
        # the last element is the difference from 100 and sum of previous elements
        msg_sf[5] = 1000 - sum
        # create the html table
        tblSf = '<table>'
        tblSf = tblSf + '<tr><th>Data Rate</th><th>Configuration</th><th>Percentage of messages</th></tr>'
        tblSf = tblSf + '<tr><td>DR0</td><td>SF12/125kHz</td><td>' + "{0:0.1f}".format(float(msg_sf[5])/10.0) + '%</td></tr>'
        tblSf = tblSf + '<tr><td>DR1</td><td>SF11/125kHz</td><td>' + "{0:0.1f}".format(float(msg_sf[4])/10.0) + '%</td></tr>'
        tblSf = tblSf + '<tr><td>DR2</td><td>SF10/125kHz</td><td>' + "{0:0.1f}".format(float(msg_sf[3])/10.0) + '%</td></tr>'
        tblSf = tblSf + '<tr><td>DR3</td><td>SF9/125kHz</td><td>'  + "{0:0.1f}".format(float(msg_sf[2])/10.0) + '%</td></tr>'
        tblSf = tblSf + '<tr><td>DR4</td><td>SF8/125kHz</td><td>'  + "{0:0.1f}".format(float(msg_sf[1])/10.0) + '%</td></tr>'
        tblSf = tblSf + '<tr><td>DR5</td><td>SF7/125kHz</td><td>'  + "{0:0.1f}".format(float(msg_sf[0])/10.0) + '%</td></tr>'
        tblSf = tblSf + '</table>'

        # ---------------------------------------------
        # convert str_last_time to time value
        val_epoch = int(strDateTimeUTCToEpoch(str_last_time))       # utc seconds
        t_last_msg = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime(val_epoch))
    # ---------------------------------------------
    
    return(t_last_msg, sfValue, tblSf, htmlImg)

# ----------------------- Added 21/01/2020
# generate these elements:
# - graph snr (Signal Noise Ratio) of data
# - spreading factor % of messages
# modify 25/11: return also the last value spreading factor
# modify 06/12: return time last message
def graphSnr(gtw_id, dev_id, gtwDt, percW, percH):

    # -------------------------------------------------
    gcm = gc.collect()
    print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))

    # https://chrisalbon.com/python/data_wrangling/pandas_time_series_basics/
    data = {}
    data.clear()                # initialize dictionary
    data['date'] = []
    data['date'].clear()
    data['snr'] = []
    data['snr'].clear()
    # list of messages with spreading factor from SP12 to SF7
    # msg_sf = [0, 0, 0, 0, 0, 0]
    NumMsg = 0
    for sample in gtwDt[dev_id]['log']:
        # ---------------------------
        # orig
        # data['date'].append(sample["time"])
        # to get last msg time
        str_last_time = sample["time"]
        data['date'].append(str_last_time)
        # ---------------------------
        data['snr'].append(sample["snr"])
        # mod 25/11 get string of spreading factor
        # str_spreading_factor = sample["data_rate"]
        # inc element in list of msg with spreading factor
        # id_sf = strSF2Value(str_spreading_factor) - 7
        # msg_sf[id_sf] = msg_sf[id_sf] + 1
        # NumMsg = NumMsg + 1
    df = pd.DataFrame(data, columns = ['date', 'snr'])
    # df["date"] = pd.to_datetime(df['date'], format="%y/%m/%d %H:%M:%S")
    df["date"] = pd.to_datetime(df['date'])
    df.index = df['date']
    del df['date']
    # print("------------------------------{}  {}".format(gtw_id, dev_id))
    # print(df)
    # print("------------------------------")
    # x = np.linspace(-np.pi, np.pi, 101)
    # sin = np.sin(x)
    # cos = np.cos(x)
    # cos[20:50] = np.NaN
    # return pd.DataFrame(np.asanyarray([sin, cos]).T, columns=['sin', 'cos'], index=x)
    resolution, width, height = 150, 7, 6
    ### resolution, width, height = 75, 21, 9           
    fig, ax = plt.subplots(figsize=(width, height))
    # ax = df.plot(x='date', y='rssi', legend=False)
    # original
    # ax = df.plot(ax=ax, legend=False, marker='o', linestyle='-')
    # mod 26/11: without linestyle
    ax = df.plot(ax=ax, legend=False, marker='o', linestyle=' ')
    # https://matplotlib.org/3.1.1/gallery/text_labels_and_annotations/date.html
    # ax.format_xdata = mdates.DateFormatter('%Y-%m-%d %H:%M:%S')
    # https://scentellegher.github.io/programming/2017/05/24/pandas-bar-plot-with-formatted-dates.html
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
    ax.grid(True)
    # ax = df.plot(x="date", y="rssi")
    ax.set_ylabel('snr')
    
    # directory to save png files
    directory = config.PathBaseDir + "/snr"
    if not os.path.exists(directory):
         os.mkdir(directory, config.access_rights)
    directory = directory + "/" + gtw_id
    if not os.path.exists(directory):
         os.mkdir(directory, config.access_rights)
    # full path of snr png
    pngFile = directory + '/snr_{}_{}.png'.format(gtw_id, dev_id)
    fig.savefig(pngFile, dpi=resolution)
    # encode a base64 png01
    encodedH64 = base64.b64encode(open(pngFile, 'rb').read())
    htmlImg = ''
    htmlImg = '</br>' + '<img style=\"width:{}%;height:{}%\" src="data:image/png;base64,{}">'.format(percW, percH, encodedH64.decode('UTF-8'))
    htmlImg = htmlImg + '</br>'
    # print(htmlImg)
    # sfValue = strSF2Value(str_spreading_factor)
    # https://stackoverflow.com/questions/21884271/warning-about-too-many-open-figures
    plt.close()
    # ---------------------------------------------
    # form table of spreading factors
    #### tblSf = ''                              # empty table
    #### timeLastMsg = ''                        # time of last message
    #### if NumMsg:
    ####     # there are messages
    ####     # calc % of spreading factors. 1 decimal place
    ####     sum = 0
    ####     for i in range(5):
    ####          value = (msg_sf[i] * 1000) / NumMsg
    ####          sum = sum + value
    ####          msg_sf[i] = value
    ####     # the last element is the difference from 100 and sum of previous elements
    ####     msg_sf[5] = 1000 - sum
    ####     # create the html table
    ####     tblSf = '<table>'
    ####     tblSf = tblSf + '<tr><th>Data Rate</th><th>Configuration</th><th>Percentage of messages</th></tr>'
    ####     tblSf = tblSf + '<tr><td>DR0</td><td>SF12/125kHz</td><td>' + "{0:0.1f}".format(float(msg_sf[5])/10.0) + '%</td></tr>'
    ####     tblSf = tblSf + '<tr><td>DR1</td><td>SF11/125kHz</td><td>' + "{0:0.1f}".format(float(msg_sf[4])/10.0) + '%</td></tr>'
    ####     tblSf = tblSf + '<tr><td>DR2</td><td>SF10/125kHz</td><td>' + "{0:0.1f}".format(float(msg_sf[3])/10.0) + '%</td></tr>'
    ####     tblSf = tblSf + '<tr><td>DR3</td><td>SF9/125kHz</td><td>'  + "{0:0.1f}".format(float(msg_sf[2])/10.0) + '%</td></tr>'
    ####     tblSf = tblSf + '<tr><td>DR4</td><td>SF8/125kHz</td><td>'  + "{0:0.1f}".format(float(msg_sf[1])/10.0) + '%</td></tr>'
    ####     tblSf = tblSf + '<tr><td>DR5</td><td>SF7/125kHz</td><td>'  + "{0:0.1f}".format(float(msg_sf[0])/10.0) + '%</td></tr>'
    ####     tblSf = tblSf + '</table>'
    #### 
    ####     # ---------------------------------------------
    ####     # convert str_last_time to time value
    ####     val_epoch = int(strDateTimeUTCToEpoch(str_last_time))       # utc seconds
    ####     t_last_msg = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime(val_epoch))
    #### # ---------------------------------------------
    
    # return(t_last_msg, sfValue, tblSf, htmlImg)
    return(htmlImg)

# map data tmrssi of single device
def mapDataTmRssi(fullPathReport, deviceID):
    gcm = gc.collect()
    print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))

    fig = go.Figure()

    gtwDict = {}    # dictionary of gateway data
    ### dev = deviceID

    # read gateways data
    fnListGtw = config.PathGtwDir + "/" + deviceID + "/" + "lgw_" + deviceID + "." + config.strExtension
    print(fnListGtw)
    try:
        fhGtwData = open(fnListGtw, 'r')
    except:
        return
    for line in fhGtwData:
        # -------------------------------------------------
        gcm = gc.collect()
        print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))
        
        try:
            dt = json.loads(line)
            # print(line)
            # mqttData.append(json_object)
        except:
            gcm = gc.collect()
            print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))
            return
        
        # get specific gateway data
        # check if gateway has received messages from device
        gateway = dt['gtw_id']
        ### print(gateway)
        
        dir_gtw = config.PathGtwDir + '/' + deviceID + '/' + gateway
        ### print(dir_gtw)
        if not os.path.exists(dir_gtw):
            # the gateway doesn't received data from device with device_id
            print("not exist!!!")
            continue
        # -------------------------------------------
        # get gtw info
        gtw_info = {}
        fFullPath = os.path.join( dir_gtw, "inf_" + gateway + ".json" )
        with open(fFullPath, 'r') as fInfo:
            gtw_info = json.loads(fInfo.read())

        # check tropo distance
        fDistanceTropo = True                           # tropo distance
        # check of config.DistLimTmRssi
        if gtw_info['distance'] < config.DistLimTmRssi:
            # distance less to tropo phenomenon
            fDistanceTropo = False                      # no tropo distance
            continue
        fFullPath = os.path.join( dir_gtw, "gtw_" + gateway + ".json" )
        # mod 06/04/2020: prevent empty file
        if not os.path.exists(fFullPath):
            print("mapDataTmRssi FILE NON ESISTE:[{}]".format(fFullPath))
            continue
        ### print(fFullPath)
        
        df = pd.read_csv(fFullPath)
        df = df.replace('{"time": "','', regex=True)
        df = df.replace('"','', regex=True)
        df = df.replace('rssi:','', regex=True)

        fig.add_trace(go.Scatter(x=df[df.columns[0]], y=df[df.columns[1]],mode='markers',name=gateway)) 
            
    fhGtwData.close()
    fig.write_html(fullPathReport, auto_open=False)
    
    #-----------------------------------------------
    # map.save(fullPathReport)                 # save html map

    # -------------------------------------------------
    gcm = gc.collect()
    print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))

# added 26/03: map data time - snr
# map data tmrsnr of single device
def mapDataTmSnr(fullPathReport, deviceID):
    gcm = gc.collect()
    print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))

    fig = go.Figure()

    gtwDict = {}    # dictionary of gateway data
    ### dev = deviceID

    # read gateways data
    fnListGtw = config.PathGtwDir + "/" + deviceID + "/" + "lgw_" + deviceID + "." + config.strExtension
    print(fnListGtw)
    try:
        fhGtwData = open(fnListGtw, 'r')
    except:
        return
    for line in fhGtwData:
        # -------------------------------------------------
        gcm = gc.collect()
        print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))
        
        try:
            dt = json.loads(line)
            # print(line)
            # mqttData.append(json_object)
        except:
            gcm = gc.collect()
            print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))
            return
        
        # get specific gateway data
        # check if gateway has received messages from device
        gateway = dt['gtw_id']
        ### print(gateway)
        
        dir_gtw = config.PathGtwDir + '/' + deviceID + '/' + gateway
        ### print(dir_gtw)
        if not os.path.exists(dir_gtw):
            # the gateway doesn't received data from device with device_id
            print("not exist!!!")
            continue
        # -------------------------------------------
        # get gtw info
        gtw_info = {}
        fFullPath = os.path.join( dir_gtw, "inf_" + gateway + ".json" )
        with open(fFullPath, 'r') as fInfo:
            gtw_info = json.loads(fInfo.read())

        # check tropo distance
        fDistanceTropo = True                           # tropo distance
        # check of config.DistLimTmRssi
        if gtw_info['distance'] < config.DistLimTmRssi:
            # distance less to tropo phenomenon
            fDistanceTropo = False                      # no tropo distance
            continue
        fFullPath = os.path.join( dir_gtw, "gtw_" + gateway + ".json" )
        # mod 06/04/2020: prevent empty file
        if not os.path.exists(fFullPath):
            print("mapDataTmSnr FILE NON ESISTE:[{}]".format(fFullPath))
            continue
        ### print(fFullPath)
        
        df = pd.read_csv(fFullPath)
        df = df.replace('{"time": "','', regex=True)
        df = df.replace('"','', regex=True)
        df = df.replace('snr:','', regex=True)

        fig.add_trace(go.Scatter(x=df[df.columns[0]], y=df[df.columns[2]],mode='markers',name=gateway)) 
            
    fhGtwData.close()
    fig.write_html(fullPathReport, auto_open=False)
    
    #-----------------------------------------------
    # map.save(fullPathReport)                 # save html map

    # -------------------------------------------------
    gcm = gc.collect()
    print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))

# return the spreading factor as string
def strDataRate(x):
    if x=="SF7BW125" : return " SF7"
    if x=="SF8BW125" : return " SF8"
    if x=="SF9BW125" : return " SF9"
    if x=="SF10BW125": return "SF10"
    if x=="SF11BW125": return "SF11"
    if x=="SF12BW125": return "SF12"
    return(x)

# map data devsf of single device
def mapDataDevSf(fullPathReport, deviceID):
    gcm = gc.collect()
    print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))

    fig = go.Figure()

    gtwDict = {}    # dictionary of gateway data

    # read gateways data
    fnListGtw = config.PathGtwDir + "/" + deviceID + "/" + "lgw_" + deviceID + "." + config.strExtension
    print(fnListGtw)
    try:
        fhGtwData = open(fnListGtw, 'r')
    except:
        return
    # -------------- create empty DataFrame for bar graph
    # https://kite.com/python/answers/how-to-create-an-empty-dataframe-with-column-names-in-python
    # Call pd.DataFrame(columns = None) with a list of strings as columns to create an empty DataFrame with column names.
    # column_names = ["a", "b", "c"]
    # df = pd.DataFrame(columns = column_names)
    column_names = ['Spreading Factor', 'percentage', 'gateway']
    df_graph = pd.DataFrame(columns = column_names)
    ## print("------------------- initialize dataframe db_graph")
    ## print(df_graph)
    
    # --------------------------------------
    # create empty dataframe to initialize data for bar graph
    data_sf_empty = [
        [" SF7", 0.0, ""],
        [" SF8", 0.0, ""],
        [" SF9", 0.0, ""],
        ["SF10", 0.0, ""],
        ["SF11", 0.0, ""],
        ["SF12", 0.0, ""]
        ]
    empty_df_graph = pd.DataFrame(data_sf_empty, columns=column_names,dtype=float)
        
    for line in fhGtwData:
        # -------------------------------------------------
        gcm = gc.collect()
        print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))
        
        try:
            dt = json.loads(line)
            # print(line)
            # mqttData.append(json_object)
        except:
            gcm = gc.collect()
            print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))
            return
        
        # get specific gateway data
        # check if gateway has received messages from device
        gateway = dt['gtw_id']
        ### print(gateway)
        
        dir_gtw = config.PathGtwDir + '/' + deviceID + '/' + gateway
        ### print(dir_gtw)
        if not os.path.exists(dir_gtw):
            # the gateway doesn't received data from device with device_id
            print("not exist!!!")
            continue
        # -------------------------------------------
        # get gtw info
        gtw_info = {}
        fFullPath = os.path.join( dir_gtw, "inf_" + gateway + ".json" )
        with open(fFullPath, 'r') as fInfo:
            gtw_info = json.loads(fInfo.read())

        # check tropo distance
        fDistanceTropo = True                           # tropo distance
        # check of config.DistLimTmRssi
        if gtw_info['distance'] < config.DistLimTmRssi:
            # distance less to tropo phenomenon
            fDistanceTropo = False                      # no tropo distance
            continue
        fFullPath = os.path.join( dir_gtw, "gtw_" + gateway + ".json" )
        # mod 06/04/2020: prevent empty file
        if not os.path.exists(fFullPath):
            print("mapDataDevSf FILE NON ESISTE:[{}]".format(fFullPath))
            continue
        ### print(fFullPath)
        
        # leggi il file json dei messaggi ricevuti dal gateway e crea il dataframe
        df = pd.read_json(fFullPath, lines=True)
        # colums: ["time", "rssi", "snr", "data_rate", "tmrx_server"]
        # Delete multiple columns from the dataframe df
        # https://stackoverflow.com/questions/44931834/pandas-drop-function-error-label-not-contained-in-axis
        df.drop(["time", "rssi", "snr", "tmrx_server"], axis=1, inplace=True)
        # debug
        ### print(df.head())
        # from data_rate extract only spreading factor 
        # https://stackoverflow.com/questions/36213383/pandas-dataframe-how-to-apply-function-to-a-specific-column
        df['data_rate'] = df['data_rate'].apply(strDataRate)
        # rename column
        # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.rename.html
        # df.rename(columns={'data_rate': 'Spreading Factor'}, inplace = True)
        # df['data_rate'] = df['data_rate'].astype(int)
        
        # calc frequency of spreading factor
        ### print("----------------------------- dataframe frequenza % SF")
        sc = df['data_rate'].value_counts(normalize=True)
        df_1 = pd.DataFrame(sc)          # wrap pd.Series to pd.DataFrame
        df_vc1 = df_1.reset_index()
        df_vc1.columns = ['Spreading Factor', 'percentage']         # change column names
        ## print("------------------- sc = s.value_counts(normalize=True)")
        ## print(df_vc1)
        # calc percentage, multiply each value for 100
        df_vc1['percentage'] = df_vc1['percentage'] * 100           # calc percentage
        ## print(df_vc1)
        # add gateway column to dataframe. Gateway name is the default value
        df_vc1['gateway'] = gateway
        ## print("------------------- sc aggiornato con nome gateway")
        ## print(df_vc1)
        # result example:
        # Spreading Factor  percentage               gateway
        #             SF12       100.0  eui-0000024b080312f3

        # ------------------- concat the dataframe to df_graph
        df_graph = pd.concat([df_graph, df_vc1], ignore_index=True)
        ## print("------------------- risultato concatenazione dataframe [df_graph, df_vc1]")
        ## print(df_graph)
        # -------------------------------- end for line in fhGtwData:
           
    fhGtwData.close()
    ## print("------------------- risultato concatenazione dataframe [df_graph, df_vc1]")
    ## print(df_graph)
    # sort df_graph using spreading factor column
    df_graph = df_graph.sort_values(by=df_graph.columns[0],ascending=True)
    df_graph = df_graph.reset_index(drop=True)
    ## print("------------------- risultato ordinamento dataframe")
    ## print(df_graph)
    # check if df_graph is empty
    if df_graph.empty == True:
        print('DataFrame df_graph is empty')
        df_graph = pd.concat([df_graph, empty_df_graph], ignore_index=True)
    
    # create the bar graph
    # column_names = ['Spreading Factor', 'percentage', 'gateway']
    fig = px.bar(df_graph, x='Spreading Factor', y='percentage', color= 'gateway', barmode="group")
    fig.write_html(fullPathReport, auto_open=False)
    
    #-----------------------------------------------
    # map.save(fullPathReport)                 # save html map

    # -------------------------------------------------
    gcm = gc.collect()
    print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))

# load image encoded h64
def HtmlImage(ImgFullPath, percW, percH):
    # -------------------------------------------------
    gcm = gc.collect()
    print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))

    htmlImg = ''
    if os.path.isfile(ImgFullPath):
        # the image exist
        encodedH64 = base64.b64encode(open(ImgFullPath, 'rb').read())
        htmlImg = '</br>' + '<img style=\"width:{}%;height:{}%\" src="data:image/png;base64,{}">'.format(percW, percH, encodedH64.decode('UTF-8'))
        htmlImg = htmlImg + '</br>'
    # print(htmlImg)
    gcm = gc.collect()
    print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))
    return(htmlImg)

# map data of single device
def mapData(UtcStartTime, UtcEndTime, fullPathReport, deviceID):
    gcm = gc.collect()
    print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))

    # ------------------------------------------
    # convert UtcStartTime, UtcEndTime in string
    strUtcStart = time.strftime('%Y%m%d_%H%M%S', time.gmtime(UtcStartTime))
    strUtcEnd = time.strftime('%Y%m%d_%H%M%S', time.gmtime(UtcEndTime))
    print("{},{}".format(strUtcStart, strUtcEnd))
    # ------------------------------------------
    # original
    ## lat, lon = centroidDevices(config.device, "location")
    # mod 08/03/2020
    lat = config.device[deviceID]["location"]["latitude"]
    lon = config.device[deviceID]["location"]["longitude"]
    # end mod
    
    map = folium.Map(location=[lat, lon], zoom_start=6, tiles='Stamen Terrain')
    map             # Calls the map to display

    gtwDict = {}    # dictionary of gateway data
    dev = deviceID
    # original: for dev in config.device:
    # marker device
    folium.Marker([str(config.device[dev]['location']['latitude']), str(config.device[dev]['location']['longitude'])]).add_to(map)

    # read gateways data
    fnListGtw = config.PathGtwDir + "/" + dev + "/" + "lgw_" + dev + "." + config.strExtension
    try:
        fhGtwData = open(fnListGtw, 'r')
    except:
        return
    for line in fhGtwData:
        # -------------------------------------------------
        gcm = gc.collect()
        print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))

        # dbg print("fhGtwData[{}]".format(line))
        try:
            dt = json.loads(line)
            # print(line)
            # mqttData.append(json_object)
        except:
            gcm = gc.collect()
            print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))
            return
        
        # get specific gateway data
        gtwDict.clear()             # initialize dictionary
        # dbg print("-------------------------- read gateway[{}][{}][{}] data".format(dt['gtw_id'], strUtcStart, strUtcEnd)) 
        ResultCode, gtwDict = getGatewayData(config.PathGtwDir, dt['gtw_id'], strUtcStart, strUtcEnd, deviceID)
        # print("------------------ gateway data")
        # print(gtwDict)
        # print("------------------ gateway data")

        # check if there are acquisitions in that interval
        if not (dev in gtwDict):
            print('[{}] not in dict'.format(dev))
            # passa al prossimo elemento
            continue
            
        # there are some data for that specific dev_ID
        # ------------------------- form popup data
        # for efficiency, create a list. Append each element in string. At end return '\n'.join(lst)
        lpup = []
        lpup.clear()
        lpup.append('<b>Gateway ID: </b>')
        lpup.append(dt['gtw_id'])
        lpup.append('</br>')
        n_devices = len(gtwDict.keys())
        # pup = pup + '<b>Received msg from </b>' + str(n_devices)
        # if n_devices > 1:
        #     pup = pup + ' devices'+ '</br>'
        # else:
        #     pup = pup + ' device'+ '</br>'
        lpup.append(' device</br>')
        
        # original: for dev_log in gtwDict:
        dev_log = deviceID                  # only for 1 device
        dev_color = config.device[dev_log]['color']
        lpup.append('<hr>')                  # horizontal line
        lpup.append('<b>Device ID: </b>')
        lpup.append(dev_log)
        lpup.append('</br>')
        distance = gtwDict[dev_log]['info']['distance']
        lpup.append('<b>Distance (km): </b>')
        lpup.append(str(distance))
        lpup.append('</br>')
        nPacket = len(gtwDict[dev_log]['log'])
        lpup.append('<b>Number of packets received: </b>')
        lpup.append(str(nPacket))
        lpup.append('</br>') 
        
        # original pup = pup + graphRssi(dt['gtw_id'], dev_log, gtwDict, 100, 100)
        # mod 25/11
        t_last_msg, sfValue, tblSf, graph_rssi = graphRssi(dt['gtw_id'], dev_log, gtwDict, 100, 100)
        # -------------------
        # mod 21/01/2020
        # added graph Snr
        graph_snr = graphSnr(dt['gtw_id'], dev_log, gtwDict, 100, 100)
        # -------------------
        
        # original
        # pup = pup + '<b>Spreading factor last message: </b>' + str(sfValue) + '</br>' 
        # mod 06/12: print time last received message
        lpup.append('<b>Last received message on: </b>')
        lpup.append(t_last_msg)
        lpup.append(' UTC</br>') 
        lpup.append('</br>')
        lpup.append(tblSf)
        # ------------- graph rssi:
        lpup.append('</br></br>') 
        lpup.append(graph_rssi)
        # ------------- graph snr:
        # mod 21/01/2020
        lpup.append('</br></br>') 
        lpup.append(graph_snr)
        # -----------------------------------------------
        # mod 26/10/2019
        # show profile generated with splat
        # det full path of image
        imgPath = config.PathBaseDir + '/profileimg/' + dev_log + '/' + dt['gtw_id'] + '.png'
        lpup.append(HtmlImage(imgPath, 100, 100))
        pup = '\n'.join(lpup)
        # -----------------------------------------------

        # if n_devices > 1:
        #     # temporaneo: se gateway ha ricevuto messaggi da piu' devices
        #     dev_color = 'blue'
            
        # load popup data
        # ori:
        ### test = folium.Html(
        ###         pup ,
        ###         script=True)
        ### popup = folium.Popup(test, max_width=2650)
        # mod 31/10. See graph04.py
        ### per test resolution, width, height = 75, 21, 9           
        # forma iframe
        ### iframe = IFrame(pup, width=(width*resolution)+20, height=(height*resolution)+20)
        iframe = IFrame(pup, width=800, height=400)
        popup = folium.Popup(iframe, max_width=2650)
       
        if ResultCode == 0:
            # no tropo distance
            folium.CircleMarker(
                [float(dt['gtw_location']['latitude']), 
                float(dt['gtw_location']['longitude'])],
                radius=8,
                popup=popup,
                color= dev_color,
                fill=True,
                fill_color='#green',
                # fill_color='#red',
                fill_opacity=1).add_to(map)
        else:
            # gtw has tropo distance
            # use a polygon as different marker
            # https://gist.github.com/wrobstory/5609786
            folium.RegularPolygonMarker(
                [float(dt['gtw_location']['latitude']), 
                float(dt['gtw_location']['longitude'])],
                number_of_sides=6,
                radius=10,
                popup=popup,
                color= dev_color,
                fill=True,
                fill_color='#green',
                # fill_color='#red',
                fill_opacity=1).add_to(map)
            
    fhGtwData.close()
    
    #-----------------------------------------------
    # create a legend
    # https://medium.com/@bobhaffner/creating-a-legend-for-a-folium-map-c1e0ffc34373
    # multiline string
    # legend_html = '''
    #  <div style="position: fixed; 
    #  bottom: 50px; left: 50px; width: 200px; height: 90px; 
    #  border:4px solid black; z-index:9999; font-size:14px;
    #  background:#000;
    #  ">&nbsp; Tropo acquisition <br>
    #  &nbsp; East &nbsp; <i class="fa fa-map-marker fa-2x"
    #               style="color:green"></i><br>
    #  &nbsp; West &nbsp; <i class="fa fa-map-marker fa-2x"
    #               style=”color:red”></i>
    #   </div>
    #  '''
    legend_html = '''
     <div style="position: fixed; 
     bottom: 50px; left: 50px; width: 270px; height: 70px; 
     border:2px solid black; z-index:9999; font-size:16px;
     background:#fff;
     ">&nbsp; 
     '''
    ## t_start = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime(UtcStartTime))
    ## t_end = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime(UtcEndTime))
    t_start = time.strftime('%Y/%m/%d %H:%M', time.gmtime(UtcStartTime))
    t_end = time.strftime('%Y/%m/%d %H:%M', time.gmtime(UtcEndTime))
    legend_html = legend_html + 'One day tropo acquisition:<br>&nbsp;'
    legend_html = legend_html + 'T. start: &nbsp; ' + t_start + ' UTC<br>&nbsp;'
    legend_html = legend_html + 'T. end: &nbsp; ' + t_end + ' UTC<br>&nbsp;'
    legend_html = legend_html + '</div>'
    #-----------------------------------------------
    map.get_root().html.add_child(folium.Element(legend_html))
    
    map.save(fullPathReport)                 # save html map

    # -------------------------------------------------
    gcm = gc.collect()
    print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))

### --------------------------------------
# form a set of html report for device
def FormHtmlReportDevice(deviceID):
    gcm = gc.collect()
    print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))
    #----------------------

    # check if exist a subdirectory deviceID inside gtw
    PathDeviceGtw = config.PathGtwDir + "/" + deviceID
    if not os.path.isdir(PathDeviceGtw):
        # directory not exist, so no acquisitions from device
        return
        
    # ------------------- there are some messages from deviceID
    # create report and archive of data
    
    PathMapsDevice = config.PathMapDir + '/' + deviceID
    directory = PathMapsDevice
    if not os.path.exists(directory):
         os.mkdir(directory, config.access_rights)
    
    # get actual time
    act_t = int(calendar.timegm(time.gmtime()))    # read actual time GMT
    strUtcTime = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime(act_t))
    print("time act: [{}] [{}] [{}]".format(time.gmtime(), calendar.timegm(time.gmtime()), strUtcTime))
         
    # ------- create report 24h
    prev_t = act_t - (24*60*60)
    fullPathReport = PathMapsDevice + '/' + deviceID + '_1day.html'
    print("------------- mapData: [{}]-[{}][{}][{}]".format(prev_t, act_t, fullPathReport, deviceID))
    mapData(prev_t, act_t, fullPathReport, deviceID)
         
    # ------- create report 10gg
    prev_t = act_t - (24*60*60*10)
    fullPathReport = PathMapsDevice + '/' + deviceID + '_10days.html'
    print("10 giorni !!!!!!!!!!!!!!!!!!!!!")
    print("------------- mapData: [{}]-[{}][{}][{}]".format(prev_t, act_t, fullPathReport, deviceID))
    mapData(prev_t, act_t, fullPathReport, deviceID)

    # ------- create report 20gg
    prev_t = act_t - (24*60*60*20)
    fullPathReport = PathMapsDevice + '/' + deviceID + '_20days.html'
    print("------------- mapData: [{}]-[{}][{}][{}]".format(prev_t, act_t, fullPathReport, deviceID))
    mapData(prev_t, act_t, fullPathReport, deviceID)

    # ------- create report 30gg
    prev_t = act_t - (24*60*60*30)
    fullPathReport = PathMapsDevice + '/' + deviceID + '_30days.html'
    print("------------- mapData: [{}]-[{}][{}][{}]".format(prev_t, act_t, fullPathReport, deviceID))
    mapData(prev_t, act_t, fullPathReport, deviceID)
    
    # ------- create report all data
    prev_t = 0
    fullPathReport = PathMapsDevice + '/' + deviceID + '_all.html'
    print("------------- mapData: [{}]-[{}][{}][{}]".format(prev_t, act_t, fullPathReport, deviceID))
    mapData(prev_t, act_t, fullPathReport, deviceID)
    
    # ------- create report time-rssi
    fullPathReport = PathMapsDevice + '/' + deviceID + '_tmrssi.html'
    print("------------- mapDataTmRssi: [{}][{}]".format(prev_t, act_t, fullPathReport, deviceID))
    mapDataTmRssi(fullPathReport, deviceID)

    # ------- create report time-snr
    fullPathReport = PathMapsDevice + '/' + deviceID + '_tmsnr.html'
    print("------------- mapDataTmSnr: [{}][{}]".format(prev_t, act_t, fullPathReport, deviceID))
    mapDataTmSnr(fullPathReport, deviceID)

    # ------- create report time-spreading factor
    fullPathReport = PathMapsDevice + '/' + deviceID + '_tmsf.html'
    print("------------- mapDataTmRssi: [{}][{}]".format(prev_t, act_t, fullPathReport, deviceID))
    mapDataDevSf(fullPathReport, deviceID)
    
    # ------- create archive of acquisitions
    zipName = PathMapsDevice + '/' + deviceID + '.zip'
    with zipfile.ZipFile(zipName, mode='w') as zf:
        fn = PathDeviceGtw + '/lgw_' + deviceID + '.json'
        zf.write(fn, os.path.basename(fn))
        # list of subdirectories
        # https://stackoverflow.com/questions/973473/getting-a-list-of-all-subdirectories-in-the-current-directory
        subfolders = [f.path for f in os.scandir(PathDeviceGtw) if f.is_dir() ]
        for PathDir in subfolders:
            fn = PathDir + '/gtw_' + os.path.basename(PathDir) + '.json'
            if os.path.isfile(fn):
                zf.write(fn, os.path.basename(fn))
            fn = PathDir + '/inf_' + os.path.basename(PathDir) + '.json'
            if os.path.isfile(fn):
                zf.write(fn, os.path.basename(fn))
        zf.close()
    # end of FormHtmlReportDevice

# form the html report index page
def ReportIndexPage():
    # -------------------------------------------------
    gcm = gc.collect()
    print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))

    # list of devices
    LstDevices = [f.name for f in os.scandir(config.PathGtwDir) if f.is_dir() ]            # list of devices actually acquired
    
    indexHtml = ''                  # empty page

    # ------------------------------- read start section idm01.txt
    fnIdmSection = config.PathIdmDir + '/idm01.txt'
    print(fnIdmSection)
    try:
        fpSection = open(fnIdmSection, 'r')
        indexHtml = fpSection.read()
        fpSection.close()
    except:
        return('')

    # get actual time
    act_t = int(calendar.timegm(time.gmtime()))    # read actual time GMT
    strUtcTime = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime(act_t))
    print("time act: [{}] [{}] [{}]".format(time.gmtime(), calendar.timegm(time.gmtime()), strUtcTime))
    
    # ------------------------------- form table of devices info
    # for efficiency, create a list. Append each element in string. At end return '\n'.join(lst)
    lTblRep = []
    lTblRep.clear()
    #----------------------
    # set the section title
    lTblRep.append("<!-- Report of acquired devices -->\n\n")
    lTblRep.append("<br>\n")
    lTblRep.append("<h1 style=\"text-align: center;\">Acquired devices</h1>\n")

    #------------------------------------------------
    # create report info of table (first row of table)
    lTblRep.append("<!-- table report devices -->\n")
    lTblRep.append("<table class=\"table table-hover\">\n")
    lTblRep.append("<thead>\n")
    lTblRep.append("<tr>\n")
    lTblRep.append("<th>Device ID</th>\n")
    lTblRep.append("<th>Last update</th>\n")
    lTblRep.append("<th>Report 1</th>\n")
    lTblRep.append("<th>Report 2</th>\n")
    lTblRep.append("<th>Report 3</th>\n")
    lTblRep.append("<th>Report 4</th>\n")
    lTblRep.append("<th>Report 5</th>\n")
    lTblRep.append("<th>Report 6</th>\n")
    lTblRep.append("<th>Report 7</th>\n")
    lTblRep.append("<th>Report 8</th>\n")
    lTblRep.append("<th width=\"10%%\">Download Page</th>\n")

    lTblRep.append("</tr>\n")
    lTblRep.append("</thead>\n")
    lTblRep.append("<tbody>\n")

    for deviceID in LstDevices:
        #------------------------------------------------[start row table info]
        # create row table info
        lTblRep.append("<!-- row table -->\n")
        lTblRep.append("<tr>\n")
        
        # deviceID
        lTblRep.append("<td style=\"vertical-align:middle;\">\n")
        lTblRep.append("{}\n".format(deviceID))
        lTblRep.append("</td>\n")
        
        # update time
        lTblRep.append("<td style=\"vertical-align:middle;\">\n")
        lTblRep.append("{}\n".format(strUtcTime))
        lTblRep.append("</td>\n")
        
        # list of reports
        
        baseName = './'  + deviceID  + '/' + deviceID
        repName = baseName + '_1day.html'
        lTblRep.append("<td style=\"vertical-align:middle;\">\n")
        lTblRep.append("<a href=\"{}\">\n".format(repName))
        lTblRep.append("\"1 day\" </a>\n")
        lTblRep.append("</td>\n")
        
        repName = baseName + '_10days.html'
        lTblRep.append("<td style=\"vertical-align:middle;\">\n")
        lTblRep.append("<a href=\"{}\">\n".format(repName))
        lTblRep.append("\"10 days\" </a>\n")
        lTblRep.append("</td>\n")
        
        repName = baseName + '_20days.html'
        lTblRep.append("<td style=\"vertical-align:middle;\">\n")
        lTblRep.append("<a href=\"{}\">\n".format(repName))
        lTblRep.append("\"20 days\" </a>\n")
        lTblRep.append("</td>\n")
        
        repName = baseName + '_30days.html'
        lTblRep.append("<td style=\"vertical-align:middle;\">\n")
        lTblRep.append("<a href=\"{}\">\n".format(repName))
        lTblRep.append("\"30 days\" </a>\n")
        lTblRep.append("</td>\n")
        
        repName = baseName + '_all.html'
        lTblRep.append("<td style=\"vertical-align:middle;\">\n")
        lTblRep.append("<a href=\"{}\">\n".format(repName))
        lTblRep.append("\"All acq.\" </a>\n")
        lTblRep.append("</td>\n")
        
        repName = baseName + '_tmrssi.html'
        lTblRep.append("<td style=\"vertical-align:middle;\">\n")
        lTblRep.append("<a href=\"{}\">\n".format(repName))
        lTblRep.append("\"time-rssi\" </a>\n")
        lTblRep.append("</td>\n")
        
        repName = baseName + '_tmsnr.html'
        lTblRep.append("<td style=\"vertical-align:middle;\">\n")
        lTblRep.append("<a href=\"{}\">\n".format(repName))
        lTblRep.append("\"time-snr\" </a>\n")
        lTblRep.append("</td>\n")
        
        repName = baseName + '_tmsf.html'
        lTblRep.append("<td style=\"vertical-align:middle;\">\n")
        lTblRep.append("<a href=\"{}\">\n".format(repName))
        lTblRep.append("\"time-SF\" </a>\n")
        lTblRep.append("</td>\n")
        
        archiveName = baseName + '.zip'
        lTblRep.append("<td style=\"vertical-align:middle;\">\n")
        lTblRep.append("<a href=\"{}\">\n".format(archiveName))
        lTblRep.append("\"Acq. archive\" </a>\n")
        lTblRep.append("</td>\n")
        
        lTblRep.append("</tr>\n")
        #------------------------------------------------[end row table info]

    #----------------
    # write end of table
    lTblRep.append("<!-- end row table -->\n")
    lTblRep.append("</tbody>\n")
    lTblRep.append("</table>\n")
    TableRow = '\n'.join(lTblRep)
    
    # save TableRow in idm02report.txt
    PathIdmDir = config.PathBaseDir + "/idm"
    directory = PathIdmDir
    if not os.path.exists(directory):
         os.mkdir(directory, config.access_rights)
    fnIdmSection = config.PathIdmDir + '/idm02report.txt'         
    fpSection = open(fnIdmSection, 'w')
    fpSection.write(TableRow)
    fpSection.close()

    indexHtml += TableRow
    # ------------------------------- read end section idm03end.txt
    fnIdmSection = config.PathIdmDir + '/idm03end.txt'         
    try:
        fpSection = open(fnIdmSection, 'r')
        indexHtml += fpSection.read()
        fpSection.close()
    except:
        print("except")
        return('')

    # -------------------------------------------
    # create the directories used by index.html
    PathMapsJscript = config.PathMapDir + '/jscript'
    directory = PathMapsJscript
    if not os.path.exists(directory):
         os.mkdir(directory, config.access_rights)
    
    # copy jscript files in PathMapsJscript
    PathJscriptDir = config.PathBaseDir + '/jscript'
    files = [f.path for f in os.scandir(PathJscriptDir) if f.is_file() ]
    # https://www.tutorialspoint.com/How-to-copy-files-from-one-folder-to-another-using-Python
    for f in files:
        shutil.copy(f, PathMapsJscript) 
    
    #----------------------
    # save index.html
    PathIndexHtml = config.PathMapDir + '/index.html'
    fpIndex = open(PathIndexHtml, 'w')
    fpIndex.write(indexHtml)
    fpIndex.close()

# =======================================================================================
# ---------------------------------------------- main
# =======================================================================================
# Collecting now keeps the objects as uncollectable
# https://stackoverflow.com/questions/5067604/determine-function-name-from-within-that-function-without-using-traceback
gcm = gc.collect()
print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))

loadNVM()                       # load parameters saved
# debug
print(nvm)

# subdivide in block of 4 analysis. 
# reduced to 1 for Out Of Memory error
for i in range(1):
    gcm = gc.collect()
    print('---[{}] GC Unreachable objects: [{}] Remaining Garbage: [{}]'.format(inspect.currentframe().f_code.co_name, gcm, gc.garbage))

    # print("----------------- i [{}]".format(i))
    # check if there are no acquired parameters
    if nvm['device']['count'] == 0:
        break
    indexDevice = nvm['device']['idx']
    if indexDevice < nvm['device']['count']:
        deviceID = nvm['device']['id'][indexDevice]
        print("nameDevice[{}]".format(deviceID))

        FormHtmlReportDevice(deviceID)
        # ------- show html reports
        # copy tree
        # originale usato per server tedesco 116.203.83.146:
        copytree(config.PathMapDir, config.PathReportDestination)
        # mod 13/02/2020: usato per server ICTP
        ### copyToVisualizationServer(config.PathMapDir)
        # ------- end show html reports
        #
        indexDevice = indexDevice + 1
        nvm['device']['idx'] = indexDevice
    if indexDevice >= nvm['device']['count']:
        updateAcqDevices()              # update list of device acquired
    saveNVM()                           # save list of acquired parameters

ReportIndexPage()                       # create index page

    
