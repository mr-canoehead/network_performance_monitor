#!/usr/bin/env python3
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

# This script configures network interfaces and network namespaces
# for the Network Performance Monitor. Its input is a JSON file containing
# details of the various network interfaces and network namespaces used
# by the system. In normal operation it is invoked via an entry in rc.local

import os
import json
import sys
import logging
import shutil
from netperf_settings import netperf_settings


class bcolors:
	FAIL = '\033[91m'
	WARNING = '\033[93m'
	ENDC = '\033[0m'

# Interface info path
IF_INFO_PATH="/sys/class/net"

# JSON file containing interface configuration info
CONFIG_PATH="/opt/netperf/config"
INTERFACES_FILE=CONFIG_PATH + "/interfaces.json"
RUN_PATH="/run/netperf"
FORCE_CONFIGURE = False
DISABLE_CONFIGURE = False
NETPERF_SETTINGS = netperf_settings()

logging.basicConfig(filename=NETPERF_SETTINGS.get_log_filename(), format=NETPERF_SETTINGS.get_logger_format())
configure_log = logging.getLogger("configure_interfaces")
configure_log.setLevel(NETPERF_SETTINGS.get_log_level())

if len(sys.argv) > 1:
	arg = str(sys.argv[1])
	if (arg == "-f") or (arg == "--force"):
		FORCE_CONFIGURE = True
	else:
		if (arg == "-n") or (arg == "--no-config"):
			DISABLE_CONFIGURE = True

def critical_error (error_str):
	print(bcolors.FAIL + "\nERROR: " + error_str + "\n" + bcolors.ENDC)
	os._exit(0)

def warn (warning_str):
	print(bcolors.WARNING + "\nWARNING: " + warning_str + "\n"+ bcolors.ENDC)


#### Do some sanity checks before configuring the interfaces:

# Make sure we're running as root
if os.geteuid() != 0:
	critical_error ("This script must be run as root.\nPlease try again using 'sudo'.")

# read the interface configuration JSON file
print ("Reading interfaces file " + INTERFACES_FILE)

with open(INTERFACES_FILE,"r+") as json_file:
	interface_info = json.load(json_file)
	if (interface_info["configure_interfaces"] == False) and (FORCE_CONFIGURE == False):
		# Nothing to do, exit
		sys.exit(0)
	else:
		if DISABLE_CONFIGURE == True:
			interface_info["configure_interfaces"] = False
			json_file.seek(0)
			json.dump(interface_info, json_file, indent=4)
			json_file.truncate()
			sys.exit(0)
		else:
			network_interfaces = interface_info["interfaces"]
	json_file.close()

#### Configure the bandwidth monitoring bridge
print ("Configuring the bandwidth monitoring bridge...")
bridge_info = interface_info["bandwidth_monitor_bridge"]
if bridge_info["configure"] == True:
	bridge_namespace = bridge_info["namespace"]
	bridge_name = bridge_info["bridge_name"]
	modem_interface = bridge_info["modem_interface"]
	router_interface = bridge_info["router_interface"]

	# add network namespace for the bridge
	os.system("/sbin/ip netns add {}".format(bridge_namespace))
	cmd_prefix = "/sbin/ip netns exec {} ".format(bridge_namespace)

	# move interfaces to new namespace
	os.system("ip link set {} netns {}".format(modem_interface,bridge_namespace))
	os.system("ip link set {} netns {}".format(router_interface,bridge_namespace))

	# create the bridge interface
	os.system("{} ip link add name {} type bridge".format(cmd_prefix,bridge_name))

	# add network interfaces to the bridge
	os.system("{} ip link set {} master {}".format(cmd_prefix,modem_interface,bridge_name))
	os.system("{} ip link set {} master {}".format(cmd_prefix,router_interface,bridge_name))

	# bring up the bridge interfaces
	os.system("{} ip link set {} up".format(cmd_prefix,modem_interface))
	os.system("{} ip link set {} up".format(cmd_prefix,router_interface))
	os.system("{} ip link set {} up".format(cmd_prefix,bridge_name))

	# start the bandwidth monitoring daemon
	os.system("{} /sbin/runuser -l pi -c 'python3 /opt/netperf/bwmonitor.py -i {}'".format(cmd_prefix,modem_interface))

