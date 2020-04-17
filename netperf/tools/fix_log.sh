#!/bin/bash
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

# This script fixes issues related to the netperf log file; it creates the log directory if it doesn't exist,
# creates the inital log file as the 'pi' user if it doesn't exist, and changes ownership of the log file to 'pi'
# if it exists and is not owned by the 'pi' user (e.g. if the file was created by /opt/netperf/configure_interfaces.py
# run via the crontab). This ensures that the log file is writable by all processes run by the 'pi' user.

logfile="netperf.log"
data_root=$( /opt/netperf/netperf_settings.py --get data_root )

# create the log directory if it doesn't exist
if [[ ! -d "$data_root/log" ]]; then
	sudo -u pi mkdir "$data_root/log"
fi

# create the initial log file if it doesn't exist
if [[ ! -f "$data_root/log/$logfile" ]]; then
	sudo -u pi touch "$data_root/log/$logfile"
fi

# change ownership of the log file to the 'pi' user so that the Network Performance Monitor processes can write to it
owner=$(stat -c '%U' "$data_root/log/$logfile")
if [[ "$owner" != "pi" ]]; then
	chown pi:pi "$data_root/log/$logfile"
fi
