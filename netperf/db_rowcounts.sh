#!/bin/bash

declare -a tables

tables+=( "bandwidth" )
tables+=( "ping" )
tables+=( "iperf3" )
tables+=( "dns" )
tables+=( "speedtest" )
tables+=( "isp_outages" )

client_id=$(cat /proc/cpuinfo | grep Serial | awk '{print $3}' | sed 's/^0*//')
database="/mnt/usb_storage/netperf/$client_id/database/$client_id.db"
printf "\nDatabase file: %s\n\n" "$database"

printf "%-12s %s\n" "Table" "Rowcount"
printf "%-12s %s\n" "-----" "--------"

for table in "${tables[@]}"
do
	rowcount=$( sqlite3 "$database"	"select count(*) from $table;" )
	printf "%-12s %s\n" "$table" "$rowcount"
done
