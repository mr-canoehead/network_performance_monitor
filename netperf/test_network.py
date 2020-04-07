#!/usr/bin/env python
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.


import os
import json
from subprocess import check_output,Popen,STDOUT,PIPE
import sys
import util
import time
from netperf_db import db_queue
import logging

client_id = util.get_client_id()

logging.basicConfig(filename='/mnt/usb_storage/netperf/log/netperf.log',level=logging.INFO)
test_log = logging.getLogger('netperf.test_network')
test_log.setLevel(logging.INFO)

#logging.basicConfig(filename='netperf.log',level=logging.DEBUG)
#logger = logging.getLogger('netperf.test_network')

def pingtest(test_exec_namespace,remote_host,dbq):
	if test_exec_namespace is not None:
		cmd_prefix = "sudo ip netns exec {} ".format(test_exec_namespace)
	else:
		cmd_prefix = ""
	cmd = "{}ping -c 10 {} | tail -1| awk '{{print $4}}'".format(cmd_prefix,remote_host)
	ps = Popen(cmd,shell=True,stdout=PIPE,stderr=STDOUT)
	ping_results = ps.communicate()[0]
	if len(ping_results) > 20:
		# successful ping test
		ping_stats = ping_results.strip().split('/')
		min = ping_stats[0]
		avg = ping_stats[1]
		max = ping_stats[2]
		mdev = ping_stats[3]
		pingtest_results=(client_id,time.time(),remote_host,min,avg,max,mdev)
	else:
		# ping test failed
		min = 0
		avg = 0
		max = 0
		mdev = 0
		pingtest_results=(client_id,time.time(),remote_host,0,0,0,0)

	p_results = {	"client_id" : client_id, \
			"timestamp" : time.time(), \
			"remote_host" : remote_host, \
			"min" : min, \
			"avg" : avg, \
			"max" : max, \
			"mdev" : mdev}
	db_data = {	"type" : "ping", \
			"data" : p_results}

	dbq.write(db_data)
	return pingtest_results

def test_local_network(test_exec_namespace, remote_host, dbq):
	test_log.info("Testing interface {}".format(remote_host))
	if test_exec_namespace is not None:
		cmd_prefix = "sudo ip netns exec {} ".format(test_exec_namespace)
	else:
		cmd_prefix = ""

	# Perform local network speed / ping tests
	cmd = "{}iperf3 --connect-timeout 5000 -c {} --json".format(cmd_prefix,remote_host)
	ps = Popen(cmd,shell=True,stdout=PIPE,stderr=STDOUT)
	json_str = ps.communicate()[0]
	if ps.returncode == 0:
		test_log.info("Successful iperf3 test.")
		# successful iperf3 test
		iperf3_json=json.loads(json_str)
		tx_Mbps=round(float(iperf3_json['end']['sum_sent']['bits_per_second'])/1e6,2)
		rx_Mbps=round(float(iperf3_json['end']['sum_received']['bits_per_second'])/1e6,2)
		retransmits=iperf3_json['end']['sum_sent']['retransmits']
		iperf3_results=(client_id,time.time(),remote_host,rx_Mbps,tx_Mbps,retransmits)
	else:
		# iperf3 test failed
		test_log.info("iperf3 test failed.")
		iperf3_results=(client_id,time.time(),remote_host,0,0,0)

	ip3_results = {	"client_id" : client_id, \
			"timestamp" : time.time(), \
			"remote_host" : remote_host, \
			"rx_Mbps" : rx_Mbps, \
			"tx_Mbps" : tx_Mbps, \
			"retransmits" : retransmits}
	db_data = {	"type" : "iperf3", \
			"data" : ip3_results}
	dbq.write(db_data)

	cmd = "{}ping -c 10 {} | tail -1| awk '{{print $4}}'".format(cmd_prefix,remote_host)
	ps = Popen(cmd,shell=True,stdout=PIPE,stderr=STDOUT)
	ping_results = ps.communicate()[0]
	if len(ping_results) > 20:
		# successful ping test
		ping_stats = ping_results.strip().split('/')
		min = ping_stats[0]
		avg = ping_stats[1]
		max = ping_stats[2]
		mdev = ping_stats[3]
		pingtest_results=(client_id,time.time(),remote_host,min,avg,max,mdev)
	else:
		# ping test failed
		pingtest_results=(client_id,time.time(),remote_host,0,0,0,0)


	db_data = { "type" : "ping",\
		    "data" : { \
				"client_id" : client_id, \
				"timestamp" : time.time(), \
				"remote_host" : remote_host, \
				"min" : min, \
				"avg" : avg, \
				"max" : max, \
				"mdev" : mdev} \
		  }

	dbq.write(db_data)