#### Configure the performance testing interfaces
print ("Configuring the performance testing interfaces...")
root_namespace_interfaces = 0
for interface in network_interfaces:
	if_details = network_interfaces[interface]

	# check if namespace exists already (i.e. this script has already been run)
	if os.system("/sbin/ip netns list | /bin/grep " + interface + " > /dev/null") == 0:
		critical_error("A network namespace already exists for interface " + interface + ", please reboot if you need to reconfigure the interfaces.")

	# check if interface exists
	if not os.path.exists(IF_INFO_PATH + "/" + interface):
		critical_error("Can't find interface " + interface + " in " + IF_INFO_PATH + ". Double-check the configuration at the top of this script.")

	if 'namespace' not in if_details:
		if_details['namespace'] = "root"
		print(interface + " has no configured namespace, defaulting to 'root')
		
	if if_details['type'] == 'wireless':
		if not os.path.exists(IF_INFO_PATH + "/" + interface + "/phy80211"):
			critical_error(interface + " does not appear to be a wireless network interface, please verify the interface configuration file.")
		else:
			if if_details['namespace'] is not None and (if_details['namespace'] not in ("root", "default")):
				# check if interface supports switching network namespace
				with open('/sys/class/net/' + interface + "/phy80211/name", 'r') as file:
					if_details['phy_name'] = file.read().replace('\n', '')
					cmd = "/sbin/iw phy " + if_details['phy_name'] + " info | /bin/grep netns"
					if os.system("/sbin/iw phy " + if_details['phy_name'] + " info | /bin/grep netns > /dev/null") != 0:
							critical_error("Wireless interface " + interface + " is configured to use its own network namespace, but its driver does not support the set_wiphy_netns command required to do so. Please verify the interface configuration file.")

		#wpa_supplicant_config = CONFIG_PATH + "/wpa_supplicant_" + interface + ".conf"
		if not os.path.isfile(if_details["wpa_supplicant_config"]):
			critical_error("Missing wpa_supplicant configuration file " + if_details["wpa_supplicant_config"] + " for wireless interface " + interface)
	else:
		if os.path.exists(IF_INFO_PATH + "/" + interface + "/phy80211"):
			critical_error(interface + " appears to be a wireless network interface, please verify the interface configuration file.")
	if if_details['namespace'] is None:
		root_namespace_interfaces += 1

if root_namespace_interfaces == 0:
	warn ("No interfaces will be configured in the root namespace. The network will not be reachable from the console shell. To access the network you will need to switch to a namespace with a configured interface.")

if root_namespace_interfaces > 1:
	warn ("More than one interface is configured in the root namespace. Performance tests between these interfaces will communicate via the loopback adapter, and so will report innacurate (artificially fast) results.")

warn ("The network interfaces are being reconfigured, if you are connected via ssh your session will disconnect or hang.\nTo terminate a ssh session that has hung, type the key sequence <Enter><Tilde><Dot> (The 'Enter' key, then the '~' key, then the '.' key.)\nTo reconnect, ssh to one of the configured namespace IP addresses, or to the address of the interface in the root namespace.")

print("Configuring interfaces for network performance monitoring:\n")

for interface in network_interfaces:
	if_details = network_interfaces[interface]
	print("Configuring " + if_details['type'] + " interface " + interface)
	if if_details['namespace'] is not None and (if_details['namespace'] not in ("root", "default")):
		print("Adding network namespace " + if_details['namespace'])
		os.system("/sbin/ip netns add " + if_details['namespace'])
		cmd_prefix = "/sbin/ip netns exec " + if_details['namespace'] + " "
		print("Moving interface " + interface + " to network namespace " + if_details['namespace'])
		if if_details['type'] == 'wireless':
			#with open('/sys/class/net/' + interface + "/phy80211/name", 'r') as file:
    			#	phy_name = file.read().replace('\n', '')
			exit_code = os.system("/sbin/iw phy " + if_details['phy_name'] + " set netns name " + if_details['namespace'])
			if exit_code != 0:
				critical_error("Unable to change network namespace of wireless interface " + interface)
		else:
			exit_code = os.system(" /sbin/ip link set " + interface + " netns " + if_details['namespace'])
			if exit_code != 0:
				critical_error("Can't change network namespace of ethernet interface " + interface + ", its driver may not support this function")
	else:
		print("Leaving interface in the root network namespace")
		if_details['namespace'] = "root"
		cmd_prefix = ""

	print("Bringing up interface " + interface + " in " + if_details['namespace'])
	exit_code = os.system(cmd_prefix + "/sbin/ip link set dev " + interface + " up")
	if exit_code != 0:
		critical_error("Unble to bring up interface " + interface)

	print("Configuring IPv4 address for interface " + interface)
	exit_code = os.system(cmd_prefix + "/sbin/ip address add " + if_details['ipv4_addr'] + "/24 dev " + interface)
	if exit_code != 0:
		critical_error("Unble to assign IPv4 address for interface " + interface)

	print("Configuring IPv4 default gateway for interface " + interface)
	exit_code = os.system(cmd_prefix + "/sbin/ip route replace default via " + if_details['ipv4_gw'] + " dev " + interface)
	if exit_code != 0:
		critical_error("Unble to add default gateway for interface " + interface)
	if if_details['type'] == "wireless":
		command_path=shutil.which("rfkill")
		if command_path is not None:
			os.system("{} unblock wifi".format(command_path))
		print("Connecting interface to its wireless network")
		wpa_supplicant_prefix = "wpa_supplicant-" + interface
		exit_code = os.system(cmd_prefix+ "/sbin/wpa_supplicant -B -P " + RUN_PATH + "/" + wpa_supplicant_prefix + ".pid   -c " + if_details["wpa_supplicant_config"] + " -i " + interface)
		if exit_code != 0:
			critical_error("Unble to connect interface " + interface + " to the wireless network")

	os.system (cmd_prefix + "/usr/sbin/sshd -o PidFile=" + RUN_PATH + "/sshd-" + interface + ".pid")
	print ("Starting iperf3 server daemon in " + if_details['namespace'] + " namespace")
	os.system(cmd_prefix + "/usr/bin/iperf3 -D -s -i 1 --pidfile " + RUN_PATH + "/iperf3-" + interface + ".pid > /tmp/" + interface + "_iperf3.log")
	os.system("/bin/sed -i " +"\"/" + if_details['alias'] + "/d\"" + " /etc/hosts")
	print ("Adding interface alias to /etc/hosts:")
	with open("/etc/hosts","a") as hosts_file:
		hosts_file.write(if_details['ipv4_addr'] + "	" + if_details['alias'] + "\n")
		print (if_details['ipv4_addr'] + "	" + if_details['alias'] + "\n\n")

print ("Network interfaces have been configured.")
print ("You can access the interfaces from another computer via ssh using their IP addresses as follows:\n")
print ("IPv4 address	Interface")
for interface in network_interfaces:
	print (network_interfaces[interface]['ipv4_addr'] + "	" + interface)
	print ("\nExample usage:")
	print ("On another computer, run an iperf3 test like this:")
	test_if = next(iter(network_interfaces))
	test_if_details = network_interfaces[test_if]
	print ("iperf3 -c " + test_if_details['ipv4_addr'])
	print ("This will test the " + test_if_details['type'] + " interface " + test_if + " on this computer.")

	print ("\nYou can switch to a network namespace using the following command:\nsudo ip netns exec <namespace name> bash -c \"su pi\"\ne.g.:\nsudo ip netns exec ns_wlan0 bash -c \"su pi\"")
