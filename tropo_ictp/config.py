# tropo configuration options

import os

# https://www.thethingsnetwork.org/docs/lorawan/frequency-plans.html
# frequency plan: used to filter also the gateways
#      'EU_863_870' ,'EU_433'     ,'US_902_928' ,'CN_470_510' ,
#      'CN_779_787' ,'AU_915_928' ,'AS_923'     ,'AS_920_923' ,
#      'AS_923_925' ,'KR_920_923' ,'IN_865_867'
frequency_plan = 'EU_863_870'
# frequency_plan = 'AS_923'

# timeInterval = 60 * 60          # change directory in seconds
# @@@ debug
timeInterval = 5 * 60          # change directory in seconds
# @@ ori timeUpdateJson = 60 * 60       # time to update json to analyze
# @@@ debug
timeUpdateJson = 10 * 60       # time to update json to analyze

# ---------- nota: non va bene se si lancia lo script da cron
# PathBaseDir = os.getcwd()                    # current working directory of the process
# ---------- MR: usare questo se si lancia lo script da cron
PathBaseDir = "/root/tropo_ictp"

# debug 
# PathBaseDir = "."

access_rights = 0o777          # define the access rights

PathAcqDir = PathBaseDir + "/acq"
# create directory for acquisition data, if not exist
directory = PathAcqDir
if not os.path.exists(directory):
     os.mkdir(directory, access_rights)

PathGtwDir = PathBaseDir + "/gtw"
# create directory for gateway data, if not exist
directory = PathGtwDir
if not os.path.exists(directory):
     os.mkdir(directory, access_rights)

# not used
# PathRssiDir = PathBaseDir + "rssi"
# # create directory if not exist
# directory = PathRssiDir
# if not os.path.exists(directory):
#      os.mkdir(directory, access_rights)

strExtension = "json"
# ------------------------------ form full path file names
# output file for 1 hour:
OutFile1Hour = PathAcqDir + "/" + "tropo" + "." + strExtension
DestFile1Hour = PathBaseDir + "/" + "tropo" + "." + strExtension

# for tropo.py
fnInput_json = DestFile1Hour             # json with acquisition data
fnLinks_device = PathBaseDir + "/" + "links_device.txt"
fnLinks_unique_device = PathBaseDir + "/" + "links_unique_device.txt"
#full path gateways
fnGateways_device = PathBaseDir + "/" + "gateways_device.csv"

# for visualyze.py
# destination file: index.html with map
# fnHtmlMap = 'index.html'                                                  
fnHtmlMap = '/var/www/html/tropo_ictp/index.html'                                                  

# for genidx01.py
# destination directory of index.html and reports
PathReportDestination = '/var/www/html/tropo_ictp'                                                  
# debug: PathReportDestination = './tropo_ictp'                                                  

# --------------------- for maps
# mod 06/11/2019
PathMapDir = PathBaseDir + "/maps"
# create directory for slides, if not exist
directory = PathMapDir
if not os.path.exists(directory):
     os.mkdir(directory, access_rights)

# html stubs to create html pages
PathIdmDir = PathBaseDir + "/idm"
# javascrip dir
PathJscriptDir = PathBaseDir + "/docfiles/jscript"
# icon dir
PathIcoDir = PathBaseDir + "/docfiles/ico"

# ------------------------------ end full path file names
                                                                      
