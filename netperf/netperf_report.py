#!/usr/bin/env python
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

#from scipy.interpolate import make_interp_spline, BSpline
from datetime import datetime,date,timedelta
import time
import sys
import os
from subprocess import check_output,Popen,STDOUT,PIPE
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as md
import numpy as np
import re
import util
from netperf_db import netperf_db
import pprint
import logging
from time_bins import time_bins

CLIENT_ID = util.get_client_id()
DATA_ROOT="/mnt/usb_storage/netperf/{}".format(CLIENT_ID)
NETPERF_DB="{}/database/{}.db".format(DATA_ROOT,CLIENT_ID)
REPORT_TEMPLATE_PATH="/opt/netperf/templates"
REPORTS_PATH="{}/reports".format(DATA_ROOT)
TMP_PATH="{}/tmp".format(REPORTS_PATH)
KEYVALUE_FILE="{}/keyvalues.tex".format(TMP_PATH)

if not os.path.isdir(REPORTS_PATH):
        os.makedirs(REPORTS_PATH)

if not os.path.isdir(TMP_PATH):
        os.makedirs(TMP_PATH)

LOG_PATH="/mnt/usb_storage/netperf/log"
LOG_FILE="{}/netperf.log".format(LOG_PATH)

if not os.path.isdir(LOG_PATH):
        os.makedirs(LOG_PATH)

logging.basicConfig(filename=LOG_FILE,level=logging.INFO)
netperf_report_log = logging.getLogger('netperf.reporting')
netperf_report_log.setLevel(logging.INFO)

#class keyvals:
#	def __init__(self):
#		self.keyvalues = dict()
#	def add(self,family,key,value):
#		if family in self.keyvalues:
#			self.keyvalues[family][key] = value
#		else:
#			self.keyvalues[family] = dict()
#			self.keyvalues[family][key] = value

#	def tex(self):
#		tex_str = ""
#		for family in self.keyvalues:
#			for key in self.keyvalues[family]:
#				tex_str += "\define@key{{{}}}{{{}}}[{}]{{#1}}\n".format(family,key,self.keyvalues[family][key])
#		return tex_str

def fractional_hour(timestamp):
	# convert timestamp to fractional hour e.g. timestamp = 13:30 -> 13.5, timestamp = 15:45 -> 15.75 etc.
	SECONDS_PER_HOUR = 60*60
	dt = datetime.fromtimestamp(timestamp)
	dt_12am = datetime.combine(dt,datetime.min.time())
	tdelta = dt - dt_12am
	hour_frac = round(float(tdelta.seconds)/SECONDS_PER_HOUR,3)
	return hour_frac

def align_yaxis(ax1, v1, ax2, v2):
    """adjust ax2 ylimit so that v2 in ax2 is aligned to v1 in ax1"""
    _, y1 = ax1.transData.transform((0, v1))
    _, y2 = ax2.transData.transform((0, v2))
    inv = ax2.transData.inverted()
    _, dy = inv.transform((0, 0)) - inv.transform((0, y1-y2))
    miny, maxy = ax2.get_ylim()
    ax2.set_ylim(miny+dy, maxy+dy)

