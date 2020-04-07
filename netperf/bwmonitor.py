#!/usr/bin/env python
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

logging.basicConfig(filename='/mnt/usb_storage/netperf/log/netperf.log',level=logging.ERROR)
logging.basicConfig(filename='/tmp/netperf.log',level=logging.ERROR)
bwmonitor_log = logging.getLogger('netperf.bwmonitor')
bwmonitor_log = logging.getLogger('bwmonitor')

def bwmonitor(interface):
	client_id = util.get_client_id()

	MAX_32UINT = (2 ** 32) - 1
	STATS_PATH="/sys/class/net/{}/statistics".format(interface)

	try:
		rx_bytes_file = open("{}/rx_bytes".format(STATS_PATH))
	except:
		bwmonitor_log.critical("Unable to open stats file for interface {}".format(interface))
		sys.exit(2)
	try:
		tx_bytes_file = open("{}/tx_bytes".format(STATS_PATH))
	except:
		bwmonitor_log.critical("Unable to open stats file for interface {}".format(interface))
		sys.exit(2)

	last_rx_bytes = None
	last_tx_bytes = None
	last_time = None

	dbq = db_queue()

	while True:
        	loop_start_time = time.time()
        	rx_bytes_file.seek(0)
        	rx_bytes = long(rx_bytes_file.read().strip())
        	tx_bytes_file.seek(0)
        	tx_bytes = long(tx_bytes_file.read().strip())
        	if last_time is not None:
	                if last_rx_bytes > rx_bytes:
        	                # rollover occurred
				bwmonitor_log.debug("Rollover on rx_bytes")
                        	rx_bytes_delta = rx_bytes + (MAX_32UINT - last_rx_bytes)
          	 	else:
                	        rx_bytes_delta = rx_bytes - last_rx_bytes
               		if last_tx_bytes > tx_bytes:
                        	# rollover occurred
				bwmonitor_log.debug("Rollover on tx_bytes")
                        	tx_bytes_delta = tx_bytes + (MAX_32UINT - last_tx_bytes)
                	else:
                        	tx_bytes_delta = tx_bytes - last_tx_bytes
                	time_delta = loop_start_time - last_time
                	rx_bps = float(rx_bytes_delta * 8) / time_delta
                	tx_bps = float(tx_bytes_delta * 8) / time_delta
			bwmonitor_log.debug("rx_Mbps: {} tx_Mbps: {}".format(round(rx_bps/1e6,2),round(tx_bps/1e6,2)))
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
	if interface == None:
		bwmonitor_log.error("An interface is required.")
		sys.exit(2)

	with daemon.DaemonContext():
    		bwmonitor(interface)