# ------------------------------ mosquitto log command
# note: install latest version mosquitto
# see:
# https://noviello.it/come-installare-mosquitto-mqtt-broker-su-ubuntu-18-04-lts/
# sudo apt-add-repository ppa:mosquitto-dev/mosquitto-ppa
# sudo apt-get update
# sudo apt-get install mosquitto
# sudo apt-get install mosquitto-clients
# check mosquitto status
# sudo service mosquitto status
#
# Command line options eclipse mosquitto (https://mosquitto.org):
# -h (--host):
# Specify the host to connect to. Defaults to localhost.
# -p (--port):
# Connect to the port specified. If not given, the default of 1883 for plain MQTT or 8883 for MQTT over TLS will be used.    
# -t (--topic):
# The MQTT topic to subscribe to. See mqtt(7) for more information on MQTT topics.
# -u (--username):
# Provide a username to be used for authenticating with the broker. See also the --pw argument.
# -P (--pw):
# Provide a password to be used for authenticating with the broker. 
# Using this argument without also specifying a username is invalid when using MQTT v3.1 or v3.1.1. See also the --username option 
# -W:
# Provide a timeout as an integer number of seconds. mosquitto_sub will stop processing messages and disconnect after this number of seconds has passed. 
# The timeout starts just after the client has connected to the broker.
# -C:
# Disconnect and exit the program immediately after the given count of messages have been received. 
# This may be useful in shell scripts where on a single status value is required, for example.

# original cmd_mos = "/usr/bin/mosquitto_sub -h eu.thethings.network -p 1883 -t +/devices/+/up -P ttn-account-v2.Cg4a7GWcW5Vtnmvt8KQTSMO6_UZbNvloIVUVAmOFfcE -u tropo_ictp -C 1"
fp_CmdMosquitto = "/usr/bin/mosquitto_sub"              # full path mosquitto command
mos_host_ttn = "-h eu.thethings.network"                # mosquitto host ttn (-h opt)
mos_port = "-p 1883"                                    # mosquitto port (-p opt)
mos_topic = "-t +/devices/+/up"                         # mosquitto topic (-t opt)
# ori
# mos_timeout = "-W 5"                                    # mosquitto timeout after 5sec
# mos_nmsg = "-C 1"                                       # mosquitto nmsg to acq
# mr test
mos_timeout = ""                                    # mosquitto timeout after 5sec
mos_nmsg = ""                                       # mosquitto nmsg to acq

mos_parTTNAppID = "-u"                                  # parameter command: ttn application id to authenticate with the broker. Follow app_ID
mos_parTTNAppPass = "-P"                                # parameter command: ttn application id to authenticate with the broker- Follow password to ttn app

# dictionary of TTN applications registered.
# The format is: [application ID]: [password]
# The password used is the default key in TTN access keys section of ttn application
TTNapplication = {
    "tropo_ictp"            : "ttn-account-v2.Cg4a7GWcW5Vtnmvt8KQTSMO6_UZbNvloIVUVAmOFfcE",
	# aggiunta per Helix Venezia
	"test-venezia-helix"	: "ttn-account-v2.A6u2SMMBwFYKOmakLVO3_eQGoVKIsyYxen0A-ephSrs",
    # 31/01/2020 aggiunta per centraline torino
    "ixem-wine"             : "ttn-account-v2.WTdXW7_32n_DXurwYaO9-eSzH0hR-1Xlwj8tJwItJ40",
    # aggiunta per test:
    # "test-bsfrance"         : "ttn-account-v2.TsFoWEWZe0xENIS_wjwTLuXavF3esk7tXME0ozwZCw8"
    # aggiunta per device Manzoni 06/03/2020 installazione Germania (disabilitato)
    # "hb-tropotest"          : "ttn-account-v2._-frd3au58vS2NmSVBTdWuuIlxtsCkSgiGvvikzp_Uo"
    # aggiunta per device Manzoni 09/03/2020 installazione Spagna
    "lopy2ttn"              : "ttn-account-v2.TPE7-bT_UDf5Dj4XcGpcCQ0Xkhj8n74iY-rMAyT1bWg"
}

