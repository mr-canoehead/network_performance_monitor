#!/usr/bin/env python
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

	def get_db_write_queue_name(self):
		db_write_queue_name = "/netperfdb.write"
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

	def set_data_root(self,path):
		self.settings_json["data_root"] = path.rstrip("/")
		self.save_settings()


def main():
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
			print ns.get_db_filename()
		else:
			if setting == "log_filename":
				print ns.get_log_filename()
			else:
				if setting == "data_root":
					print ns.get_data_root()


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
		else:
			if setting == "enforce_quota":
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
			else:
				if setting == "data_root":
					if os.path.isdir(value):
						ns.set_data_root(value)
					else:
						print("Invalid path.")
if __name__ == "__main__":
	main()