def test_isp(test_exec_namespace,dbq):
	test_log.info("Testing Internet speed...")
	if test_exec_namespace is not None:
		cmd_prefix = "sudo ip netns exec {} ".format(test_exec_namespace)
	else:
		cmd_prefix = ""
	cmd = "{}speedtest-cli --json".format(cmd_prefix)
	ps = Popen(cmd,shell=True,stdout=PIPE,stderr=STDOUT)
	json_str = ps.communicate()[0]
	if ps.returncode == 0:
		test_log.info("Successful speedtest.")
		# successful speedtest
		speedtest_json=json.loads(json_str)
		rx_Mbps=round(float(speedtest_json['download'])/1e6,2)
		tx_Mbps=round(float(speedtest_json['upload'])/1e6,2)
		ping = round(speedtest_json['ping'],2)
		remote_host=speedtest_json['server']['host']
		url=speedtest_json['server']['url']
		speedtest_results=(client_id,time.time(),rx_Mbps,tx_Mbps,remote_host,url,ping)
		test_status = True
	else:
		test_log.info("Speedtest failed.")
		# speedtest failed
		speedtest_results=(client_id,time.time(),0,0,"n/a","n/a",0)
		rx_Mbps = 0
		tx_Mbps = 0
		ping = 0
		remote_host = "n/a"
		url = "n/a"
		test_status = False
	st_data = { "type" : "speedtest", \
		    "data" : {  "client_id" : client_id, \
				"timestamp" : time.time(), \
				"rx_Mbps" : rx_Mbps, \
				"tx_Mbps" : tx_Mbps, \
				"remote_host" : remote_host, \
				"url" : url, \
				"ping" : ping}
                          }
	dbq.write(st_data)

	return test_status

def test_name_resolution(test_exec_namespace,dbq):
	test_log.info("Testing name resolution...")
	#logger.debug("Testing name resolution...")
	EXTERNAL_DNS_SERVERS=['8.8.8.8','8.8.4.4','1.1.1.1','9.9.9.9']
	if test_exec_namespace is not None:
		cmd_prefix = "sudo ip netns exec {} ".format(test_exec_namespace)
	else:
		cmd_prefix = ""
	internal_dns_ok = False
	external_dns_ok = False
	internal_dns_failures = 0
	external_dns_failures = 0
	internal_dns_query_time = 0
	external_dns_query_time = 0

	# try resolving names using local DNS
	cmd = "{}dig www.example.com +noall +stats".format(cmd_prefix)
	for i in range(5):
		print "Testing local DNS {}...".format(int(i))
		ps = Popen(cmd,shell=True,stdout=PIPE,stderr=STDOUT)
		cmd_output = ps.communicate()[0]
		if ps.returncode == 0:
			test_log.info("Internal DNS ok.")
			internal_dns_ok = True
			internal_dns_query_time = cmd_output.partition("Query time:")[2].split()[0]
			#print "Query time is: |{}| ".format(local_query_time)
			break
		else:
			test_log.info("Internal DNS failure.")
			internal_dns_failures += 1

	# try resolving names using external DNS
	for dns_server in EXTERNAL_DNS_SERVERS:
		cmd = "{}dig @{} www.example.com +noall +stats".format(cmd_prefix,dns_server)
		for i in range(5):
			print "Testing external DNS {} {}...".format(dns_server,int(i))
			ps = Popen(cmd,shell=True,stdout=PIPE,stderr=STDOUT)
			cmd_output = ps.communicate()[0]
			if ps.returncode == 0:
				test_log.info("External DNS ok.")
				external_dns_ok = True
				external_dns_query_time = cmd_output.partition("Query time:")[2].split()[0]
				#print "External query time is : |{}|".format(external_query_time)
				break
			else:
				test_log.info("External DNS failure.")
				external_dns_failures += 1
		if external_dns_ok == True:
			break
	dns_results=(client_id,time.time(),internal_dns_ok,internal_dns_query_time,internal_dns_failures,external_dns_ok,external_dns_query_time,external_dns_failures)
	dns_data = { "type" : "dns", \
		     "data" : { \
				"client_id" : client_id, \
				"timestamp" : time.time(), \
				"internal_dns_ok" : internal_dns_ok, \
				"internal_dns_query_time" : internal_dns_query_time, \
				"internal_dns_failures" : internal_dns_failures, \
				"external_dns_ok" : external_dns_ok, \
				"external_dns_query_time" : external_dns_query_time, \
				"external_dns_failures" : external_dns_failures
				} \
		    }
	dbq.write(dns_data)

	if internal_dns_ok == False or external_dns_ok == False:
		return False
	else:
		return True