# form the mosquitto command in base of TTN application id and password
def FormCmdMosquitto(ttnAppID, ttnAppPass):
    global fp_CmdMosquitto                              # full path mosquitto command
    global mos_host_ttn                                 # mosquitto host ttn (-h opt)
    global mos_port                                     # mosquitto port (-p opt)
    global mos_topic                                    # mosquitto topic (-t opt)
    global mos_timeout                                  # mosquitto timeout after 5sec
    global mos_nmsg                                     # mosquitto nmsg to acq
    global mos_parTTNAppID                              # parameter command: ttn application id to authenticate with the broker. Follow app_ID
    global mos_parTTNAppPass                            # parameter command: ttn application id to authenticate with the broker- Follow password to ttn app

    cmd = "{} {} {} {} {} {} {} {} {} {}".format(
        fp_CmdMosquitto         ,                       # full path mosquitto command
        mos_host_ttn            ,                       # mosquitto host ttn (-h opt)
        mos_port                ,                       # mosquitto port (-p opt)
        mos_topic               ,                       # mosquitto topic (-t opt)
        mos_parTTNAppPass       ,                       # parameter command: ttn application id to authenticate with the broker- Follow password to ttn app
        ttnAppPass              ,                       # TTN application password
        mos_parTTNAppID         ,                       # parameter command: ttn application id to authenticate with the broker. Follow app_ID
        ttnAppID                ,                       # TTN application id
        mos_timeout             ,                       # mosquitto timeout
        mos_nmsg                                        # mosquitto nmsg to acq
        )
    return(cmd)
        
# ------------------------------- devices configuration

# dictionary with device data
device = {
   "ggh_roof_omni_small": {
        "location": {
            "latitude": 45.7038584,
            "longitude": 13.7180477,
             "altitude": 10
       },
        "color": 'red'
    },
   "helix-ve-01": {
        "location": {
            "latitude": 45.430538,
            "longitude": 12.354038,
            "altitude": 10
        },
        "color": 'green'
    },
   "5cf54d890d206c7cae43b77a": {
        "location": {
            "latitude": 39.152143,
            "longitude": 8.276366,
            "altitude": 1.2
        },
        "color": 'red'
    },
   "5b7d818c0d206c25a658940f": {
        "location": {
            "latitude": 45.622208,
            "longitude": 8.360729,
            "altitude": 1.2
        },
        "color": 'red'
    },
   "ggh_roof": {
        "location": {
            "latitude": 45.7038584,
            "longitude": 13.7180477,
            "altitude": 10
        },
        "color": 'green'
    },
   "ggh_roof_omni": {
        "location": {
            "latitude": 45.7038584,
            "longitude": 13.7180477,
            "altitude": 10
        },
        "color": 'red'
    },

   "tropo_grc1": {
        "location": {
            "latitude": 39.482712,
            "longitude":-0.346661,
            "altitude": 15
        },
        "color": 'red'
    },
}

# 21/10/2019
# to automatically recognize tropospheric phenomenon this distance limit from device and gateway in Km
DistanceLimit = 70
# -------------------------------
# 24/02/2020
# distance limit for tmrssi script. Set to 150Km
DistLimTmRssi = 70
# -------------------------------

# 22/01/2020:
# flag enable check DistanceLimit. If False, the DistanceLimit is not checked
EnableCheckTropoDistance = False

# distance limit from gateway and Device in Km
RadiusGtwDevice = 500

# ------------------------------- used for splat analysis
# PathSplatDir = PathBaseDir + "/splat"
# directory = PathSplatDir
# if not os.path.exists(directory):
#      os.mkdir(directory, access_rights)
# PathSplatDir stesso della directory dove si trova rfprobe
PathSplatDir = PathBaseDir

# directory to save qth files
directory = PathSplatDir + "/user"
if not os.path.exists(directory):
     os.mkdir(directory, access_rights)
PathQthDir = directory + "/tropo"
directory = PathQthDir
if not os.path.exists(directory):
     os.mkdir(directory, access_rights)

# directory to save img profiles
## PathImgProfileDir = PathQthDir + "/profileimg"
## directory = PathImgProfileDir
## if not os.path.exists(directory):
##      os.mkdir(directory, access_rights)
