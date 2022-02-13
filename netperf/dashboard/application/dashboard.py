#!/usr/bin/env python3
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

import sys
import datetime
import syslog
import json
import time
import os
import syslog

from threading import Lock
from flask import Flask, request, copy_current_request_context
from flask_socketio import SocketIO, emit, disconnect

from celery import Celery
from kombu import Queue

# insert at 1, 0 is the script path (or '' in REPL)
sys.path.insert(1, '/opt/netperf')

from netperf_db import netperf_db,dashboard_queue
from netperf_settings import netperf_settings
from time_bins import time_bins
from util import fractional_hour

SIO_NAMESPACE="/dashboard"
MQ_HOST="localhost"
MQ_VHOST="netperf"
MQ_USER="netperf"
MQ_PASS="netperf"
MQ_URI=f"amqp://{MQ_USER}:{MQ_PASS}@{MQ_HOST}/{MQ_VHOST}"

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = "threading"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dashboard'
app.config['CELERY_BROKER_URL'] = MQ_URI
app.config['result_backend'] = "rpc://"

celery = Celery(app.name,broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)
celery.conf.broker_connection_max_retries = 0
celery.conf.worker_prefetch_multiplier = 1
celery.conf.task_acks_late = True
celery.conf.task_default_queue = 'medium'
celery.conf.task_queues = (
    Queue('light'),
    Queue('medium'),
    Queue('heavy')
)

socketio = SocketIO(app, async_handlers=True, async_mode=async_mode, message_queue=MQ_URI)
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
			socketio.emit(type,data,namespace=SIO_NAMESPACE, broadcast=True)
		else:
			# type and/or data is None, skip this message
			continue

@socketio.on('connect', namespace=SIO_NAMESPACE)
def connect():
	global thread
	with thread_lock:
		if thread is None:
			thread = socketio.start_background_task(background_thread)

def dbQuery(queryType, data = None):
	NETPERF_SETTINGS = netperf_settings()
	db = netperf_db(NETPERF_SETTINGS.get_db_filename())
	queryDate = datetime.date.today()
	if data is not None:
		if "queryDateTimestamp" in data:
			try:
				queryDate = datetime.date.fromtimestamp(data["queryDateTimestamp"] / 1000.0)
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

@celery.task
def async_task(request_event = None, data = None, requester_sid = None):
	response_event = ""
	response_data = None
	if request_event == 'get_speedtest_data':
		response_event = 'speedtest_data'
		response_data = dbQuery('speedtest',data)
	elif request_event == 'get_dns_data':
		response_event = 'dns_data'
		response_data = dbQuery('dns',data)
	elif request_event == 'get_iperf3_data':
		response_event = 'iperf3_data'
		response_data = dbQuery('iperf3',data)
	elif request_event == 'get_isp_outage_data':
		response_event = 'isp_outage_data'
		response_data = dbQuery('isp_outage',data)
	elif request_event == 'get_settings':
		response_event = 'settings'
		nps = netperf_settings()
		response_data = {'settings': nps.settings_json}
	elif request_event == 'get_bandwidth_data':
		response_event = 'bandwidth_data'
		nps = netperf_settings()
		db = netperf_db(nps.get_db_filename())
		if (data is not None) and ("minutes" in data):
			response_data = db.get_bandwidth_data(minutes=data['minutes'])
		else:
			if (data is not None) and ("rows" in data):
				response_data = db.get_bandwidth_data(rows=data["rows"])
			else:
				response_data = db.get_bandwidth_data(datetime.date.today())
	elif request_event == 'get_bandwidth_usage':
		response_event = 'bandwidth_usage'
		response_data = None
		rows = dbQuery('bandwidth_usage',data)
		if len(rows) > 0:
			bin_width = 10
			rx_tbins = time_bins(bin_width)
			tx_tbins = time_bins(bin_width)
			for r in rows:
				rx_tbins.add_value(fractional_hour(r["timestamp"]),round(r["rx_bps"]/1e6))
				tx_tbins.add_value(fractional_hour(r["timestamp"]),round(r["tx_bps"]/1e6))
			averaged_data = {
				'rx': [],
				'tx': []
			}
			rx_times = rx_tbins.get_times()
			rx_means = rx_tbins.get_means()
			tx_times = tx_tbins.get_times()
			tx_means = tx_tbins.get_means()
			for i in range(len(rx_times)):
				averaged_data['rx'].append({'fractional_hour' : rx_times[i], 'value' : rx_means[i]})
			for i in range(len(tx_times)):
				averaged_data['tx'].append({'fractional_hour' : tx_times[i], 'value' : tx_means[i]})
		response_data = { 'averaged_usage' : averaged_data }
	elif request_event == 'get_report_list':
		response_event = 'report_list'
		nps = netperf_settings()
		reportPath = nps.get_report_path()
		reportFileList = []
		for file in os.listdir(reportPath):
			if file.endswith(".pdf"):
				reportFileList.append(file)
		response_data = reportFileList

	sio = SocketIO(message_queue=MQ_URI)
	sio.emit(response_event, response_data, namespace=SIO_NAMESPACE, room=f"{requester_sid}")

@socketio.event(namespace=SIO_NAMESPACE)
def get_dns_data(data = None):
	async_task.apply_async(args=[request.event["message"],data,request.sid],queue='light')

@socketio.event(namespace=SIO_NAMESPACE)
def get_bandwidth_data(data = None):
	async_task.apply_async(args=[request.event["message"],data,request.sid],queue='medium')

@socketio.event(namespace=SIO_NAMESPACE)
def get_bandwidth_usage(data = None):
	async_task.apply_async(args=[request.event["message"],data,request.sid],queue='heavy')

@socketio.event(namespace=SIO_NAMESPACE)
def get_speedtest_data(data = None):
	async_task.apply_async(args=[request.event["message"],data,request.sid],queue='light')

@socketio.event(namespace=SIO_NAMESPACE)
def get_iperf3_data(data = None):
	async_task.apply_async(args=[request.event["message"],data,request.sid],queue='medium')

@socketio.event(namespace=SIO_NAMESPACE)
def get_isp_outage_data(data = None):
	async_task.apply_async(args=[request.event["message"],data,request.sid],queue='light')

@socketio.event(namespace=SIO_NAMESPACE)
def get_report_list(data = None):
	async_task.apply_async(args=[request.event["message"],data,request.sid],queue='medium')

@socketio.event(namespace=SIO_NAMESPACE)
def get_settings(data = None):
	async_task.apply_async(args=[request.event["message"],data,request.sid],queue='light')

if __name__ == '__main__':
	socketio.run(app, host="0.0.0.0",debug=True)
