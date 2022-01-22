#!/bin/bash
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

# This script performs three functions:
# 1) it is used as a systemd service dependency to prevent other services from starting before the netperf
#    data root directory exists (e.g. the usb device it is located on has not yet been mounted)
# 2) it creates the netperf/log directory and initial log file if they do not exist
# 3) it fixes the ownership of the netperf log file if it exists and is not owned by the 'pi' user.


NETPERF_LOG="netperf.log"
MOUNT_WAIT_SECONDS=180
logger "Checking Network Performance Monitor data directory:"
data_root=$( /opt/netperf/netperf_settings.py --get data_root )
data_root_exists=false
warn=true
for (( s=0; s<"$MOUNT_WAIT_SECONDS"; s++ ))
do
	if [[ -d "$data_root" ]]; then
		data_root_exists=true
		break
	else
		if [[ "$warn" = true ]]; then
			logger "netperf data root directory not found, waiting up to $MOUNT_WAIT_SECONDS seconds for directory to be mounted..."
			warn=false
		fi
		sleep 1
	fi
done
exit_status=0
if [[ "$data_root_exists" = true ]]; then
	logger "netperf data root directory exists."
	# create the log directory if it doesn't exist
	if [[ ! -d "$data_root/log" ]]; then
	        sudo -u pi mkdir "$data_root/log"
	fi
	# create the initial log file if it doesn't exist
	if [[ ! -f "$data_root/log/$NETPERF_LOG" ]]; then
		sudo -u pi touch "$data_root/log/$NETPERF_LOG"
	fi
	# change ownership of the log file to the 'pi' user so that the Network Performance Monitor processes can write to it
	owner=$(stat -c '%U' "$data_root/log/$NETPERF_LOG")
	if [[ "$owner" != "pi" ]]; then
        	chown pi:pi "$data_root/log/$NETPERF_LOG"
	fi
else
	logger "netperf data root directory does not exist, please check your system configuration."
	exit_status=1
fi
exit "$exit_status"
