#!/bin/bash

declare -a tables

tables+=( "bandwidth" )
tables+=( "ping" )
tables+=( "iperf3" )
tables+=( "dns" )
tables+=( "speedtest" )
tables+=( "data_usage" )
tables+=( "isp_outages" )

database=$( python /opt/netperf/netperf_settings.py --get db_filename )

printf "\nDatabase file: %s\n\n" "$database"
printf "%-12s %s\n" "Table" "Rowcount"
printf "%-12s %s\n" "-----" "--------"

for table in "${tables[@]}"
do
	rowcount=$( sqlite3 "$database"	"select count(*) from $table;" )
	printf "%-12s %s\n" "$table" "$rowcount"
done
