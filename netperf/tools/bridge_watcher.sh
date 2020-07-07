#!/bin/bash
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

database=$( python3 /opt/netperf/netperf_settings.py --get db_filename )

echo "Ethernet Bridge Watcher"
echo "Press Q to exit."
printf "\nDatabase file: %s\n\n" "$database"
echo "rx_Mbps  tx_Mbps"
echo "-------  -------"
while true; do
	rx_tx_bps=$( sqlite3 "$database" "select rx_bps,tx_bps from bandwidth WHERE epoch_time = (SELECT MAX(epoch_time)  FROM bandwidth);" )
	rx_bps=$( echo "$rx_tx_bps" | awk -F'|' '{print $1}' )
	tx_bps=$( echo "$rx_tx_bps" | awk -F'|' '{print $2}' )
	rx_Mbps=$( echo "$rx_bps/10^6" | bc -l )
	tx_Mbps=$( echo "$tx_bps/10^6" | bc -l )
	printf "\r%7.4f  %7.4f" "$rx_Mbps" "$tx_Mbps"
	read -t 0.25 -N 1 input
	if [[ $input = "q" ]] || [[ $input = "Q" ]]; then
		echo
		break
	fi
done
