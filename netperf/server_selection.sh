#!/bin/bash
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.
#
# This script is used to set the speed test server selection method, and to choose a specific speed test server
# if the selection method is 'manual'.
#
# Note that the open source speedtest-cli is currently broken with regards to targeting a specific server; if the
# open source client is installed, this script will default to the automatic server selection setting.

TITLE="Network Performance Monitor Configuration"
INPUT_FIELD_SEPARATOR="\|\|"

speedtestClient=$( /opt/netperf/netperf_settings.py --get speedtest_client )
if [[ "$speedtestClient" == "ookla" ]]; then
	serverSelectionMethod=$( whiptail --title "$TITLE" --menu "Internet speed test server selection method:" 0 0 2 \
		Automatic: "let the speedtest client choose servers automatically" \
		Manual: "choose a specific server for performing speed tests" \
		3>&1 1>&2 2>&3 )

	serverId="None"
	cancel=false
	if [[ "$serverSelectionMethod" == *"Manual"* ]]; then
		serverAccepted=false
		until [[ "$serverAccepted" == true ]] || [[ "$cancel" == true ]]
		do
			printf "\nRequesting speed test server list...\n"
			serverList=$( /usr/bin/python /opt/netperf/get_speedtest_servers.py )
			if [[ "$?" -ne 0 ]]; then
				whiptail --title "$TITLE" --yesno "Unable to retrieve speed test server list.\nTry again?" 0 0
					if [[ "$?" -eq 0 ]]; then
					continue
				else
					cancel=true
					continue
				fi
			fi
			menuItems=()
			OLDIFS=$IFS
			IFS=$'\n'
			declare -A serverDetails
			while read line
			do
				id=$(echo "$line" | awk -F "$INPUT_FIELD_SEPARATOR" '{printf $1}')
				details=$(echo "$line" | awk  -F "$INPUT_FIELD_SEPARATOR" '{printf $2 " " $3}')
				menuItems+=("$id" "$details")
				serverDetails["$id"]="$details"
			done <<< $serverList
			IFS=$OLDIFS
			serverId=$( whiptail --title "$TITLE" --menu "Choose an Internet speed test server:" 18 100 10 "${menuItems[@]}" 3>&1 1>&2 2>&3 )
			if [[ "$?" -ne 0 ]]; then
				cancel=true
				continue
			fi
			whiptail --title "$TITLE" --yesno "The following server will be used for all Internet speed tests:\n\n$serverId ${serverDetails[$serverId]}\n\nContinue with this selection?" 0 0
			if [[ "$?" -eq 0 ]]; then
				serverAccepted=true
			else
				continue
			fi
		done
		if [[ "$serverId" == "None" ]]; then
			whiptail --title "$TITLE" --msgbox "Manual server selection failed.\nThe speed test server will be chosen automatically." 0 0
		fi
	else
		whiptail --title "$TITLE" --msgbox "The speedtest client will choose a server automatically." 0 0
	fi
else
	# speedtest-cli is being used, default to automatic server selection
	serverId="None"
fi

if [[ "$cancel" == true ]]; then
	echo "Speed test server selection canceled."
	exit 1
fi

sudo /opt/netperf/netperf_settings.py --set speedtest_server_id --value "$serverId"

if [[ "$serverId" != "None" ]]; then
	echo "Speed test server ID set to $serverId"
else
	echo "Speed test server will be selected automatically by the client."
fi
