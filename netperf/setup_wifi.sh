#!/bin/bash
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

# This script is used to associate a wireless network interface with a wireless network.
# It uses whiptail to interact with the user, stepping them through the process of
# scanning for wireless networks, selecting a SSID, and entering a passphrase.
# The output of this script is a wpa_supplicant configuration file for the interface.

COUNTRY_CODE="$1"
INTERFACE="$2"
WPA_SUPPLICANT_PATH="/opt/netperf/config/wpa_supplicant"
WPA_SUPPLICANT_FILE="$WPA_SUPPLICANT_PATH/$INTERFACE.conf"
CTRL_INTERFACE_PATH="/var/run/netperf/wpa_supplicant"
TITLE="Wireless network configuration"

# check command line parameters
if [[ "$#" -ne 2 ]]; then
	echo "Usage: $(basename $0) <wifi_country_code> <interface_name>"
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

mkdir -p "$WPA_SUPPLICANT_PATH"
mkdir -p "$CTRL_INTERFACE_PATH"

# check if wpa_supplicant daemon is already running for the interface
if [[ -e "${CTRL_INTERFACE_PATH}/$INTERFACE" ]]; then
	echo "wpa_supplicant daemon is running for $INTERFACE, shutting it down..."
	# shut down wpa_supplicant for the interface
	wpa_cli -i "$INTERFACE" -p "$CTRL_INTERFACE_PATH" terminate > /dev/null
	sleep 3
else
	echo "wpa_supplicant daemon is not running for $INTERFACE"
fi

# create the initial wpa_supplicant config file for the interface
printf "ctrl_interface=DIR=${CTRL_INTERFACE_PATH}\nupdate_config=1\ncountry=${COUNTRY_CODE}" | tee "$WPA_SUPPLICANT_FILE" > /dev/null

# start wpa_supplicant daemon for the interface
echo "Starting wpa_supplicant daemon for $INTERFACE..."
wpa_supplicant -B -c "$WPA_SUPPLICANT_FILE" -i "$INTERFACE" > /dev/null
sleep 5

# add a network
network_id=$(wpa_cli -i "$INTERFACE" -p "$CTRL_INTERFACE_PATH" add_network)

