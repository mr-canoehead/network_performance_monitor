#!/usr/bin/env python3
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

import sys
import os
import getopt
import logging
import json
import util

APP_PATH="/opt/netperf"
SETTINGS_FILE="{}/config/netperf.json".format(APP_PATH)

def log_level_switcher(log_level_txt):
	log_levels = {
		"CRITICAL" : logging.INFO,
		"ERROR" : logging.ERROR,
		"WARNING": logging.WARNING,
		"INFO": logging.INFO,
		"DEBUG": logging.DEBUG
	}
	if log_level_txt in log_levels:
		log_level = log_levels[log_level_txt]
	else:
		log_level = logging.NOTSET
	return log_level


class netperf_settings:

	settings_json = None

	def save_settings(self):
		with open(SETTINGS_FILE,"w") as sf:
			settings_json_string = json.dumps(self.settings_json,indent=4)
			sf.truncate()
			sf.write(settings_json_string)
			sf.close()

	def __init__(self):
		with open(SETTINGS_FILE) as sf:
			self.settings_json = json.load(sf)

	def get_username(self):
		return self.settings_json.get("username",None)

	def get_data_root(self):
		if "data_root" in self.settings_json:
			return str(self.settings_json["data_root"])
		else:
			return None

	def get_db_filename(self):
		if "data_root" in self.settings_json:
			client_id = util.get_client_id()
			db_filename = "{}/{}/database/{}.db".format(self.settings_json["data_root"].rstrip("/"),client_id,client_id)
			return db_filename
		else:
			return None

	def get_db_path(self):
		if "data_root" in self.settings_json:
			client_id = util.get_client_id()
			db_path = "{}/{}/database".format(self.settings_json["data_root"].rstrip("/"),client_id)
			return db_path
		else:
			return None

	def get_report_path(self):
		if "data_root" in self.settings_json:
			client_id = util.get_client_id()
			report_path = "{}/{}/reports".format(self.settings_json["data_root"].rstrip("/"),client_id)
			return report_path
		else:
			return None

	def get_db_write_queue_name(self):
		db_write_queue_name = "/netperf.db"
		if "db_write_queue" in self.settings_json:
			db_write_queue_name = str(self.settings_json["db_write_queue"])
		return db_write_queue_name

	def get_log_filename(self):
		log_filename = "/mnt/usb_storage/netperf/log/netperf.log"
		if "data_root" in self.settings_json:
			log_filename = "{}/log/netperf.log".format(self.settings_json["data_root"].rstrip("/"))
		return log_filename

	def get_log_path(self):
		if "data_root" in self.settings_json:
			log_path = "{}/log".format(self.settings_json["data_root"].rstrip("/"))
			return log_path
		else:
			return "/mnt/usb_storage/netperf/log"

	def get_speedtest_enforce_quota(self):
		if "speedtest" in self.settings_json:
			speedtest_settings = self.settings_json["speedtest"]
			if "enforce_quota" in speedtest_settings:
				return speedtest_settings["enforce_quota"]
			else:
				return None

	def get_data_usage_quota_GB(self):
		if "speedtest" in self.settings_json:
			speedtest_settings = self.settings_json["speedtest"]
			if "data_usage_quota_GB" in speedtest_settings:
				return speedtest_settings["data_usage_quota_GB"]
			else:
				return None

	def get_logger_format(self):
		logger_format="%(asctime)s %(name)s %(levelname)s:%(message)s"
		if "logging" in self.settings_json:
			log_settings = self.settings_json["logging"]
			if "logger_format" in log_settings:
				logger_format = log_settings["logger_format"]
		return logger_format


	def get_log_level(self):
		log_level=logging.NOTSET
		if "logging" in self.settings_json:
			log_settings = self.settings_json["logging"]
			if "log_level" in log_settings:
				log_level = log_level_switcher(log_settings["log_level"])
		return log_level

	def set_data_usage_quota_GB(self,data_usage_quota_GB):
		self.settings_json["speedtest"]["data_usage_quota_GB"] = data_usage_quota_GB
		self.save_settings()

	def set_speedtest_enforce_quota(self,flag):
		self.settings_json["speedtest"]["enforce_quota"] = flag
		self.save_settings()

	def set_username(self, username):
		self.settings_json["username"] = username
		self.save_settings()

	def set_data_root(self,path):
		self.settings_json["data_root"] = path.rstrip("/")
		self.save_settings()

	def set_log_level(self,log_level):
		if "logging" in self.settings_json:
			log_settings = self.settings_json["logging"]
			if "log_level" in log_settings:
				log_settings["log_level"] = log_level
		self.save_settings()

	def get_dashboard_enabled(self):
		if "dashboard" in self.settings_json:
			dashboard_enabled = self.settings_json["dashboard"].get("enabled", False)
		else:
			dashboard_enabled = False
		return dashboard_enabled

	def get_dashboard_queue_name(self):
		if "dashboard" in self.settings_json:
			queue_name = self.settings_json["dashboard"].get("queue_name", None)
		else:
			queue_name = None
		return queue_name

	def set_dashboard_enabled(self,value):
		self.settings_json["dashboard"]["enabled"] = value
		self.save_settings()

	def set_bandwidth_monitor_enabled(self,value):
		self.settings_json["bandwidth_monitor"]["enabled"] = value
		self.save_settings()

	def set_speedtest_client(self, value):
		self.settings_json["speedtest"]["client"] = value
		self.save_settings()

	def get_speedtest_client(self):
		if "speedtest" in self.settings_json:
			speedtest_client = self.settings_json["speedtest"].get("client", None)
		else:
			speedtest_client = None
		return speedtest_client

	def set_speedtest_server_id(self,server_id):
		if "speedtest" in self.settings_json:
			speedtest_settings = self.settings_json["speedtest"]
			if server_id == "None":
				speedtest_settings["server_id"] = None
			else:
				speedtest_settings["server_id"] = server_id
		self.save_settings()

	def get_speedtest_server_id(self):
		if "speedtest" in self.settings_json:
			server_id = self.settings_json["speedtest"].get("server_id", None)
		else:
			server_id = None
		return server_id

	def get_bandwidth_monitor_enabled(self):
		bwm_enabled=False
		if "bandwidth_monitor" in self.settings_json:
			bwm_enabled=self.settings_json["bandwidth_monitor"].get("enabled",False)
		return bwm_enabled

