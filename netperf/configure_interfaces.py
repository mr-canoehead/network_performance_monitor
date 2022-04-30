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

username = NETPERF_SETTINGS.get_username()

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
	print ("This script must be run as root.\nPlease try again using 'sudo'.")
	critical_error ("This script must be run as root.\nPlease try again using 'sudo'.")

# read the interface configuration JSON file
configure_log.info("Network Perormance Monitor interface configuration\nReading interfaces file {}".format(INTERFACES_FILE))

with open(INTERFACES_FILE,"r+") as json_file:
	interface_info = json.load(json_file)
	if (interface_info["configure_interfaces"] == False) and (FORCE_CONFIGURE == False):
		configure_log.debug("Interface configuration is disabled. Nothing to do, exiting.")
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
bridge_info = interface_info["bandwidth_monitor_bridge"]
if bridge_info["configure"] == True:
	configure_log.info("Configuring the bandwidth monitoring bridge")
	bridge_namespace = bridge_info["namespace"]
	bridge_name = bridge_info["bridge_name"]
	modem_interface = bridge_info["modem_interface"]
	router_interface = bridge_info["router_interface"]

	# add network namespace for the bridge
	configure_log.debug("adding network namespace for the bridge")
	os.system("/sbin/ip netns add {}".format(bridge_namespace))
	cmd_prefix = "/sbin/ip netns exec {} ".format(bridge_namespace)

	# move interfaces to new namespace
	configure_log.debug("moving modem (upstream) interface {} to network namespace {}".format(modem_interface,bridge_namespace))
	exit_code = os.system("ip link set {} netns {}".format(modem_interface,bridge_namespace))
	if exit_code != 0:
		configure_log.critical("failed to move interface {} to network namespace {}".format(modem_interface,bridge_namespace))
	configure_log.debug("moving router (downstream) interface {} to network namespace {}".format(router_interface,bridge_namespace))
	exit_code = os.system("ip link set {} netns {}".format(router_interface,bridge_namespace))
	if exit_code != 0:
		configure_log.critical("failed to move interface {} to network namespace {}".format(router_interface,bridge_namespace))

	# create the bridge interface
	configure_log.debug("creating bridge interface {}".format(bridge_name))
	os.system("{} ip link add name {} type bridge".format(cmd_prefix,bridge_name))

	# add network interfaces to the bridge
	configure_log.debug("adding modem (upstream) interface {} to bridge".format(modem_interface))
	os.system("{} ip link set {} master {}".format(cmd_prefix,modem_interface,bridge_name))
	configure_log.debug("adding router (downstream) interface {} to bridge".format(router_interface))
	os.system("{} ip link set {} master {}".format(cmd_prefix,router_interface,bridge_name))

	# bring up the bridge interfaces
	configure_log.debug("bringing up bridge interfaces")
	os.system("{} ip link set {} up".format(cmd_prefix,modem_interface))
	os.system("{} ip link set {} up".format(cmd_prefix,router_interface))
	os.system("{} ip link set {} up".format(cmd_prefix,bridge_name))

	# start the bandwidth monitoring daemon
	configure_log.debug("starting the bandwidth monitoring daemon")
	os.system("{} /sbin/runuser -l {} -c 'python3 /opt/netperf/bwmonitor.py -i {}'".format(cmd_prefix,username,modem_interface))
	configure_log.info("bandwidth monitoring bridge configuration is complete")
else:
	configure_log.info("Bandwidth monitoring is disabled.")

