#!/bin/bash
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.
#
# This script generates udev rules for renaming network interfaces so that they have predictable names.
#
# It looks for any interfaces that have the specified prefixes ('eth' and 'wlan') and renames them using
# the same scheme as 'Predictable Network Interface Names', i.e. the form 'enx{mac address}' for ethernet
# interfaces, and 'wlx{mac address}' for wireless interfaces. Example:
#
# current name  mac address        predictable name
# ------------  -----------------  ----------------
# eth0          dc:a6:32:8d:71:71  enxdca6328d7171
# wlan0         dc:a6:32:8d:71:72  wlxdca6328d7172
#
# This is useful for Raspberry Pi deployments as the 'Predictable Network Interface Names' setting in the
# raspi-config tool does not affect the integrated network interfaces. Creating udev rules ensures that
# these interfaces will have predictable names across system reboots.

UDEV_RULES_FILE="70-predictable-net-names.rules"
UDEV_RULES_DIR="/etc/udev/rules.d"
UDEV_RULES_PATH="${UDEV_RULES_DIR}/${UDEV_RULES_FILE}"
SYSFS_DIR="/sys/class/net"
MAC_ADDR_SEPARATORS=":-"
declare -A PREFIX_MAP
PREFIX_MAP["wlan"]="wlx"
PREFIX_MAP["eth"]="enx"
PREFIX_LIST=$(echo "${!PREFIX_MAP[@]}" | sed -rn 's/\s/\,/pg')
DIALOG_TITLE="Predictable Network Interface Names"

command -v whiptail > /dev/null
if ! [[ "$?" -eq 0 ]]; then
	printf "This script requires the whiptail command. Do you wish to install it?\n"
	select yn in "Yes" "No"; do
		case $yn in
			Yes )
				sudo apt install -y whiptail
				break
				;;
			No )
				printf "Exiting script, no changes were made.\n"
				exit 1
				;;
		esac
	done
fi

if [[ $EUID -ne 0 ]]; then
        printf "This script must be run as root, e.g:\nsudo ./$(basename $0)\n"
        exit 1
fi

if ! [[ -d "$SYSFS_DIR" ]]; then
	printf "Error: sysfs directory $SYSFS_DIR does not exist on this system.\n"
	exit 1
fi

if [[ -f "$UDEV_RULES_PATH" ]]; then
	mapfile -t udev_rules < "$UDEV_RULES_PATH"
else
	udev_rules=()
fi
interface_directories=($(eval "ls -bdx $SYSFS_DIR/{$PREFIX_LIST}* 2>/dev/null"))
new_rules_text=""
if [[ "${#interface_directories[@]}" -gt 0 ]]; then
	for idir in "${interface_directories[@]}"; do
		current_name=$(basename "$idir")
		mac_addr=$(<"${idir}/address")
		stripped_mac_addr=$(echo "$mac_addr" | sed -rn "s/[${MAC_ADDR_SEPARATORS}]//pg")
		if [[ "${udev_rules[@]}" != *"$mac_addr"* ]]; then
		        for prefix in "${!PREFIX_MAP[@]}"; do
				if [[ "$current_name" == "$prefix"* ]]; then
					pni_name="${PREFIX_MAP[$prefix]}$stripped_mac_addr"
					udev_rules+=("SUBSYSTEM==\"net\", ACTION==\"add\", ATTR{address}==\"${mac_addr}\", NAME=\"${pni_name}\"")
					new_rules_text+=$(printf "%-16s  %-17s  %s" "$current_name" "$mac_addr" "$pni_name\n")
				fi
			done
		fi
	done
else
	whiptail --title "$DIALOG_TITLE" --msgbox "All interfaces are already assigned Predictable Network Interface Names." 0 0
fi
if [[ "${#new_rules_text}" -gt 0 ]]; then
	headers=$(printf "%-16s  %-17s  %s\n%s" "Current name" "MAC address" "Predictable name" "----------------  -----------------  ----------------")
	prompt="Do you wish to apply these rules?"
	dialog_text="${headers}\n${new_rules_text}\n${prompt}"
	apply_rules=$(whiptail --title "$DIALOG_TITLE" --yesno "The following interface naming rules were created:\n\n$dialog_text" 0 0 2 3>&1 1>&2 2>&3; echo $([[ "$?" == 0 ]] && echo "yes" || echo "no"))
	if [[ "$apply_rules" == "yes" ]]; then
		for rule in "${udev_rules[@]}"; do
			printf "$rule\n" >> "$UDEV_RULES_PATH"
		done
		whiptail --title "$DIALOG_TITLE" --msgbox "The new interface naming rules have been written to:\n${UDEV_RULES_PATH}\n\nThey will be applied during the next reboot." 0 0
	else
		whiptail --title "$DIALOG_TITLE" --msgbox "Discarding changes." 0 0
	fi
else
	whiptail --title "$DIALOG_TITLE" --msgbox "No interface naming rules were added." 0 0
fi
exit 0