def print_usage():
	print ("usage: {} <local|isp>".format(sys.argv[0]))

def main():
	if ((len(sys.argv) < 2) or (len(sys.argv) > 2)):
		print_usage()
		sys.exit(1)
	dbq = db_queue()

	with open("/opt/netperf/config/interfaces.json","r") as config_file:
		interface_info = json.load(config_file)
		test_exec_namespace = interface_info["test_exec_namespace"]
		if sys.argv[1] == 'local':
			interfaces = interface_info["interfaces"]
			for i in interfaces:
				if interfaces[i]["namespace"] != test_exec_namespace:
					test_local_network(test_exec_namespace, interfaces[i]["alias"],dbq)
		else:
			if sys.argv[1] == 'isp':
				test_ok = test_isp(test_exec_namespace,dbq)
				if not test_ok:
					# speedtest failed, test for an Internet outage outage
					ping_results = pingtest(test_exec_namespace,"8.8.8.8",dbq)
					(client_id,timestamp,remote_host,min,avg,max,mdev) = ping_results
					if min == 0 or max == 0:
						# log an outage
						outage_data = {"type": "isp_outage",\
								"data" : { \
									"client_id" : client_id, \
									"timestamp" : timestamp} \
								}
						dbq.write(outage_data)
			else:
				if sys.argv[1] == 'dns':
					dns_ok = test_name_resolution(test_exec_namespace,dbq)
					if not dns_ok:
						# dns lookup failures, test for an Internet outage
						ping_results = pingtest(test_exec_namespace,"8.8.8.8",dbq)
						(client_id,timestamp,remote_host,min,avg,max,mdev) = ping_results
						if min == 0 or max == 0:
							# log an outage
							outage_data = {"type": "isp_outage",\
									"data" : { \
									"client_id" : client_id, \
									"timestamp" : timestamp} \
								}
							dbq.write(outage_data)
				else:
					if sys.argv[1] == 'internet_ping':
						ping_results = pingtest(test_exec_namespace,"8.8.8.8",dbq)
						(client_id,timestamp,remote_host,min,avg,max,mdev) = ping_results
						message = {     "type" : "ping", \
								"data" : { 	"client_id" : client_id, \
										"timestamp" : timestamp, \
										"remote_host" : remote_host, \
										"min" : min, \
										"avg" : avg, \
										"max" : max, \
										"mdev" : mdev}}
						#logger.info("sending ping data to database")
						#dbq.write(message)

						if min == 0 or max == 0:
							outage_data = {"type": "isp_outage",\
									"data" : { \
										"client_id" : client_id, \
										"timestamp" : timestamp} \
									}
							dbq.write(outage_data)
					else:
						print_usage()
						sys.exit(1)
if __name__ == "__main__" :
        main()
