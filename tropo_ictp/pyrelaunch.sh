#!/bin/bash
# ------------------------------------------------------------
# Monitor and Restart a list of python script If Not Running
# from:
# https://www.osetc.com/en/how-to-run-cron-job-to-check-and-restart-service-if-dead-in-linux.html
#
# PLIST is the list of script to relaunch
PLIST="m03.py"
for p in $PLIST
do 
    pgrep -f $p 
    if [ $? -ne 0 ]
    then
		echo "relaunch python script: "$p
        /usr/bin/python3 /root/tropo_ictp/$p >/dev/null
	else
		echo "python script: "$p" is running"
	fi
done
