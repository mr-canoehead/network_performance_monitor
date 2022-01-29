#!/bin/bash
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

TITLE="Network Performance Monitor Deployment Status"
OUTPUT_FILE="/tmp/netperf_deployment_status.txt"

printf "%s" "Gathering system configuration info..."
grep -i "raspbian" /etc/os-release > /dev/null
if [[ "$?" -eq 0 ]]; then
	cmdline=$(cat /boot/cmdline.txt)
else
	cmdline="N/A"
fi

if [[ -L "/etc/systemd/network/99-default.link" ]]; then
	pnin_status="disabled"
else
	pnin_status="enabled"
fi

datetime=$(date)
block_devices=$(blkid)
mounts=$(mount)
os_release=$(cat /etc/os-release)
installed_os_packages=$(apt list --installed 2>/dev/null | grep -v "Listing...")
installed_python3_packages=$(pip3 list)
data_root=$(/opt/netperf/netperf_settings.py --get data_root 2>/dev/null)
if [[ "$?" -ne 0 ]]; then
	data_root="N/A"
else
	data_root_permissions=$(ls -ld "$data_root")
fi
wpa_supplicant_service_status=$(systemctl status wpa_supplicant)
wpa_supplicant_status=$(ps aux | grep wpa_supplicant | grep -v grep)
dhcpcd_conf=$(cat /etc/dhcpcd.conf | grep -v ^\# | grep -v ^$)
netperf_run=$(ls -l /run/netperf)
netperf_interfaces_service_status=$(systemctl status netperf-interfaces.service)
netperf_db_service_status=$(systemctl status netperf-interfaces.service)
dashboard_flask_service_status=$(systemctl status dashboard-flask.service)
dashboard_celery_service_status=$(systemctl status dashboard-celery.service)
mapfile -t nn_list < <( ip netns list | awk '{print $1}' )
network_namespaces="${nn_list[*]}\n"
default_nn_links=$(ip link show)
default_nn_addresses=$(ip addr show)
default_nn_routes=$(ip route)
if [[ "$default_nn_routes" = "" ]]; then
	default_nn_routes="N/A"
fi
netperf_config=$(cat /opt/netperf/config/netperf.json 2>/dev/null)
netperf_interface_config=$(cat /opt/netperf/config/interfaces.json 2>/dev/null)
crontab=$(crontab -l -u pi | grep -v "^\s*#")

OUTPUT="$TITLE\n"
OUTPUT+="$datetime\n\n"
OUTPUT+="OS release:\n$os_release\n\n"
OUTPUT+="cmdline.txt:\n$cmdline\n\n"
OUTPUT+="Predictable network interface names:\n$pnin_status\n\n"
OUTPUT+="Block devices:\n$block_devices\n\n"
OUTPUT+="Mounts:\n$mounts\n\n"
OUTPUT+="Installed OS packages:\n$installed_os_packages\n\n"
OUTPUT+="Installed Python3 packages:\n$installed_python3_packages\n\n"
OUTPUT+="Data root:\n$data_root_permissions\n\n"
OUTPUT+="WPA supplicant service status:\n$wpa_supplicant_service_status\n\n"
OUTPUT+="WPA supplicant status:\n$wpa_supplicant_status\n\n"
OUTPUT+="dhcpcd.conf:\n$dhcpcd_conf\n\n"
OUTPUT+="netperf /run:\n$netperf_run\n\n"
OUTPUT+="Netperf interfaces service status:\n$netperf_interfaces_service_status\n\n"
OUTPUT+="Netperf db service status:\n$netperf_db_service_status\n\n"
OUTPUT+="Dashboard flask service status:\n$dashboard_flask_service_status\n\n"
OUTPUT+="Dashboard celery service status:\n$dashboard_celery_service_status\n\n"
OUTPUT+="Interface info for default network namespace:\n"
OUTPUT+="Links:\n$default_nn_links\n\n"
OUTPUT+="Addresses:\n$default_nn_addresses\n\n"
OUTPUT+="Routes:\n$default_nn_routes\n\n"
OUTPUT+="Network namespaces:\n$network_namespaces\n"
for i in "${nn_list[@]}"; do
	cmd_prefix="sudo ip netns exec $i"
	OUTPUT+="Interface info for network namespace $i:\n"
	links=$($cmd_prefix ip link show 2>/dev/null)
	OUTPUT+="Links:\n$links\n"
	addresses=$($cmd_prefix ip addr show 2>/dev/null)
	OUTPUT+="Addresses:\n$addresses\n"
	routes=$($cmd_prefix ip route 2>/dev/null)
	if [[ "$routes" = "" ]]; then
		routes="N/A"
	fi
	OUTPUT+="Routes:\n$routes\n\n"
done
OUTPUT+="Netperf config:\n$netperf_config\n\n"
OUTPUT+="Interface config:\n$netperf_interface_config\n\n"
OUTPUT+="End of interface configuration status.\n\n"
OUTPUT+="pi user crontab:\n$crontab\n\n"
OUTPUT+="End of configuration info.\n"
printf "%b%s" "$OUTPUT" > "$OUTPUT_FILE"
printf "\n%s %s\n" "Configuration info has been saved to:" "$OUTPUT_FILE"