#### Configure the performance testing interfaces
configure_log.info("Configuring the performance testing interfaces")
root_namespace_interfaces = 0
for interface in network_interfaces:
	if_details = network_interfaces[interface]

	# check if namespace exists already (i.e. this script has already been run)
	if os.system("/sbin/ip netns list | /bin/grep {} > /dev/null".format(interface)) == 0:
		configure_log.error("Network namespace exists for interface {}, the interface has already been configured on this system.\n To reconfigure the interfaces, refer to the \"Reconfigure the network interfaces\" page of the project Wiki".format(interface))
		sys.exit(1)
	# check if interface exists
	if not os.path.exists(IF_INFO_PATH + "/" + interface):
		configure_log.critical("Can't find interface {} in {}".format(interface,IF_INFO_PATH))
		sys.exit(1)
	if if_details['type'] == 'wireless':
		if not os.path.exists("{}/{}/phy80211".format(IF_INFO_PATH,interface)):
			configure_log.critical("{} does not appear to be a wireless network interface, please verify the interface configuration file.".format(interface))
			sys.exit(1)
		else:
			if if_details['namespace'] is not None and (if_details['namespace'] not in ("root", "default")):
				# check if interface supports switching network namespace
				with open("/sys/class/net/{}/phy80211/name".format(interface), 'r') as file:
					if_details['phy_name'] = file.read().replace('\n', '')
					#cmd = "/sbin/iw phy {} info | /bin/grep netns".format(if_details['phy_name']))
					if os.system("/sbin/iw phy {} info | /bin/grep netns > /dev/null".format(if_details['phy_name'])) != 0:
						configure_log.critical("Wireless interface {} is configured to use its own network namespace, but its driver does not support the set_wiphy_netns command required to do so. Please verify the interface configuration file.".format(interface))
						sys.exit(1)

		#wpa_supplicant_config = CONFIG_PATH + "/wpa_supplicant_" + interface + ".conf"
		if not os.path.isfile(if_details["wpa_supplicant_config"]):
			configure_log.critical("Missing wpa_supplicant configuration file {} for wireless interface {}.".format(if_details["wpa_supplicant_config"],interface))
			sys.exit(1)
	else:
		if os.path.exists("{}/{}/phy80211".format(IF_INFO_PATH,interface)):
			configure_log.critical("{} appears to be a wireless network interface, please verify the interface configuration file.".format(interface))
			sys.exit(1)
	if if_details['namespace'] is None:
		root_namespace_interfaces += 1

if root_namespace_interfaces == 0:
	warn ("No interfaces will be configured in the root namespace. The network will not be reachable from the console shell. To access the network you will need to switch to a namespace with a configured interface.")

if root_namespace_interfaces > 1:
	warn ("More than one interface is configured in the root namespace. Performance tests between these interfaces will communicate via the loopback adapter, and so will report innacurate (artificially fast) results.")

warn ("The network interfaces are being reconfigured, if you are connected via ssh your session will disconnect or hang.\nTo terminate a ssh session that has hung, type the key sequence <Enter><Tilde><Dot> (The 'Enter' key, then the '~' key, then the '.' key.)\nTo reconnect, ssh to one of the configured namespace IP addresses, or to the address of the interface in the root namespace.")

configure_log.info("Configuring interfaces for network performance monitoring:")

