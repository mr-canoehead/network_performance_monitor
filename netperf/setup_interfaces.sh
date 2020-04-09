#!/bin/bash
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.


NET_INFO_PATH="/sys/class/net/"
pingtest_retcode_file="/tmp/pingtest.retcode"
TITLE="Network Performance Monitor Configuration"
APPLICATION_PATH="/opt/netperf"
OUTPUT_FILE="$APPLICATION_PATH/config/interfaces.json"

###### Supporting Functions

function check_addr_assigned () {
	if [[ " ${interface_ipv4_addrs[@]} " =~ " ${1} " ]]; then
		return 255
	else
		return 0
	fi
}

function check_valid_ipv4 () {
 if [[ $1 =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
   return 0
 else
   return 255
 fi
}

function pingtest() {
        ping -c4 -w 5 $1 > /dev/null
        echo $? > /tmp/pingtest.retcode
}


##### Start of the main script

declare -A interface_types
declare -A phy_names
declare -A supports_netns
declare -A interface_namespaces
declare -A interface_ipv4_addrs
declare -A interface_aliases
declare -A ipv4_gw
declare -a ethernet_interfaces

if [[ $EUID -ne 0 ]]; then
	echo "This script must be run as root, e.g:"
	echo "sudo ./$(basename $0)"
	exit 1
fi

# check if the interfaces have already been configured
ns_count=$( ip netns list | wc -l )
if [[ "$ns_count" -ne "0" ]]; then
        whiptail --title "$TITLE" --msgbox "The network interfaces have already been configured on this system.\nTo reconfigure the interfaces, please refer to the page:\n\"Reconfiguring the network interfaces\" in the project Wiki" 10 76 3>&1 1>&2 2>&3
        exit 1
fi

result=$(whiptail --title "$TITLE" --yesno "This script will generate a configuration file for the Network Performance Monitor network interfaces. If a configuration file already exists, it will be overwritten.\nBefore continuing, you should have performed the network interface identification and physical labeling procedure described in the wiki.\nDo you wish to proceed?" 13 80 3>&1 1>&2 2>&3)
if [ $? == 1 ]; then
	exit 0
fi

###### Network Interface Detection

# get list of network interfaces, excluding the loopback interface
mapfile -t interfaces < <( ls $NET_INFO_PATH | sed -n '/\blo\b/!p' )
#echo ${interfaces[@]}

# gather details for each interface
for i in "${interfaces[@]}"
do
	dir="$NET_INFO_PATH$i/phy80211"
	if [ -d "$dir" ]; then
		interface_types["$i"]="wireless"
		phy_name=$(cat "$dir/name")
		phy_names["$i"]="$phy_name"
		iw phy "$phy_name" info | grep netns > /dev/null
		if [ $? == 0 ]; then
			supports_netns["$i"]=true
		else
			supports_netns["$i"]=false
		fi
	else
		ethernet_interfaces+=( "$i" )
		interface_types["$i"]="ethernet"
		# most ethernet adapters support switching network namespaces, so let's assume it
		supports_netns["$i"]=true
	fi
	#interface_choices="$interface_choices $i ${interface_types[$i]} off"
done


##### Bandwidth Monitor Configuration

result=$(whiptail --title "$TITLE" --yesno "Do you wish to configure the Bandwidth Monitor? This feature requires two dedicated Ethernet interfaces." 10 54 3>&1 1>&2 2>&3)
if [ ! $? == 1 ]; then
	if [ ${#ethernet_interfaces[@]} -lt 3 ]; then
		if [ ${#ethernet_interfaces[@]} -eq 1 ]; then
			interface_message="Only 1 Ethernet interface was detected. Please add 2 additional Ethernet interfaces"
		else
			interface_message="Only 2 Ethernet interfaces were detected. Please add 1 additional Ethernet interface"
		fi
		whiptail --title "$TITLE" --msgbox "At least 3 Ethernet interfaces are needed in order to configure the Network Performance Monitor with the Bandwidth Monitor option. $interface_message and then re-run this configuration script." 12 80 3>&1 1>&2 2>&3
		exit 0
	fi
	configure_bwmonitor=true
	ethernet_choices=""
	# build menu choice list for bwmonitor upstream interface
	for i in "${ethernet_interfaces[@]}"
	do
		ethernet_choices="$ethernet_choices $i $i"
	done

	# prompt user to select bwmonitor upstream interface (ISP Modem LAN port)
	upstream_interface=$(whiptail --title "$TITLE" --menu --nocancel "Choose the Upstream Ethernet interface for the Bandwidth Monitor (the interface that will be connected to the ISP Modem LAN port):" 15 80 5 --noitem ${ethernet_choices[@]} 3>&1 1>&2 2>&3)

	delete_interface=("$upstream_interface")
	ethernet_interfaces=(${ethernet_interfaces[@]/$delete_interface})

	# remove interface from main list so that it can't be chosen as a testing interface later
	interfaces=(${interfaces[@]/$delete_interface})

	# build menu choice list for bwmonitor downstream interface
	ethernet_choices=""
	for i in "${ethernet_interfaces[@]}"
	do
		ethernet_choices="$ethernet_choices $i $i"
	done

	# prompt user to select bwmonitor downstream interface (Router WAN port)
	downstream_interface=$(whiptail --title "$TITLE" --menu --nocancel "Choose the Downstream Ethernet interface for the Bandwidth Monitor (the interface that will be connected to the Router WAN port):" 15 80 5 --noitem ${ethernet_choices[@]} 3>&1 1>&2 2>&3)
	delete_interface=("$downstream_interface")
	ethernet_interfaces=(${ethernet_interfaces[@]/$delete_interface})

	# remove interface from main list so that it can't be chosen as a testing interface later
	interfaces=(${interfaces[@]/$delete_interface})
else
	configure_bwmonitor=false
fi

##### Test Execution Network Interface Selection

if [ ${#ethernet_interfaces[@]} -eq 1 ]; then
	# only 1 ethernet interface left, we'll use it as the test execution network interface
	whiptail --title "$TITLE" --msgbox --nocancel "The Ethernet network interface ${ethernet_interfaces[0]} will be used as the test execution network interface. The performance test programs (iperf3, speedtest-cli, etc.) will be run in the Network Namespace associated with this interface. You should connect this interface to a regular LAN port on your router." 12 80 3>&1 1>&2 2>&3
	test_execution_interface=${ethernet_interfaces[@]}
else
	ethernet_choices=""
	# build menu choice list for bwmonitor upstream interface
	for i in "${ethernet_interfaces[@]}"
	do
		ethernet_choices="$ethernet_choices $i $i"
	done
	# prompt user to select test execution network interface
	test_execution_interface=$(whiptail --title "$TITLE" --menu --nocancel "Choose the test execution network interface. The performance test programs (iperf3, speedtest-cli, etc.) will be run in the Network Namespace associated with this interface. You should connect the selected interface to a normal LAN port on your router." 17 78 5 --noitem ${ethernet_choices[@]} 3>&1 1>&2 2>&3)
fi
delete_interface=("$test_execution_interface")
ethernet_interfaces=(${ethernet_interfaces[@]/$delete_interface})
# remove interface from main list so that it can't be chosen as a test interface later
interfaces=(${interfaces[@]/$delete_interface})


##### Selection of Additional Testing Interfaces

# build the checklist choice list
for i in "${interfaces[@]}"
do
	interface_choices="$interface_choices $i ${interface_types[$i]} off"
done

# prompt user to select additional interfaces for configuration
checklist_selections=$(whiptail --title "$TITLE" --checklist --nocancel --separate-output "Select additional network interfaces to configure as testing targets.\nUse the spacebar to toggle selections:" "$((${#interfaces[@]} + 8))" 50  "${#interfaces[@]}" $interface_choices 3>&1 1>&2 2>&3)

# split results into array
selected=($(echo "$checklist_selections" | tr ' ' '\n'))

# add the test execution interface to the list so that it will be configured in the next step
selected=( "${selected[@]}" "$test_execution_interface" )

##### Network Interface Configuration

# get default gateway
default_gateway=$(ip route | grep -m 1 default | awk '{print $3}')
ip_subnet=$(echo $default_gateway | cut -d"." -f1-3)


for s in "${selected[@]}"
do
	title="Configuration info for $s"
	valid_ip=false
	until [ $valid_ip == true ]
	do
		default_gateway=$(whiptail --title "$title" --inputbox "Enter the default gateway IPv4 address for ${interface_types[$s]} interface $s:" 10 60 "$default_gateway" 3>&1 1>&2 2>&3)
		check_valid_ipv4 $default_gateway
		if [ $? == 0 ]; then
			valid_ip=true
		else
			whiptail --title "$TITLE" --msgbox "Invalid default gateway IPv4 address, please try again." 8 78 3>&1 1>&2 2>&3
		fi
	done
	ipv4_gw["$s"]=$default_gateway

	valid_ip=false
	until [ $valid_ip == true ]
	do
		ip_addr=$(whiptail --title "$title" --inputbox "Enter the IPv4 address for ${interface_types[$s]} interface $s:" 10 60 "$ip_subnet." 3>&1 1>&2 2>&3)
		check_valid_ipv4 $ip_addr
		if [ $? == 0 ]; then
			valid_ip=true
			assigned=$(check_addr_assigned "$ip_addr")
			if [ $? != 0 ]; then
				whiptail --title "$TITLE" --msgbox "The IPv4 address $ip_addr has already been assigned to the network interface $assigned. Please enter a different address." 10 40 3>&1 1>&2 2>&3
				valid_ip=false
				continue
			fi
			if [ -f $pingtest_retcode_file ]; then
			        rm $pingtest_retcode_file
			fi
			pingtest "$ip_addr" &
			PCT=0
			(
			while [ ! -f $pingtest_retcode_file ] && [ $PCT -le 100 ];
			do
				PCT=`expr $PCT + 10`;
				echo $PCT;
				sleep 1;
			done; ) | whiptail --title "$TITLE" --gauge "Verifying that the IPv4 address $ip_addr is not in use" 8 70 0
			retcode=$(cat $pingtest_retcode_file)
			if [ $retcode == 0 ]; then
				whiptail --title "$TITLE" --yesno --yes-button "Back" --no-button "Continue" "The IPv4 address $ip_addr appears to be in use. Choose 'Back' to enter a different IPv4 address, or 'Continue' to ignore this warning." 8 78
				if [ $? == 0 ]; then
					valid_ip=false
				else
					valid_ip=true
				fi
			fi
			if [ valid_ip == true ]; then
				echo "GOOD IP YAY"
				exit 0
				interface_ipv4_addrs["$s"]=$ip_addr
			fi
		else
			whiptail --title "$TITLE" --msgbox "Invalid IPv4 address, please try again." 8 40 3>&1 1>&2 2>&3
		fi
	done
	interface_ipv4_addrs["$s"]="$ip_addr"

	if [ "${supports_netns[$s]}" == "true" ]; then
		whiptail --title "$TITLE" --msgbox "The interface $s will be moved to the network namespace ns_$s." 8 60 3>&1 1>&2 2>&3
		interface_namespaces["$s"]="ns_$s"
	else
		whiptail --title "$TITLE" --msgbox "This interface does not support switching network namespaces. It will be left in the root network namespace." 10 60 3>&1 1>&2 2>&3
		interface_namespaces["$s"]="root"
	fi

	good_alias=false
	until [ $good_alias == true ]
	do
		if_alias=$(whiptail --title "$TITLE" --inputbox "Enter an alias for the ${interface_types[$s]} interface $s, e.g. if_lan1, if_2.4GHz, if_5GHz. This alias will be used on the daily report to make identifying the interfaces easier for the reader." 10 78 3>&1 1>&2 2>&3)
		if [[ $if_alias =~ ^[A-Za-z_.0-9-]+$ ]]; then
			good_alias=true
			interface_aliases["$s"]="$if_alias"
		else
			good_alias=false
			whiptail --title "$TITLE" --msgbox "Invalid alias, please enter an alias with valid characters." 8 60 3>&1 1>&2 2>&3
		fi
	done
done

###### wpa_supplicant configuration for wireless interfaces

show_wifi_config_msg=true
# configure wpa_supplicant for any wireless interfaces
for s in "${selected[@]}"
do
	if [ "${interface_types[$s]}" == "wireless" ]; then
		if [[ "$show_wifi_config_msg" == true ]]; then
			whiptail --title "$TITLE" --msgbox "The script will now connect the wireless interfaces to their respective wireless networks. You will be prompted to select a wireless network and to enter the corresponding passphrase for each network." 12 60 3>&1 1>&2 2>&3
			show_wifi_config_msg=false
		fi
		$APPLICATION_PATH/setup_wifi.sh "$s"
	fi
done

# write the configuration info to a JSON file
echo "{" > $OUTPUT_FILE
echo "	\"configure_interfaces\" : true," >> $OUTPUT_FILE
echo "	\"test_exec_namespace\" : \"${interface_namespaces[$test_execution_interface]}\"," >> $OUTPUT_FILE
echo "	\"interfaces\" : {" >> $OUTPUT_FILE
for i in "${selected[@]}"
do
	echo "		\"$i\" : {" >> $OUTPUT_FILE
	echo "			\"type\" : \"${interface_types[$i]}\"," >> $OUTPUT_FILE
	if [[ "${interface_types[$i]}" == "wireless" ]]; then
		echo "			\"wpa_supplicant_config\" : \"/etc/wpa_supplicant/$i.conf\"," >> $OUTPUT_FILE
	fi
	echo "			\"ipv4_addr\" : \"${interface_ipv4_addrs[$i]}\"," >> $OUTPUT_FILE
	echo "			\"ipv4_gw\" : \"${ipv4_gw[$i]}\"," >> $OUTPUT_FILE
	echo "			\"namespace\" : \"${interface_namespaces[$i]}\"," >> $OUTPUT_FILE
	echo "			\"alias\" : \"${interface_aliases[$i]}\"" >> $OUTPUT_FILE
	if [[ "${selected[-1]}" == "$i" ]]; then
	echo "		}" >> $OUTPUT_FILE
	else
	echo "		}," >> $OUTPUT_FILE
	fi
done
echo "	}," >> $OUTPUT_FILE

echo "	\"bandwidth_monitor_bridge\" : {" >> $OUTPUT_FILE
if [[ "$configure_bwmonitor" == true ]]; then
	echo "		\"configure\" : true," >> $OUTPUT_FILE
	echo "		\"namespace\" : \"bwmonitor\"," >> $OUTPUT_FILE
	echo "		\"bridge_name\" : \"bwmonitor\"," >> $OUTPUT_FILE
	echo "		\"modem_interface\" : \"$upstream_interface\"," >> $OUTPUT_FILE
	echo "		\"router_interface\" : \"$downstream_interface\"" >> $OUTPUT_FILE
else
	echo "		\"configure\" : false" >> $OUTPUT_FILE
fi
echo "	}" >> $OUTPUT_FILE
echo "}" >> $OUTPUT_FILE

whiptail --title "$TITLE" --msgbox "The network interface configuration process is now complete.\nThe configuration info has been saved to:\n$OUTPUT_FILE" 10 70 3>&1 1>&2 2>&3

# validate configuration file JSON format
parser_output=$(python -m json.tool "$OUTPUT_FILE" 2>&1) > /dev/null
if [[ $? -ne 0 ]]; then
	echo "An error occurred when validating the generated configuration file. Please inspect the file for errors."
	echo "The error message generated by the parser is:"
	echo "$parser_output"
else
	echo "The generated configuration file was parsed successfully."
fi