def main():
	main_replacement_values = {}
	today = date.today()
	midnight = datetime.combine(today,datetime.max.time())
	yesterday = today - timedelta(days=1)
	if len(sys.argv) > 1:
		try:
			query_date = datetime.strptime(sys.argv[1], '%Y-%m-%d')
		except:
			query_date = yesterday
		if query_date > midnight:
			netperf_report_log.error("Invalid report date; cannot generate a report for future dates.")
			return
	else:
		query_date = yesterday

	netperf_report_log.info("Generating network performance report for date {}".format(query_date.strftime("%Y-%m-%d")))

	main_replacement_values["<CLIENT_ID>"] = CLIENT_ID
	main_replacement_values["<QUERY_DATE>"] = query_date.strftime("%Y-%m-%d")
	main_replacement_values["<GRAPHICS_PATH>"] = TMP_PATH

	db = netperf_db(NETPERF_DB)

	isp_outage_rows = db.get_isp_outages(query_date)

	# get any internet ping failure rows, we'll add these as outage data points to the chart
	#iping_outage_rows = db.get_ping_interface_data(query_date,"8.8.8.8",outage_only=True)

	# outage timestamp for testing purposes, one hour ago
	#test_outage_ts = time.time() - (60 * 60 * 1000)
	#outage_ping_rows = [{'timestamp': test_outage_ts, 'max': 0.0, 'avg': 0.0, 'mdev': 0.0, 'min': 0.0}]
	#print outage_ping_rows
	rows = db.get_speedtest_data(query_date)
	if len(rows) == 0:
		netperf_report_log.error("No speedtest data available for date {}".format(query_date.strftime("%Y-%m-%d")))
		return

	speedtest_data={}
	speedtest_data["rx_Mbps"] = {}
	speedtest_data["rx_Mbps"]["raw"] = []
	speedtest_data["tx_Mbps"] = {}
	speedtest_data["tx_Mbps"]["raw"] = []
	speedtest_data["ping"] = {}
	speedtest_data["ping"]["raw"] = []
	speedtest_data["times"] = {}
	speedtest_data["times"]["raw"] = []
	speedtest_data["outages"] = {}
	speedtest_data["outages"]["times"] = []
	rx_bytes = long(0)
	tx_bytes = long(0)

	for r in rows:
		speedtest_data["rx_Mbps"]["raw"].append(r["rx_Mbps"])
		speedtest_data["tx_Mbps"]["raw"].append(r["tx_Mbps"])
		rx_bytes += long(r["rx_bytes"])
		tx_bytes += long(r["tx_bytes"])
		speedtest_data["ping"]["raw"].append(r["ping"])
		speedtest_data["times"]["raw"].append(fractional_hour(r["timestamp"]))
		if (r["rx_Mbps"] == 0) or (r["tx_Mbps"] == 0):
			speedtest_data["outages"]["times"].append(fractional_hour(r["timestamp"]))

	# create numpy arrays used for averaging
	speedtest_data["rx_Mbps"]["np_array"] = np.array(speedtest_data["rx_Mbps"]["raw"])
	speedtest_data["tx_Mbps"]["np_array"] = np.array(speedtest_data["tx_Mbps"]["raw"])
	speedtest_data["ping"]["np_array"] = np.array(speedtest_data["ping"]["raw"])
	speedtest_data["times"]["np_array"] = np.array(speedtest_data["times"]["raw"])

	# create interpolated data for smooth plot lines
	# NOTE: I ended up not using interpolated lines, I'm leaving this code here in case you wish to do so.
	#       When plotting the data, use ["smoothed"] instead of ["raw"] for interpolated line plots.
	#
	# spline_degree = 3
	# speedtest_data["times"]["smoothed"] = np.linspace(speedtest_data["times"]["np_array"].min(),speedtest_data["times"]["np_array"].max(),300)
	# spline = make_interp_spline(speedtest_data["times"]["np_array"], speedtest_data["rx_Mbps"]["raw"], k=spline_degree)
	# speedtest_data["rx_Mbps"]["smoothed"] = spline(speedtest_data["times"]["smoothed"])
	# spline = make_interp_spline(speedtest_data["times"]["np_array"], speedtest_data["tx_Mbps"]["raw"], k=spline_degree)
	# speedtest_data["tx_Mbps"]["smoothed"] = spline(speedtest_data["times"]["smoothed"])
	# spline = make_interp_spline(speedtest_data["times"]["np_array"],speedtest_data["ping"]["raw"], k=spline_degree)
	# speedtest_data["ping"]["smoothed"] = spline(speedtest_data["times"]["smoothed"])

	# add ping outage timestamps (ping test occurs much more frequently, so it is useful to include these on the speedtest chart)

	isp_outages={}
	isp_outages["times"] = []
	for r in isp_outage_rows:
		isp_outages["times"].append(fractional_hour(r["timestamp"]))

	isp_outages["y_values"] = np.zeros_like(isp_outages["times"])


	main_replacement_values["<ISP_OUTAGES>"] = str(len(isp_outage_rows))

	speedtest_data["outages"]["y_values"] = np.zeros_like(speedtest_data["outages"]["times"])
	speedtest_data["averages"] = {}
	speedtest_data["averages"]["rx_Mbps"] = speedtest_data["rx_Mbps"]["np_array"].mean()
	speedtest_data["averages"]["tx_Mbps"] = speedtest_data["tx_Mbps"]["np_array"].mean()
	speedtest_data["averages"]["ping"] = speedtest_data["ping"]["np_array"].mean()

	### generate speedtest chart
	axes={}
	fig, axes["rx_tx"] = plt.subplots()
	axes["rx_tx"].set_title("Speedtest results for {}".format(query_date.strftime("%Y-%m-%d")))
	axes["rx_tx"].set_xlabel('Time of day (24 hour clock)')
	axes["rx_tx"].set_ylabel('Bandwidth (Mbps)')
	lines={}
	lines["rx"] = axes["rx_tx"].plot(speedtest_data["times"]["raw"],speedtest_data["rx_Mbps"]["raw"],color="xkcd:blue",marker="",label='Download (Mbps)')
	lines["tx"] = axes["rx_tx"].plot(speedtest_data["times"]["raw"],speedtest_data["tx_Mbps"]["raw"],color="xkcd:green",marker="",label='Upload (Mbps)',linestyle="--")
	fig.subplots_adjust(bottom=0.2)
	axes["rx_tx"].set_xlim(0,24)
	axes["rx_tx"].set_xticks(np.arange(0,24,1))
	axes["ping"] = axes["rx_tx"].twinx()
	axes["ping"].set_ylabel('Latency (ms)', color="xkcd:red")
	axes["ping"].set_xlabel('Time of day (24 hr clock)')
	axes["ping"].tick_params(axis='y', labelcolor="xkcd:red")
	lines["ping"] = axes["ping"].plot(speedtest_data["times"]["raw"], speedtest_data["ping"]["raw"], color="xkcd:red", linewidth=1,linestyle=':',marker="",label="Latency (ms)")
	linesum = lines["rx"] + lines["tx"] + lines["ping"]
	if len(isp_outages["times"]) > 0:
		# plot isp outage times on chart
		lines["isp_outages"] = axes["rx_tx"].plot(isp_outages["times"],isp_outages["y_values"],color="xkcd:red",zorder=2,marker="D",linestyle="None", label="Internet outage")
		#for i in isp_outages["times"]:
		#	axes["rx_tx"].axvline(i,color="xkcd:red",linewidth=0.5)
		linesum = linesum + lines["isp_outages"]
		legend_columns = 2
	else:
		legend_columns = 3

	if len(speedtest_data["outages"]["times"]) > 0:
		lines["speedtest_outages"] = axes["rx_tx"].plot(speedtest_data["outages"]["times"],speedtest_data["outages"]["y_values"],color="xkcd:orange",zorder=1,marker="D",linestyle="None", label="Speedtest outage")
		linesum = linesum + lines["speedtest_outages"]
		legend_columns = 3

	if len(isp_outages["times"]) > 0:
		speedtest_data["outages"]["info"] = "One or more times during the reporting day an Internet outage was recorded."
		#speedtest_data["outages"]["info"] = "One or more times during the reporting day an Internet outage was recorded.\\footnote{{An internet outage is logged when the system fails to ping the remote host '8.8.8.8'. This address is Google's primary DNS server which is an extremely reliable service. A failure to ping this remote host is a strong indication that Internet connectivity has been interrupted.}} This may indicate that an interruption occurred with your Internet service."
	else:
		speedtest_data["outages"]["info"] = "No Internet outages were recorded during the reporting day."

	main_replacement_values["<OUTAGE_INFO>"] = speedtest_data["outages"]["info"]
	legend_labels = [l.get_label() for l in linesum]
	axes["rx_tx"].legend(linesum,legend_labels,loc='upper center', bbox_to_anchor=(0.5, -0.15), shadow=True, ncol=legend_columns)
	chart_filename = "speedtest_chart.pdf"
	main_replacement_values["<SPEEDTEST_CHART_NAME>"] = chart_filename
	fig.savefig("{}/{}".format(TMP_PATH,chart_filename),format='pdf', bbox_inches='tight')
	plt.cla()

	with open("{}/netperf_report_template.tex".format(REPORT_TEMPLATE_PATH)) as f:
		report = f.read()

	# generate LaTeX strings that will be used to print the speedtest data rows
	speedtest_data["table_tex"] = ""
	for r in rows:
		speedtest_data["table_tex"] += "{} & {} & {} & {} & {}\\\\\n".format(datetime.fromtimestamp(r["timestamp"]).strftime("%H:%M"),r["rx_Mbps"],r["tx_Mbps"],r["ping"],r["remote_host"])
	main_replacement_values["<SPEEDTEST_TABLE_DATA>"] = speedtest_data["table_tex"]

	rows = db.get_bandwidth_data(query_date)

	if len(rows) > 0:
		bin_width = 10
		rx_tbins = time_bins(bin_width)
		tx_tbins = time_bins(bin_width)
		bandwidth_data = {}
		bandwidth_data["times"] = {}
		bandwidth_data["times"]["raw"] = []
		bandwidth_data["rx"] = {}
		bandwidth_data["rx"]["bps"] = []
		bandwidth_data["rx"]["Mbps"] = []
		bandwidth_data["tx"] = {}
		bandwidth_data["tx"]["bps"] = []
		bandwidth_data["tx"]["Mbps"] = []
		for r in rows:
			rx_tbins.add_value(fractional_hour(r["timestamp"]),round(r["rx_bps"]/1e6))
			tx_tbins.add_value(fractional_hour(r["timestamp"]),round(r["tx_bps"]/1e6))
 			bandwidth_data["times"]["raw"].append(fractional_hour(r["timestamp"]))
			bandwidth_data["rx"]["bps"].append(r["rx_bps"])
			bandwidth_data["rx"]["Mbps"].append(round(r["rx_bps"]/1e6,2))
			bandwidth_data["tx"]["bps"].append(r["tx_bps"])
			bandwidth_data["tx"]["Mbps"].append(round(r["tx_bps"]/1e6,2))

		axes = {}
		fig, axes["times"] = plt.subplots()
		axes["times"].set_title("Bandwidth measurements for {}".format(query_date.strftime("%Y-%m-%d")))
		axes["times"].set_xlabel('Time of day (24 hour clock)')
		axes["times"].set_ylabel('Bandwidth (Mbps)')
		lines={}
		#lines["rx"] = axes["times"].bar(rx_tbins.get_times(),rx_tbins.get_means(),width=0.2,color="xkcd:blue",label='Receive')
		#lines["tx"] = axes["times"].bar(tx_tbins.get_times(),rx_tbins.get_means(),color="xkcd:green",label='Transmit')
		lines["rx"] = axes["times"].plot(rx_tbins.get_times(),rx_tbins.get_means(),color="xkcd:blue",label='Receive')
		#lines["rx"] = axes["times"].plot(bandwidth_data["times"]["raw"],bandwidth_data["rx"]["Mbps"],color="xkcd:blue",label='Receive')
		lines["tx"] = axes["times"].plot(tx_tbins.get_times(),tx_tbins.get_means(),color="xkcd:green",linestyle="--",label='Transmit')
		fig.subplots_adjust(bottom=0.2)
		axes["times"].set_xlim(0,24)
		axes["times"].set_xticks(np.arange(0,24,1))
		#axes["query_failures"] = axes["query_times"].twinx()
		#color = 'tab:red'
		#axes["query_failures"].set_ylabel('Query failures', color=color)
		#axes["query_failures"].set_xlabel('Time of day (24 hr clock)')
		#axes["query_failures"].tick_params(axis='y', labelcolor=color)
		#axes["query_failures"].yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
		#axes["query_failures"].set_ylim(top=max_dns_failures)
		#lines["internal_query_failures"] = axes["query_failures"].plot(dns_data["times"]["raw"], dns_data["internal"]["failures"]["raw"], linewidth=1,linestyle=':',color="xkcd:magenta",label="Internal query failures")
		#lines["external_query_failures"] = axes["query_failures"].plot(dns_data["times"]["raw"], dns_data["external"]["failures"]["raw"], linewidth=1,linestyle=':',color="xkcd:red",label="External query failures")
		linesum = lines["rx"] + lines["tx"]
		legend_labels = [l.get_label() for l in linesum]
		axes["times"].legend(linesum,legend_labels,loc='upper center', bbox_to_anchor=(0.5, -0.15), shadow=True, ncol=2)
		chart_filename = "bandwidth_chart.pdf"
		main_replacement_values["<BANDWIDTH_CHART_NAME>"] = chart_filename
		fig.savefig("{}/{}".format(TMP_PATH,chart_filename),format='pdf', bbox_inches='tight')

		with open("{}/bandwidth_report_template.tex".format(REPORT_TEMPLATE_PATH),"r") as f:
			bandwidth_tex = f.read()

		replacement_values={"<CHART_FILENAME>" : chart_filename, "<BIN_WIDTH>" : str(bin_width)}

		for key in replacement_values:
			bandwidth_tex = bandwidth_tex.replace(key,replacement_values[key])

		with open("{}/bandwidth_report.tex".format(TMP_PATH),"w") as f:
			f.truncate()
			f.write(bandwidth_tex)
			f.close()

		bandwidth_report_macro= "\\input{{{}}}\n".format("bandwidth_report.tex")
		main_replacement_values["<BANDWIDTH_REPORT>"] = bandwidth_report_macro
	else:
		netperf_report_log.info("No bandwidth data available for date {}".format(query_date.strftime("%Y-%m-%d")))
		main_replacement_values["<BANDWIDTH_REPORT>"] = ""

	max_dns_failures = 1
	rows = db.get_dns_data(query_date)
	if len(rows) > 0:
		dns_data={}
		dns_data["internal"]={}
		dns_data["internal"]["query_times"] = {}
		dns_data["internal"]["query_times"]["raw"] = []
		dns_data["internal"]["failures"] = {}
		dns_data["internal"]["failures"]["raw"] = []
		dns_data["external"]={}
		dns_data["external"]["query_times"] = {}
		dns_data["external"]["query_times"]["raw"] = []
		dns_data["external"]["failures"] = {}
		dns_data["external"]["failures"]["raw"] = []
		dns_data["times"] = {}
		dns_data["times"]["raw"] = []

		for r in rows:
 			dns_data["internal"]["query_times"]["raw"].append(r["internal_dns_query_time"])
			idnsf = r["internal_dns_failures"]
			if idnsf > max_dns_failures:
				max_dns_failures = idnsf
			dns_data["internal"]["failures"]["raw"].append(idnsf)
			dns_data["external"]["query_times"]["raw"].append(r["external_dns_query_time"])
			ednsf = r["external_dns_failures"]
			if ednsf > max_dns_failures:
				max_dns_failures = ednsf
			dns_data["external"]["failures"]["raw"].append(ednsf)
			dns_data["times"]["raw"].append(fractional_hour(r["timestamp"]))

		# create numpy arrays used for averaging
		dns_data["internal"]["query_times"]["np_array"] = np.array(dns_data["internal"]["query_times"]["raw"])
		dns_data["internal"]["failures"]["np_array"] = np.array(dns_data["internal"]["failures"]["raw"])
		dns_data["external"]["query_times"]["np_array"] = np.array(dns_data["external"]["query_times"]["raw"])
		dns_data["external"]["failures"]["np_array"] = np.array(dns_data["external"]["failures"]["raw"])
		dns_data["times"]["np_array"] = np.array(dns_data["times"]["raw"])

		axes = {}
		fig, axes["query_times"] = plt.subplots()
		axes["query_times"].set_title("Name resolution test results for {}".format(query_date.strftime("%Y-%m-%d")))
		axes["query_times"].set_xlabel('Time of day (24 hour clock)')
		axes["query_times"].set_ylabel('Query time (ms)')
		lines={}
		lines["internal_query_times"] = axes["query_times"].plot(dns_data["times"]["raw"],dns_data["internal"]["query_times"]["raw"],color="xkcd:blue",label='Internal queries')
		lines["external_query_times"] = axes["query_times"].plot(dns_data["times"]["raw"],dns_data["external"]["query_times"]["raw"],color="xkcd:green",linestyle="--",label='External queries')
		fig.subplots_adjust(bottom=0.2)
		axes["query_times"].set_xlim(0,24)
		axes["query_times"].set_xticks(np.arange(0,24,1))
		axes["query_failures"] = axes["query_times"].twinx()
		color = 'tab:red'
		axes["query_failures"].set_ylabel('Query failures', color=color)
		axes["query_failures"].set_xlabel('Time of day (24 hr clock)')
		axes["query_failures"].tick_params(axis='y', labelcolor=color)
		axes["query_failures"].yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
		axes["query_failures"].set_ylim(top=max_dns_failures)
		lines["internal_query_failures"] = axes["query_failures"].plot(dns_data["times"]["raw"], dns_data["internal"]["failures"]["raw"], linewidth=1,linestyle=':',color="xkcd:magenta",label="Internal query failures")
		lines["external_query_failures"] = axes["query_failures"].plot(dns_data["times"]["raw"], dns_data["external"]["failures"]["raw"], linewidth=1,linestyle=':',color="xkcd:red",label="External query failures")
		linesum = lines["internal_query_times"] + lines["external_query_times"] + lines["internal_query_failures"] + lines["external_query_failures"]
		legend_labels = [l.get_label() for l in linesum]
		axes["query_times"].legend(linesum,legend_labels,loc='upper center', bbox_to_anchor=(0.5, -0.15), shadow=True, ncol=2)
		chart_filename = "dns_chart.pdf"
		main_replacement_values["<DNS_CHART_NAME>"] = chart_filename
		fig.savefig("{}/{}".format(TMP_PATH,chart_filename),format='pdf', bbox_inches='tight')

	# get list of interfaces that have iperf3 records on the query date
	rows = db.get_iperf3_interfaces(query_date)

	# generate iperf3 reports for each interface
	iperf3_interfaces=[]
	for r in rows:
		iperf3_data={}
		iperf3_data["remote_host"] = r["remote_host"]
		iperf3_data["rx_Mbps"] = {}
		iperf3_data["rx_Mbps"]["raw"] = []
		iperf3_data["tx_Mbps"] = {}
		iperf3_data["tx_Mbps"]["raw"] = []
		iperf3_data["retransmits"] = {}
		iperf3_data["retransmits"]["raw"] = []
		iperf3_data["ping"] = {}
		iperf3_data["ping"]["raw"] = []
		iperf3_data["times"] = {}
		iperf3_data["times"]["raw"] = []
		iperf3_data["outages"] = {}
		iperf3_data["outages"]["times"] = []
		iperf3_data["averages"] = {}
		#remote_host = r["remote_host"]
		iperf3_interfaces.append(iperf3_data["remote_host"])
		iperf3_rows = db.get_iperf3_interface_data(query_date,iperf3_data["remote_host"])
		(fig,ax) = plt.subplots()
		rx_Mbps=[]
		tx_Mbps=[]
		retransmits=[]
		times=[]
		outage_times=[]
		for i in iperf3_rows:
			iperf3_data["rx_Mbps"]["raw"].append(i["rx_Mbps"])
			iperf3_data["tx_Mbps"]["raw"].append(i["tx_Mbps"])
			iperf3_data["retransmits"]["raw"].append(i["retransmits"])
			iperf3_data["times"]["raw"].append(fractional_hour(i["timestamp"]))
			if (i["rx_Mbps"] == 0) or (i["tx_Mbps"] == 0):
				iperf3_data["outages"]["times"].append(fractional_hour(i["timestamp"]))

		# create numpy arrays used for averaging
		iperf3_data["rx_Mbps"]["np_array"] = np.array(iperf3_data["rx_Mbps"]["raw"])
		iperf3_data["tx_Mbps"]["np_array"] = np.array(iperf3_data["tx_Mbps"]["raw"])
		iperf3_data["retransmits"]["np_array"] = np.array(iperf3_data["retransmits"]["raw"])
		iperf3_data["times"]["np_array"] = np.array(iperf3_data["times"]["raw"])
		iperf3_data["outages"]["y_values"] = np.zeros_like(iperf3_data["outages"]["times"])


		iperf3_data["averages"]["rx_Mbps"] = np.mean(iperf3_data["rx_Mbps"]["np_array"])
		iperf3_data["averages"]["tx_Mbps"] = np.mean(iperf3_data["tx_Mbps"]["np_array"])
		iperf3_data["averages"]["retransmits"] = np.mean(iperf3_data["retransmits"]["np_array"])

	        axes={}
		fig, axes["rx_tx"] = plt.subplots()
		axes["rx_tx"].set_title("iperf3 test results for interface {} on {}".format(iperf3_data["remote_host"],query_date.strftime("%Y-%m-%d")))
		axes["rx_tx"].set_xlabel('Time of day (24 hour clock)')
		axes["rx_tx"].set_ylabel('Bandwidth (Mbps)')
		lines={}
		lines["rx"] = axes["rx_tx"].plot(iperf3_data["times"]["raw"],iperf3_data["rx_Mbps"]["raw"],color="xkcd:blue",marker="",label='Receive (Mbps)')
		lines["tx"] = axes["rx_tx"].plot(iperf3_data["times"]["raw"],iperf3_data["tx_Mbps"]["raw"],color="xkcd:green",marker="",label='Transmit (Mbps)',linestyle="--")
		fig.subplots_adjust(bottom=0.2)
		axes["rx_tx"].set_xlim(0,24)
		axes["rx_tx"].set_xticks(np.arange(0,24,1))
        	linesum = lines["rx"] + lines["tx"]
		if np.count_nonzero(iperf3_data["retransmits"]["raw"]) > 0:
			axes["retransmits"] = axes["rx_tx"].twinx()
			color = "m"
			axes["retransmits"].set_ylabel('Retransmits', color="xkcd:red")
			axes["retransmits"].set_xlabel('Time of day (24 hr clock)')
			axes["retransmits"].tick_params(axis='y', labelcolor="xkcd:red")
			axes["retransmits"].yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
			lines["retransmits"] = axes["retransmits"].plot(iperf3_data["times"]["raw"], \
									iperf3_data["retransmits"]["raw"], \
									color="xkcd:red", \
									linewidth=1, \
									linestyle=':', \
									marker="", \
									label="Retransmits")
			linesum = linesum + lines["retransmits"]

		if len(iperf3_data["outages"]["times"]) > 0:
                	# plot outage times on chart
			lines["outages"] = axes["rx_tx"].plot(iperf3_data["outages"]["times"],iperf3_data["outages"]["y_values"],color="xkcd:red",marker="D",linestyle="None", label = "Inteface outage")
			for x in iperf3_data["outages"]["times"]:
				axes["rx_tx"].axvline(x,color="xkcd:red",linewidth=0.5)
			linesum = linesum + lines["outages"]
			legend_columns = 2
			iperf3_data["outages"]["info"] = "One or more times during the reporting day the Download speed and/or Upload speed was zero. This may indicate that an outage occurred on the local network."
		else:
			legend_columns = 3
			iperf3_data["outages"]["info"] = "No outage intervals were recorded during the reporting day."
		legend_labels = [l.get_label() for l in linesum]
		axes["rx_tx"].legend(linesum,legend_labels,loc='upper center', bbox_to_anchor=(0.5, -0.15), shadow=True, ncol=legend_columns)
		chart_filename = "{}_iperf3_chart.pdf".format(iperf3_data["remote_host"])
        	replacement_values = {}
		fig.savefig("{}/{}".format(TMP_PATH,chart_filename),format='pdf', bbox_inches='tight')
		plt.cla()

		with open("{}/interface_report_template.tex".format(REPORT_TEMPLATE_PATH),"r") as f:
			interface_tex = f.read()

		replacement_values={ \
			"<CHART_FILENAME>" : chart_filename, \
			"<INTERFACE_NAME>" : iperf3_data["remote_host"], \
			"<RX_MBPS_AVG>" : str(round(float(iperf3_data["averages"]["rx_Mbps"]),2)), \
			"<TX_MBPS_AVG>" : str(round(float(iperf3_data["averages"]["tx_Mbps"]),2)), \
			"<RETRANSMITS_AVG>" : str(int(round(iperf3_data["averages"]["retransmits"],0))), \
			"<OUTAGE_INTERVALS>" : str(len(iperf3_data["outages"]["times"])), \
			"<OUTAGE_INFO>" : iperf3_data["outages"]["info"]}

		for key in replacement_values:
			interface_tex = interface_tex.replace(key,replacement_values[key])

		with open("{}/{}_iperf3_report.tex".format(TMP_PATH,iperf3_data["remote_host"]),"w") as f:
			f.truncate()
			f.write(interface_tex)
			f.close()


	main_replacement_values["<RX_MBPS_AVG>"] = str(round(speedtest_data["averages"]["rx_Mbps"],2))
	main_replacement_values["<TX_MBPS_AVG>"] = str(round(speedtest_data["averages"]["tx_Mbps"],2))
	main_replacement_values["<LATENCY_AVG>"] = str(round(speedtest_data["averages"]["ping"],2))
	main_replacement_values["<RX_MB>"] = str(round(float(rx_bytes)/float(1e6),2))
	main_replacement_values["<TX_MB>"] = str(round(float(tx_bytes)/float(1e6),2))
	main_replacement_values["<RXTX_MB>"] = str(round(float(rx_bytes + tx_bytes)/float(1e6),2))

	interface_reports_macro = ""
	for i in iperf3_interfaces:
		if_report_name = "{}_iperf3_report".format(i)
		interface_reports_macro += "\\input{{{}}}\n".format(if_report_name)
	main_replacement_values["<INTERFACE_REPORTS>"] = interface_reports_macro

	for key in main_replacement_values:
		report = report.replace(key,main_replacement_values[key])

	report_filename="{}/{}_{}_netperf.tex".format(TMP_PATH,CLIENT_ID,query_date.strftime("%Y%m%d"))
	output = open(report_filename,"w")
	output.truncate()
	output.write(report)
	output.close()

	# compile the report
	cmd="/usr/bin/rubber --pdf --into {} {}".format(REPORTS_PATH,report_filename)
	##cmd="/usr/bin/rubber -p --into {} {}".format(REPORTS_PATH,report_filename)
	ps = Popen(cmd,shell=True,stdout=PIPE,stderr=STDOUT)
	(cmd_results,return_code) = ps.communicate()

	# clean up additional files generated by the compiler
	cmd="/usr/bin/rubber --clean --into {} {}".format(REPORTS_PATH,report_filename)
	##ps = Popen(cmd,shell=True,stdout=PIPE,stderr=STDOUT)
	##(cmd_results,return_code) = ps.communicate()

	# clean up temporary files created during report generation
	##tmp_files=[]
	##for root, dirs, files in os.walk(TMP_PATH):
	##    for f in files:
	##        if f.endswith((".png", ".tex",".aux",".log",".svg",".pdf")):
	##            tmp_files.append(os.path.join(root, f))
	##for f in tmp_files:
	##	try:
	##		os.remove(f)
	##	except:
	##		print "Error: unable to delete file {}".format(f)
if __name__ == "__main__":
	main()
