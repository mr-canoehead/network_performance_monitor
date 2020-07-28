#!/bin/bash
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

# This script is used to associate a wireless network interface with a wireless network.
# It uses whiptail to interact with the user, stepping them through the process of
# scanning for wireless networks, selecting a SSID, and entering a passphrase.
# The output of this script is a wpa_supplicant configuration file for the interface.

INTERFACE="$1"
WPA_SUPPLICANT_PATH="/etc/wpa_supplicant"
#WPA_SUPPLICANT_FILENAME="$2"
WPA_SUPPLICANT_FILE="$WPA_SUPPLICANT_PATH/$INTERFACE.conf"
TITLE="Wireless network configuration"

# check command line parameters
if [[ "$#" -ne 1 ]]; then
	echo "Usage: $(basename $0) <interface_name>"
	exit 0
fi
if [[ ! -d "/sys/class/net/$INTERFACE" ]]; then
	echo "Error: interface $INTERFACE was not found."
	exit 1
fi
if [[ ! -d "/sys/class/net/$INTERFACE/phy80211" ]]; then
	echo "Error: $INTERFACE is not a wireless network interface."
	exit 1
fi

# check if wpa_supplicant daemon is already running for the interface
if [[ -e "/run/wpa_supplicant/$INTERFACE" ]]; then
	echo "wpa_supplicant daemon is running for $INTERFACE, shutting it down..."
	# shut down wpa_supplicant for the interface
	wpa_cli -i $INTERFACE terminate > /dev/null
	sleep 3
else
	echo "wpa_supplicant daemon is not running for $INTERFACE"
fi

# create the initial wpa_supplicant config file for the interface
printf "ctrl_interface=DIR=/var/run/netperf/wpa_supplicant\nupdate_config=1" | tee "$WPA_SUPPLICANT_FILE" > /dev/null

# start wpa_supplicant daemon for the interface
echo "Starting wpa_supplicant daemon for $INTERFACE..."
wpa_supplicant -B -c "$WPA_SUPPLICANT_FILE" -i "$INTERFACE" > /dev/null
sleep 5

# add a network
network_id=$(wpa_cli -i "$INTERFACE" add_network)

associated=false
skip_interface=false
until [[ "$associated" == true ]] || [[ "$skip_interface" == true ]]
do
	# scan for wireless networks
	result=$(wpa_cli -i "$INTERFACE" scan > /dev/null)

	# show progress gauge while the scan runs in the background, wait 5 seconds to allow time for it to complete before accessing the scan results
	PCT=0
	(
		while [[ $PCT != 100 ]];
		do
			PCT=`expr $PCT + 20`;
			echo $PCT;
			sleep 1;
		done;
	) | whiptail --title "$TITLE" --gauge "Scanning for wireless networks using interface $INTERFACE..." 8 60 0

	# read list of wireless networks detected during scan, build menu choice list
	wireless_networks=$(wpa_cli -i "$INTERFACE" scan_results | column -t | awk '{$1=""; $4="" ; if (NR>1) {print}}' | sed -e 's/^[ \t]*//;/^$/d' | sort -nrk 2)
	if [[ $? -ne 0 ]]; then
		echo "Unable to scan wireless networks using interface $INTERFACE"
		exit 1
	fi

	declare -a menu_choices

	while read -r freq rssi ssid
	do
		if [[ ! -z "$ssid" ]]; then
			# map network frequency to a descriptive label for display in the menu
			band=$([[ "$freq" -gt 3000 ]] && echo "   5GHz" || echo " 2.4GHz")
			menu_choices+=("$ssid" "$band")
		fi
	done < <(printf "${wireless_networks[@]}")

	if [[ "${#menu_choices[@]}" -eq 0 ]]; then
		whiptail --title "$TITLE" --msgbox "Unable to find wireless networks for interface $INTERFACE.\nSelect 'OK' to re-scan." 8 70 16
		continue
	fi

	ssid=$(whiptail --title "$TITLE" --cancel-button "Re-scan" --menu "Choose a network for wireless interface $INTERFACE:" 25 90 16 "${menu_choices[@]}" 3>&1 1>&2 2>&3)
	if [[ $? == 1 ]]; then
		# Re-scan
		continue
	fi

	result=$(wpa_cli -i "$INTERFACE" set_network "$network_id" ssid \"$ssid\")
	#OK/FAIL
	psk=$(whiptail --passwordbox "Enter the password for wireless network $ssid" 8 78 --nocancel --title "$TITLE" 3>&1 1>&2 2>&3)
	#OK/FAIL
	result=$(wpa_cli -i "$INTERFACE" set_network "$network_id" psk \"$psk\")
	#OK/FAIL
	result=$(wpa_cli -i "$INTERFACE" enable_network "$network_id")


	# show a progress gauge while we wait 10 seconds for the wireless interface to associate with the network
	PCT=0
	(
		while [[ $PCT != 100 ]];
		do
			PCT=`expr $PCT + 10`;
			echo $PCT;
			sleep 1;
		done;
	) | whiptail --title "$TITLE" --gauge "Connecting to wireless network $ssid..." 7 60 0

	result=$(wpa_cli -i "$INTERFACE" status | grep "wpa_state=COMPLETED")
	if [[ $? == 0 ]]; then
		whiptail --title "$TITLE" --msgbox "Successfully connected wireless interface $INTERFACE to the network $ssid.\nNetwork information will be saved in the file: $WPA_SUPPLICANT_FILE" 10 60 3>&1 1>&2 2>&3
		associated=true
	else
		#whiptail --title "$TITLE" --msgbox "Unable to connect interface $INTERFACE to the wireless network $ssid. Please choose a different wireless network or double-check your password." 15 40 3>&1 1>&2 2>&3
		whiptail --title "$TITLE" --yesno "Unable to connect interface $INTERFACE to the wireless network $ssid.\n\nPlease choose a different wireless network or double-check your password.\n\nDo you want to retry configuring the wireless network for this interface?" 13 80 3>&1 1>&2 2>&3
	if [[ "$?" -eq 1 ]]; then
		 whiptail --title "$TITLE" --msgbox "You will need to create a wpa_supplicant file for the interface $INTERFACE manually. Please refer to the sample configuration files in the Wiki for example wpa_supplicant files." 12 80 3>&1 1>&2 2>&3
		skip_interface=true
		fi
		associated=false
	fi
done

# save network configuration to wpa_supplicant file
result=$(wpa_cli -i "$INTERFACE" save_config > /dev/null)