for interface in network_interfaces:
	if_details = network_interfaces[interface]
	configure_log.info("Configuring {} interface {}".format(if_details['type'],interface))
	if if_details['namespace'] is not None and (if_details['namespace'] not in ("root", "default")):
		configure_log.debug("Adding network namespace {}".format(if_details['namespace']))
		os.system("/sbin/ip netns add {}".format(if_details['namespace']))
		cmd_prefix = "/sbin/ip netns exec {} ".format(if_details['namespace'])
		configure_log.debug("Moving interface {} to network namespace {}".format(interface,if_details['namespace']))
		if if_details['type'] == 'wireless':
			#with open('/sys/class/net/' + interface + "/phy80211/name", 'r') as file:
    			#	phy_name = file.read().replace('\n', '')
			exit_code = os.system("/sbin/iw phy {} set netns name {}".format(if_details['phy_name'],if_details['namespace']))
			if exit_code != 0:
				configure_log.critical("Unable to change network namespace of wireless interface {}".format(interface))
				sys.exit(1)
		else:
			exit_code = os.system("/sbin/ip link set {} netns {}".format(interface,if_details['namespace']))
			if exit_code != 0:
				configure_log.critical("Unable to change network namespace of ethernet interface {}".format(interface))
				sys.exit(1)
	else:
		configure_log.debug("Leaving interface {} in the root network namespace".format(interface))
		if_details['namespace'] = "root"
		cmd_prefix = ""

	configure_log.debug("Bringing up interface {} in network namespace {}".format(interface,if_details['namespace']))
	exit_code = os.system("{} /sbin/ip link set dev {} up".format(cmd_prefix,interface))
	if exit_code != 0:
		configure_log.critical("Unble to bring up interface {}".format(interface))
		sys.exit(1)

	configure_log.debug("Configuring IPv4 address for interface {}".format(interface))
	exit_code = os.system("{} /sbin/ip address add {}/24 dev {}".format(cmd_prefix,if_details['ipv4_addr'],interface))
	if exit_code != 0:
		configure_log.critical("Unable to assign IPv4 address for interface {}".format(interface))

	configure_log.debug("Configuring IPv4 default gateway for interface {}".format(interface))
	exit_code = os.system("{} /sbin/ip route replace default via {} dev {}".format(cmd_prefix,if_details['ipv4_gw'],interface))
	if exit_code != 0:
		configure_log.critical("Unable to add default gateway for interface {}".format(interface))
		sys.exit(1)
	if if_details['type'] == "wireless":
		command_path=shutil.which("rfkill")
		if command_path is not None:
			configure_log.debug("Unblocking wifi interface")
			os.system("{} unblock wifi".format(command_path))
		configure_log.debug("Connecting interface to its wireless network")
		wpa_supplicant_prefix = "wpa_supplicant-{}".format(interface)
		exit_code = os.system("{} /sbin/wpa_supplicant -B -P {}/{}.pid -c {} -i {}".format(cmd_prefix,RUN_PATH,wpa_supplicant_prefix,if_details["wpa_supplicant_config"],interface))
		if exit_code != 0:
			configure_log.critical("Unable to connect interface {} to its wireless network".format(interface))
			sys.exit(1)
	configure_log.info("Starting ssh daemon for interface {}".format(interface))
	os.system ("{} /usr/sbin/sshd -o PidFile={}/sshd-{}.pid".format(cmd_prefix,RUN_PATH,interface))
	configure_log.info("Starting iperf3 server daemon in netowrk namespace {}".format(if_details['namespace']))
	os.system("{} /usr/bin/iperf3 -D -s -i 1 --pidfile {}/iperf3-{}.pid > /tmp/{}_iperf3.log".format(cmd_prefix,RUN_PATH,interface,interface))
	#os.system("/bin/sed -i " +"\"/" + if_details['alias'] + "/d\"" + " /etc/hosts")
	os.system("/bin/sed -i \"/{}/d\" /etc/hosts".format(if_details['alias']))

	configure_log.debug("Adding interface alias to /etc/hosts")
	with open("/etc/hosts","a") as hosts_file:
		hosts_file.write("{}        {}\n".format(if_details['ipv4_addr'],if_details['alias']))
		configure_log.debug("{}        {}".format(if_details['ipv4_addr'],if_details['alias']))

configure_log.info("Network interfaces have been configured.\nYou can access the interfaces from another computer via ssh using their IP addresses as follows:")
configure_log.info("IPv4 address        Interface")
for interface in network_interfaces:
	configure_log.info("{}        {}".format(network_interfaces[interface]['ipv4_addr'],interface))
	configure_log.info("\nExample usage:\nOn another computer, run an iperf3 test like this:")
	test_if = next(iter(network_interfaces))
	test_if_details = network_interfaces[test_if]
	configure_log.info("iperf3 -c {}".format(test_if_details['ipv4_addr']))
	configure_log.info("This will test the {} interface {} on this server.".format(test_if_details['type'],test_if))
	configure_log.info("\nYou can switch to a network namespace using the following command:\nsudo ip netns exec <namespace name> bash -c \"su pi\"\ne.g.:\nsudo ip netns exec ns_wlan0 bash -c \"su pi\"")
