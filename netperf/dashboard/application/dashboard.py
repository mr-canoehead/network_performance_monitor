#!/usr/bin/env python
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

import eventlet
eventlet.monkey_patch()
import sys
import datetime
import syslog
import json
import time
import os
import syslog
# insert at 1, 0 is the script path (or '' in REPL)
sys.path.insert(1, '/opt/netperf')

from netperf_db import netperf_db,dashboard_queue
from netperf_settings import netperf_settings
from threading import Lock
from flask import Flask, request, copy_current_request_context
from flask_socketio import SocketIO, emit, disconnect

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = "eventlet"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dashboard'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()

def background_thread():
	NETPERF_SETTINGS = netperf_settings()
	db = netperf_db(NETPERF_SETTINGS.get_db_filename())
	if NETPERF_SETTINGS.get_dashboard_enabled() == True:
		dashboard_q = dashboard_queue(NETPERF_SETTINGS.get_dashboard_queue_name())
	else:
		dashboard_q = None
		return
	while True:
		try:
			(message, priority) = dashboard_q.read()
		except:
			# no messages in the queue, wait a bit before trying to read it again
			socketio.sleep(0.25)
			continue
		type = message.get("type",None)
		data = message.get("data",None)
		if type is not None and data is not None:
			if type in {"bandwidth"}:
				timestamp = data["timestamp"]
				# discard stale bandwidth reading messages
				if time.time() - timestamp >= 1:
					continue
			socketio.emit(type,data,namespace='/dashboard', broadcast=True)
		else:
			# type and/or data is None, skip this message
			continue

@socketio.on('connect', namespace='/dashboard')
def connect():
	global thread
	with thread_lock:
		if thread is None:
			thread = socketio.start_background_task(background_thread)

def dbQuery(queryType, message = None):
	NETPERF_SETTINGS = netperf_settings()
	db = netperf_db(NETPERF_SETTINGS.get_db_filename())
	queryDate = datetime.date.today()
	if message is not None:
		if "queryDateTimestamp" in message:
			try:
				queryDate = datetime.date.fromtimestamp(message["queryDateTimestamp"] / 1000.0)
			except:
				queryDate = datetime.date.today()
	if queryType == 'speedtest':
		rowData = db.get_speedtest_data(queryDate)
	else:
		if queryType == 'isp_outage':
			rowData = db.get_isp_outage_data(queryDate)
		else:
			if queryType == 'iperf3':
				rowData = db.get_iperf3_data(queryDate)
			else:
				if queryType == 'dns':
					rowData = db.get_dns_data(queryDate)
				else:
					if queryType == 'bandwidth_usage':
						rowData = db.get_bandwidth_data(queryDate)
	return rowData

@socketio.on('get_bandwidth_data', namespace='/dashboard')
def get_bandwidth_data(message = None):
	NETPERF_SETTINGS = netperf_settings()
	db = netperf_db(NETPERF_SETTINGS.get_db_filename())
	if (message is not None) and ("minutes" in message):
		bwdata = db.get_bandwidth_data(minutes=message['minutes'])
	else:
		if (message is not None) and ("rows" in message):
			bwdata = db.get_bandwidth_data(rows=message["rows"])
		else:
			bwdata = db.get_bandwidth_data(datetime.date.today())
	emit('bandwidth_data',bwdata)

@socketio.on('get_bandwidth_usage', namespace='/dashboard')
def get_bandwidth_usage(message = None):
	bandwidth_usage = dbQuery('bandwidth_usage',message)
	emit('bandwidth_usage',bandwidth_usage)

@socketio.on('get_speedtest_data', namespace='/dashboard')
def get_speedtest_data(message = None):
    speedtest_data = dbQuery('speedtest',message)
    emit('speedtest_data',speedtest_data)

@socketio.on('get_dns_data', namespace='/dashboard')
def get_dns_data(message = None):
	dns_data = dbQuery('dns',message)
	emit('dns_data',dns_data)

@socketio.on('get_iperf3_data', namespace='/dashboard')
def get_iperf3_data(message = None):
	iperf3_data = dbQuery('iperf3',message)
	emit('iperf3_data',iperf3_data)

@socketio.on('get_report_list', namespace='/dashboard')
def get_report_list(message = None):
	nps = netperf_settings()
	reportPath = nps.get_report_path()
	reportFileList = []
	for file in os.listdir(reportPath):
		if file.endswith(".pdf"):
			reportFileList.append(file)
	emit('report_files',reportFileList)

@socketio.on('get_settings', namespace='/dashboard')
def get_settings(message = None):
	nps = netperf_settings();
	emit('settings', {'settings': nps.settings_json});

@socketio.on('get_isp_outage_data', namespace='/dashboard')
def get_isp_outage_data(message = None):
	outage_data = dbQuery('isp_outage',message)
	emit('isp_outage_data',outage_data)

if __name__ == '__main__':
	socketio.run(app, host="0.0.0.0",debug=True)