associated=false
skip_interface=false
until [[ "$associated" == true ]] || [[ "$skip_interface" == true ]]
do
	# scan for wireless networks
	result=$(wpa_cli -i "$INTERFACE" -p "$CTRL_INTERFACE_PATH" scan > /dev/null)

	# show progress gauge while the scan runs in the background, wait 10 seconds to allow time for it to complete before accessing the scan results
	PCT=0
	(
		while [[ $PCT != 100 ]];
		do
			PCT=`expr $PCT + 10`;
			echo $PCT;
			sleep 1;
		done;
	) | whiptail --title "$TITLE" --gauge "Scanning for wireless networks using interface $INTERFACE..." 8 80 0

	# get list of wireless networks detected during scan
	wireless_networks=$(wpa_cli -i "$INTERFACE" -p "$CTRL_INTERFACE_PATH" scan_results | column -t | awk '{$4="" ; if (NR>1) {print}}' | sed -e 's/^[ \t]*//;/^$/d' | sort -nrk 3)

	if [[ $? -ne 0 ]]; then
		echo "Unable to scan wireless networks using interface $INTERFACE"
		exit 1
	fi

	declare -a menu_choices
	declare -A ssids
	declare -A bands

	# parse the list of wireless networks, build item strings for the whiptail selection menu
	while read -r bssid freq rssi ssid
	do

                if [[ "$ssid" == "" ]]; then
                        ssid_text="n/a (no SSID for this network)"
                else
                        ssid_text="$ssid"
                fi
		ssids["$bssid"]="$ssid"

		# map network frequency to band description
                if [[ "$freq" -gt 900 && "$freq" -lt 1000 ]]; then
                        band="900MHz"
                elif [[ "$freq" -gt 2400 && "$freq" -lt 2500 ]]; then
                        band="2.4GHz"
                elif [[ "$freq" -gt 3600 && "$freq" -lt 3700 ]]; then
                        band="3.65GHz"
                elif [[ "$freq" -gt 5000 && "$freq" -lt 5900 ]]; then
                        band="5GHz"
                else
			band="undefined"
		fi
		bands["$bssid"]="$band"

		# build string value for this menu item
                bssid_info=$(printf " %7s %5s   %-32s" "$band" "$rssi" "$ssid_text")
                menu_choices+=("$bssid" "$bssid_info")
	done < <(printf "${wireless_networks[@]}")

	menu_height=10
	menu_headings="       BSSID           BAND  RSSI   SSID"

	# adjust menu heading indent if there's no menu scrollbar
	if [[ "${#ssids[@]}" -le "$menu_height" ]]; then
        	menu_headings=" $menu_headings"
	fi

	if [[ "${#menu_choices[@]}" -eq 0 ]]; then
		whiptail --title "$TITLE" --msgbox "Unable to find wireless networks for interface $INTERFACE.\nSelect 'OK' to re-scan." 8 70 16
		continue
	fi

	bssid=$(whiptail --title "$TITLE" --cancel-button "Re-scan" --menu "Choose a network for wireless interface $INTERFACE:\n\n$menu_headings" 20 75 "$menu_height" "${menu_choices[@]}" 3>&1 1>&2 2>&3)

	if [[ $? == 1 ]]; then
		# Re-scan
		continue
	fi

	# set bssid for network
	result=$(wpa_cli -i "$INTERFACE" -p "$CTRL_INTERFACE_PATH" bssid "$network_id" "$bssid")
	ssid="${ssids[$bssid]}"
	if [[ ${#ssid} -eq 0 ]]; then
		# hidden SSID, prompt user to enter one
		ssid_ok=false
		ssid_prompt="SSID is hidden for this network. Enter network SSID:"
		until [[ "$ssid_ok" == true ]]; do
			ssid=$(whiptail --inputbox "$ssid_prompt" --title "$TITLE" 10 60 3>&1 1>&2 2>&3)
			if [[ "${#ssid}" -lt 2 ]] || [[ "${#ssid}" -gt 32 ]]; then
				ssid_prompt="Invalid SSID. Please enter a valid SSID:"
				ssid_ok=false
			else
				ssid_ok=true
			fi
		done
		# wpa_supplicant requires scan_ssid=1 in order to connect to hidden networks
		result=$(wpa_cli -i "$INTERFACE" -p "$CTRL_INTERFACE_PATH" set_network "$network_id" scan_ssid 1)
	fi
	result=$(wpa_cli -i "$INTERFACE" -p "$CTRL_INTERFACE_PATH" set_network "$network_id" ssid \"$ssid\")

	passphrase=$(whiptail --passwordbox "Enter the password for wireless network $ssid" 8 60 --nocancel --title "$TITLE" 3>&1 1>&2 2>&3)

	# generate PSK
	wpa_psk=$(wpa_passphrase "$ssid" "$passphrase" | sed -rn 's/^\s*psk=(.*)$/\1/p')

	result=$(wpa_cli -i "$INTERFACE" -p "$CTRL_INTERFACE_PATH" set_network "$network_id" psk "$wpa_psk")
	result=$(wpa_cli -i "$INTERFACE" -p "$CTRL_INTERFACE_PATH" enable_network "$network_id")

	# show a progress gauge while we wait for the wireless interface to associate with the network
	PCT=0
	(
		while [[ $PCT != 100 ]];
		do
			result=$(wpa_cli -i "$INTERFACE" -p "$CTRL_INTERFACE_PATH" status | sed -rn 's/^\s*wpa_state=(.*)$/\1/p')
			if [[ "$result" == "COMPLETED" ]]; then
				break
			fi
			PCT=`expr $PCT + 2`;
			echo $PCT;
			sleep 1;
		done;
	) | whiptail --title "$TITLE" --gauge "Connecting to wireless network $ssid..." 7 60 0

	result=$(wpa_cli -i "$INTERFACE" -p "$CTRL_INTERFACE_PATH" status | sed -rn 's/^\s*wpa_state=(.*)$/\1/p')
	if [[ "$result" == "COMPLETED" ]]; then
		associated=true
		whiptail --title "$TITLE" --msgbox "Successfully connected wireless interface $INTERFACE to the network $ssid.\nNetwork information will be saved in the file: $WPA_SUPPLICANT_FILE" 10 60 3>&1 1>&2 2>&3
	else
		whiptail --title "$TITLE" --yesno "Unable to connect interface $INTERFACE to the wireless network $ssid.\n\nPlease choose a different wireless network or double-check your password.\n\nDo you want to retry configuring the wireless network for this interface?" 13 80 3>&1 1>&2 2>&3
		if [[ "$?" -eq 1 ]]; then
			whiptail --title "$TITLE" --msgbox "You will need to create a wpa_supplicant file for the interface $INTERFACE manually. Please refer to the sample configuration files in the Wiki for example wpa_supplicant files." 12 80 3>&1 1>&2 2>&3
			skip_interface=true
		fi
	fi
done

# save network configuration to wpa_supplicant file
result=$(wpa_cli -i "$INTERFACE" -p "$CTRL_INTERFACE_PATH" save_config > /dev/null)
