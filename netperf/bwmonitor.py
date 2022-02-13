#!/usr/bin/env python3
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

# This script runs a daemon which measures traffic on a network interface
# and sends RX/TX bits-per-second readings to the Network Performance Monitor database

import sys
import daemon
import json
import time
import getopt,sys
import util
import logging
from netperf_db import db_queue
from netperf_settings import netperf_settings

NETPERF_SETTINGS = netperf_settings()

logging.basicConfig(filename=NETPERF_SETTINGS.get_log_filename(), format=NETPERF_SETTINGS.get_logger_format())
bwmonitor_log = logging.getLogger('bwmonitor')
bwmonitor_log.setLevel(NETPERF_SETTINGS.get_log_level())

def bwmonitor(interface):
	client_id = util.get_client_id()
	os_word_size = 64 if sys.maxsize > 2**32 else 32
	MAXUINT = (2 ** os_word_size) - 1
	STATS_PATH="/sys/class/net/{}/statistics".format(interface)
	try:
		rx_bytes_file = open("{}/rx_bytes".format(STATS_PATH))
	except:
		sys.exit(2)
	try:
		tx_bytes_file = open("{}/tx_bytes".format(STATS_PATH))
	except:
		sys.exit(2)
	last_rx_bytes = None
	last_tx_bytes = None
	last_time = None
	dbq = db_queue()
	while True:
		loop_start_time = time.time()
		rx_bytes_file.seek(0)
		rx_bytes = int(rx_bytes_file.read().strip())
		tx_bytes_file.seek(0)
		tx_bytes = int(tx_bytes_file.read().strip())
		if last_time is not None:
			rx_bytes_delta = rx_bytes - last_rx_bytes if rx_bytes >= last_rx_bytes else MAXUINT - last_rx_bytes + rx_bytes + 1
			tx_bytes_delta = tx_bytes - last_tx_bytes if tx_bytes >= last_tx_bytes else MAXUINT - last_tx_bytes + tx_bytes + 1
			time_delta = loop_start_time - last_time
			rx_bps = float(rx_bytes_delta * 8) / time_delta
			tx_bps = float(tx_bytes_delta * 8) / time_delta
			bw_data = { "type" : "bandwidth", \
						"data" : {  "client_id" : client_id, \
						"timestamp" : loop_start_time, \
						"rx_bytes" : rx_bytes_delta, \
						"tx_bytes" : tx_bytes_delta, \
						"rx_bps" : rx_bps, \
						"tx_bps" : tx_bps}
			}
			dbq.write(bw_data)
		last_time = loop_start_time
		last_rx_bytes = rx_bytes
		last_tx_bytes = tx_bytes

		# sleep off remaining time
		sleeptime = 1.0 - (time.time() - loop_start_time)
		if (sleeptime > 0):
			try:
				time.sleep (sleeptime)
			except:
				pass

if __name__ == '__main__':
	bwmonitor_log.debug("__main__")
	fullCmdArguments = sys.argv
	argumentList = fullCmdArguments[1:]
	unixOptions = "i:l:"
	gnuOptions = ["interface=","loglevel="]

	try:
		arguments, values = getopt.getopt(argumentList, unixOptions, gnuOptions)
	except getopt.error as err:
		    # output error, and return with an error code
			bwmonitor_log.error(str(err))
			sys.exit(2)

	interface = None
	bwmonitor_log.debug("Processing argument list...")
	for currentArgument, currentValue in arguments:
		if currentArgument in ("-i", "--interface"):
			interface = currentValue
		if currentArgument in ("-l", "--loglevel"):
			loglevel = currentValue.lower
			if loglevel == "debug":
				bwmonitor_log.setLevel(logging.DEBUG)
			if loglevel == "info":
				bwmonitor_log.setLevel(logging.INFO)
			if loglevel == "warning":
				bwmonitor_log.setLevel(logging.WARNING)
			if loglevel == "error":
				bwmonitor_log.setLevel(logging.ERROR)
			if loglevel == "critical":
				bwmonitor_log.setLevel(logging.CRITICAL)
	bwmonitor_log.debug("Watching interface: {}".format(interface))
	if interface == None:
		print ("Error: an interface is required.")
		bwmonitor_log.error("An interface is required.")
		sys.exit(2)

	daemon_context = daemon.DaemonContext()
	with daemon_context:
		bwmonitor(interface)






