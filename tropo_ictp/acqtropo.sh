#!/bin/bash
# ------------------------------------------------------------
#
# get my_name and dir
cmd=$0
# echo $cmd
dir_script=$(dirname "${cmd}")
my_name=`basename "$0"`
# echo "my name: "$my_name
#
# check if script is already in execution
#
# https://stackoverflow.com/questions/16807876/shell-script-execution-check-if-it-is-already-running-or-not
# the -o %PPID parameter tells to omit the pid of the calling shell or shell script. 
# More info in the pidof man page.
if pidof -o %PPID -x $my_name >/dev/null; then
    echo "Process already running"
	exit
fi
# launch acquisition
# /usr/bin/python3 /root/tropo_ictp/mosqacq.py
# original
#/root/tropo_ictp/mosqacq.py
# mr acq
# /usr/bin/python3 /root/tropo_ictp/m03.py
/usr/bin/python3 /root/tropo_ictp/m04.py
