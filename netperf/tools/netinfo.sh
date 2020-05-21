#!/bin/bash
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

printf "Network Performance Monitor interface configuration status\n\n"
printf "Interface info for root network namespace:\n"
printf "Links:\n"
ip link show
printf  "\nAddresses:\n"
ip addr show
printf "\nRoutes:\n"
ip route
mapfile -t nns_list < <( ip netns list | awk '{print $1}' )
printf "\nNetwork namespaces: ${nns_list[*]}\n"
for i in "${nns_list[@]}"; do
	cmd_prefix="sudo ip netns exec $i"
	printf '\n%80s\n' | tr ' ' -
	printf "\nInterface info for network namespace $i:\n"
	printf "Links:\n"
	$cmd_prefix ip link show
	printf "\nAddresses:\n"
	$cmd_prefix ip addr show
	printf "\nRoutes:\n"
	$cmd_prefix ip route
done
printf '\n%80s\n' | tr ' ' -
printf "End of interface configuration status.\n"