def main():
	log_levels = set(['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'])
	ns = netperf_settings()
	unixOptions = 'g:s:v'
	gnuOptions = ['get=', 'set=', 'value=']
	try:
		options, remainder = getopt.getopt(sys.argv[1:], unixOptions, gnuOptions)
	except getopt.error as err:
		#output error, and return with an error code
		print(str(err))
		sys.exit(2)

	action = ""
	setting = ""
	value = ""
	for opt, arg in options:
		if opt in ('-g', '--get'):
			action = "get"
			setting = arg
		else:
			if opt in ('-s', '--set'):
				action = "set"
				setting = arg
			else:
				if opt in ('-v', '--value'):
					value = arg

	if action == "get":
		if setting == "db_filename":
			print (ns.get_db_filename())
		elif setting == "log_filename":
			print (ns.get_log_filename())
		elif setting == "username":
			print (ns.get_username())
		elif setting == "data_root":
			print (ns.get_data_root())
		elif setting == "report_path":
			print (ns.get_report_path())
		elif setting == "speedtest_server_id":
			print (ns.get_speedtest_server_id())
		elif setting == "speedtest_client":
			print (ns.get_speedtest_client())
		elif setting == "bwmonitor_enabled":
			print (ns.get_bandwidth_monitor_enabled())

	if action == "set":
		if setting == "data_usage_quota_GB":
			val_error=False
			if value == "":
				val_error = True
			try:
				data_usage_quota_GB = int(value)
			except ValueError:
				val_error = True
			if val_error or data_usage_quota_GB < 0:
				print ("data_usage_quota_GB value must be a positive integer.")
				sys.exit(0)
			else:
				ns.set_data_usage_quota_GB(data_usage_quota_GB)
		elif setting == "enforce_quota":
			value_error = False
			if value.lower() == "true":
				flag = True
			else:
				if value.lower() == "false":
					flag = False
				else:
					value_error = True
			if value_error:
				print ("enforce_quota value must be True or False")
			else:
				ns.set_speedtest_enforce_quota(flag)
		elif setting == "username":
			ns.set_username(value)
		elif setting == "data_root":
			if os.path.isdir(value):
				ns.set_data_root(value)
			else:
				print("Invalid path.")
		elif setting == "log_level":
			if value in log_levels:
				ns.set_log_level(value)
			else:
				print("Invalid log level")
		elif setting == "dashboard_enabled":
			if value.lower() == "true":
				ns.set_dashboard_enabled(True)
			elif value.lower() == "false":
				ns.set_dashboard_enabled(False)
			else:
				print ("dashboard_enabled value must be True or False")
		elif setting == "bwmonitor_enabled":
			if value.lower() == "true":
				ns.set_bandwidth_monitor_enabled(True)
			elif value.lower() == "false":
				ns.set_bandwidth_monitor_enabled(False)
			else:
				print ("bwmonitor_enabled value must be True or False")
		elif setting == "speedtest_client":
			if value.lower() == "ookla":
				ns.set_speedtest_client("ookla")
			elif value.lower() == "speedtest-cli":
				ns.set_speedtest_client("speedtest-cli")
			else:
				print ("speedtest_client value must be 'speedtest-cli' or 'ookla'")
		elif setting == "speedtest_server_id":
			if value != "":
				ns.set_speedtest_server_id(value)
			else:
				print ("speedtest_server_id setting requires a value")

if __name__ == "__main__":
	main()
