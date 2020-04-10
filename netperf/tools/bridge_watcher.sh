#!/bin/bash
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

client_id=$(cat /proc/cpuinfo | grep Serial | awk '{print $3}' | sed 's/^0*//')
database="/mnt/usb_storage/netperf/$client_id/database/$client_id.db"

echo "Ethernet Bridge Watcher"
echo "Press Q to exit."
printf "\nDatabase file: %s\n\n" "$database"
echo "rx_Mbps  tx_Mbps"
echo "-------  -------"
while true; do
	rx_tx_bps=$( sqlite3 "$database" "select rx_bps,tx_bps from bandwidth WHERE epoch_time = (SELECT MAX(epoch_time)  FROM bandwidth);" )
	rx_bps=$( echo "$rx_tx_bps" | awk -F'|' '{print $1}' )
	tx_bps=$( echo "$rx_tx_bps" | awk -F'|' '{print $2}' )
	rx_Mbps=$( echo "$rx_bps/1000000" | bc -l )
	tx_Mbps=$( echo "$tx_bps/1000000" | bc -l )
	if [[ "$rx_Mbps" == "0" ]]; then
		rx_Mbps="0.0000"
	else
		rx_Mbps=$( printf "%0.4f" "$rx_Mbps" )
	fi
	if [[ "$tx_Mbps" == "0" ]]; then
		tx_Mbps="0.0000"
	else
		tx_Mbps=$( printf "%0.4f" "$tx_Mbps" )
	fi
	printf "\r%7s  %7s" "$rx_Mbps" "$tx_Mbps"
	read -t 0.25 -N 1 input
	if [[ $input = "q" ]] || [[ $input = "Q" ]]; then
		echo
        break
    fi
done
