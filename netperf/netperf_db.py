#!/usr/bin/env python
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.


import datetime
import time
import sqlite3
import json
from sqlite3 import Error
import posix_ipc
import sys
import util
import logging
import os
from netperf_settings import netperf_settings

client_id = util.get_client_id()

NETPERF_SETTINGS = netperf_settings()

DATA_PATH = NETPERF_SETTINGS.get_db_path()
NETPERF_DB = NETPERF_SETTINGS.get_db_filename()

DB_WRITE_QUEUE = NETPERF_SETTINGS.get_db_write_queue_name()
LOG_PATH = NETPERF_SETTINGS.get_log_path()
LOG_FILE = NETPERF_SETTINGS.get_log_filename()

if not os.path.isdir(DATA_PATH):
	os.makedirs(DATA_PATH)

if not os.path.isdir(LOG_PATH):
	os.makedirs(LOG_PATH)

logging.basicConfig(filename=NETPERF_SETTINGS.get_log_filename(), format=NETPERF_SETTINGS.get_logger_format())
db_log = logging.getLogger("netperf_db")
db_log.setLevel(NETPERF_SETTINGS.get_log_level())

def start_end_timestamps(query_date):
	# given a datetime, return a tuple containing timestamps representing the earliest time
	# on that day and the latest time on that day (corresponding to 00:00:00 and 23:59:59.99999...)
	start_datetime = datetime.datetime.combine(query_date,datetime.datetime.min.time())
	end_datetime = datetime.datetime.combine(query_date,datetime.datetime.max.time())
	start_timestamp = float(start_datetime.strftime('%s'))
	end_timestamp = float(end_datetime.strftime('%s'))
	return (start_timestamp,end_timestamp)

def create_table(db_conn, create_table_sql):
        try:
                c = db_conn.cursor()
                c.execute(create_table_sql)
        except Error as e:
                print(e)

class netperf_db:
	def __init__(self,db_file):
		try:
			self.db_conn = sqlite3.connect(db_file)
			self.db_conn.execute("PRAGMA journal_mode=WAL")
		except Error as e:
			print(e)

		sql_create_isp_outage_table = """ CREATE TABLE IF NOT EXISTS isp_outages (
                                        client_id text NOT NULL,
                                        epoch_time real NOT NULL,
                                        PRIMARY KEY (client_id,epoch_time)
                                    ); """

		sql_create_speedtest_table = """ CREATE TABLE IF NOT EXISTS speedtest (
                                        client_id text NOT NULL,
                                        epoch_time real NOT NULL,
                                        rx_Mbps real NOT NULL,
                                        tx_Mbps real NOT NULL,
					rx_bytes integer NOT NULL,
					tx_bytes integer NOT NULL,
                                        remote_host text NOT NULL,
                                        url text NOT NULL,
                                        ping real,
                                        PRIMARY KEY (client_id,epoch_time)
                                    ); """

		sql_create_iperf3_table = """CREATE TABLE IF NOT EXISTS iperf3 (
                                        client_id text NOT NULL,
                                        epoch_time real NOT NULL,
                                        remote_host text NOT NULL,
                                        rx_Mbps real NOT NULL,
                                        tx_Mbps real NOT NULL,
                                        retransmits integer,
                                        PRIMARY KEY (client_id,epoch_time)
                                );"""

		sql_create_ping_table = """CREATE TABLE IF NOT EXISTS ping (
                                client_id text NOT NULL,
                                epoch_time real NOT NULL,
                                remote_host text NOT NULL,
                                min real NOT NULL,
                                avg real NOT NULL,
                                max real NOT NULL,
                                mdev real NOT NULL,
                                PRIMARY KEY (client_id,epoch_time)
                                );"""


		sql_create_dns_table = """CREATE TABLE IF NOT EXISTS dns (
                                client_id text NOT NULL,
                                epoch_time real NOT NULL,
				internal_dns_ok integer NOT NULL,
				internal_dns_query_time integer NOT NULL,
				internal_dns_failures integer NOT NULL,
				external_dns_ok integer NOT NULL,
				external_dns_query_time integer NOT NULL,
				external_dns_failures integer NOT NULL,
                                PRIMARY KEY (client_id,epoch_time)
                                );"""


		sql_create_bandwidth_table = """CREATE TABLE IF NOT EXISTS bandwidth (
				client_id text NOT NULL,
				epoch_time real NOT NULL,
				rx_bytes integer NOT NULL,
				tx_bytes integer NOT NULL,
				rx_bps real NOT NULL,
				tx_bps real NOT NULL,
				PRIMARY KEY (client_id,epoch_time)
				);"""

		sql_create_data_usage_table = """ CREATE TABLE IF NOT EXISTS data_usage (
                                        client_id text NOT NULL,
                                        epoch_time real NOT NULL,
					rxtx_bytes integer NOT NULL,
                                        PRIMARY KEY (client_id,epoch_time)
                                    ); """

		if self.db_conn is not None:
			create_table(self.db_conn, sql_create_isp_outage_table)
			create_table(self.db_conn, sql_create_speedtest_table)
			create_table(self.db_conn, sql_create_iperf3_table)
			create_table(self.db_conn, sql_create_ping_table)
			create_table(self.db_conn, sql_create_dns_table)
			create_table(self.db_conn, sql_create_bandwidth_table)
			create_table(self.db_conn, sql_create_data_usage_table)
		else:
			print("Error! cannot create the database connection.")

	def log_isp_outage(self, data):
		client_id = data["client_id"]
		timestamp = data["timestamp"]
		sql = '''INSERT OR IGNORE INTO isp_outages(client_id,epoch_time)
			VALUES(?,?);'''
		cur = self.db_conn.cursor()
		cur.execute(sql, (client_id, timestamp))
		self.db_conn.commit()
		cur.close()
		return cur.lastrowid

	def log_pingtest(self, pingtest_results):
		#logger.info("inserting ping results")
		sql = '''INSERT OR IGNORE INTO ping(client_id,epoch_time,remote_host,min,avg,max,mdev)
			VALUES(?,?,?,?,?,?,?);'''
		cur = self.db_conn.cursor()
		cur.execute(sql, pingtest_results)
		self.db_conn.commit()
		cur.close()
		return cur.lastrowid

	def log_ping(self,data):
		row_data = ( 	data["client_id"], \
				data["timestamp"], \
				data["remote_host"], \
				data["min"], \
				data["avg"], \
				data["max"], \
				data["mdev"])
		#print json.dumps(row_data)
		sql = '''INSERT OR IGNORE INTO ping(client_id,epoch_time,remote_host,min,avg,max,mdev)
			VALUES(?,?,?,?,?,?,?);'''
		cur = self.db_conn.cursor()
		cur.execute(sql, row_data)
		self.db_conn.commit()
		cur.close()
		return cur.lastrowid

	def log_iperf3(self, data):
		row_data = ( data["client_id"], \
			     data["timestamp"], \
			     data["remote_host"], \
		             data["rx_Mbps"], \
			     data["tx_Mbps"], \
			     data["retransmits"] )
		sql = '''INSERT OR IGNORE INTO iperf3(client_id,epoch_time,remote_host,rx_Mbps,tx_Mbps,retransmits)
			VALUES(?,?,?,?,?,?);'''
		cur = self.db_conn.cursor()
		cur.execute(sql, row_data)
		self.db_conn.commit()
		cur.close()
		return cur.lastrowid

	def log_speedtest(self,data):
                row_data = ( data["client_id"], \
                            data["timestamp"], \
                            data["rx_Mbps"], \
                            data["tx_Mbps"], \
                            data["rx_bytes"],\
                            data["tx_bytes"],\
                            data["remote_host"], \
                            data["url"], \
                            data["ping"] )
                sql = '''INSERT OR IGNORE INTO speedtest(client_id,epoch_time,rx_Mbps,tx_Mbps,rx_bytes,tx_bytes,remote_host,url,ping)
                        VALUES(?,?,?,?,?,?,?,?,?);'''
                cur = self.db_conn.cursor()
                cur.execute(sql, row_data)
                self.db_conn.commit()
                cur.close()
                return cur.lastrowid

	def log_bandwidth(self,data):
		row_data = ( data["client_id"], \
			     data["timestamp"], \
		             data["rx_bytes"], \
			     data["tx_bytes"], \
			     data["rx_bps"], \
			     data["tx_bps"])
		sql = '''INSERT OR IGNORE INTO bandwidth(client_id,epoch_time,rx_bytes,tx_bytes,rx_bps,tx_bps)
			VALUES(?,?,?,?,?,?);'''
		cur = self.db_conn.cursor()
		cur.execute(sql, row_data)
		self.db_conn.commit()
		cur.close()
		return cur.lastrowid

	def log_data_usage(self,data):
		db_log.debug("start of log_data_usage")
                cur = self.db_conn.cursor()
                cur.execute("SELECT rxtx_bytes FROM data_usage where epoch_time = (select max(epoch_time) from data_usage)")
                col_rxtx_bytes=0
                query_results = cur.fetchall()
		db_log.debug("length of query results: {}".format(len(query_results)))
		if len(query_results) > 0:
			current_rxtx_bytes = long(query_results[0][col_rxtx_bytes])
		else:
			current_rxtx_bytes = 0
		new_rxtx_bytes = current_rxtx_bytes + long(data["rxtx_bytes"])
		db_log.debug("new_rxtx_bytes: {}".format(new_rxtx_bytes))
                row_data = ( data["client_id"], \
                            data["timestamp"], \
                            new_rxtx_bytes )
		db_log.debug("row_data: {}".format(row_data))
                sql = '''INSERT OR IGNORE INTO data_usage(client_id,epoch_time,rxtx_bytes)
                        VALUES(?,?,?);'''
                cur.execute(sql, row_data)
                self.db_conn.commit()
                cur.close()
                return cur.lastrowid

	def log_dns(self, dns_results):
                # unpack dns_results tuple
                client_id = dns_results["client_id"]
                timestamp = dns_results["timestamp"]
                internal_dns_ok = dns_results["internal_dns_ok"]
                internal_dns_query_time = dns_results["internal_dns_query_time"]
                internal_dns_failures = dns_results["internal_dns_failures"]
                external_dns_ok = dns_results["external_dns_ok"]
                external_dns_query_time = dns_results["external_dns_query_time"]
                external_dns_failures = dns_results["external_dns_failures"]

                # map booleans to 1 = True, 0 = False
                if internal_dns_ok:
                        idns_ok = 1
                else:
                        idns_ok = 0

                if external_dns_ok:
                        edns_ok = 1
                else:
                        edns_ok = 0

                repacked_dns_results = (client_id,
                                        timestamp,
                                        idns_ok,
                                        internal_dns_query_time,
                                        internal_dns_failures,
                                        edns_ok,
                                        external_dns_query_time,
                                        external_dns_failures)

                sql = '''INSERT OR IGNORE INTO dns(client_id,epoch_time,internal_dns_ok,internal_dns_query_time,internal_dns_failures,external_dns_ok,external_dns_query_time,external_dns_failures)
                        VALUES(?,?,?,?,?,?,?,?);'''
                cur = self.db_conn.cursor()
                cur.execute(sql, repacked_dns_results)
                self.db_conn.commit()
                cur.close()
                return cur.lastrowid

	def get_isp_outages(self, query_date):
		(start_timestamp,end_timestamp) = start_end_timestamps(query_date)
		cur = self.db_conn.cursor()
		cur.execute("SELECT * FROM isp_outages where epoch_time >= {} and epoch_time <= {}".format(start_timestamp,end_timestamp))
		col_time=1
		results=[]
		for i in cur.fetchall():
			results.append({"timestamp" : i[col_time]})
		cur.close()
		return results

	def get_speedtest_data(self,query_date):
		(start_timestamp,end_timestamp) = start_end_timestamps(query_date)
		cur = self.db_conn.cursor()
		cur.execute("SELECT * FROM speedtest where epoch_time >= {} and epoch_time <= {}".format(start_timestamp,end_timestamp))
		col_time=1
		col_rx_Mbps=2
		col_tx_Mbps=3
                col_rx_bytes=4
                col_tx_bytes=5
		col_remote_host=6
		col_url=7
		col_ping=8
		results=[]
		for i in cur.fetchall():
			results.append({"timestamp" : i[col_time], \
					"rx_Mbps" : i[col_rx_Mbps], \
				        "tx_Mbps" : i[col_tx_Mbps], \
                                        "rx_bytes" : i[col_rx_bytes], \
                                        "tx_bytes" : i[col_tx_bytes], \
					"ping" : i[col_ping], \
					"remote_host" : i[col_remote_host],\
					"url" : i[col_url]})
		cur.close()
		return results

	#def delete_speedtest_data(self,query_date):
	#	(start_timestamp,end_timestamp) = start_end_timestamps(query_date)
	#	cur = self.db_conn.cursor()
	#	cur.execute("DELETE FROM speedtest where epoch_time >= {} and epoch_time <= {}".format(start_timestamp,end_timestamp))
	#	cur.close()
	#	self.db_conn.commit()

	def get_speedtest_data_usage(self,query_date):
		(start_timestamp,end_timestamp) = start_end_timestamps(query_date)
		cur = self.db_conn.cursor()
		cur.execute("SELECT COUNT(*) AS test_count, SUM(rx_bytes + tx_bytes) AS rxtx_bytes FROM speedtest where epoch_time >= {} and epoch_time <= {}".format(start_timestamp,end_timestamp))
		col_test_count=0
		col_rxtx_bytes=1
		results=[]
		query_results = cur.fetchall()
		test_count = query_results[0][col_test_count]
		if test_count == 0:
			rxtx_bytes = 0
		else:
			rxtx_bytes = long(query_results[0][col_rxtx_bytes])
		results.append({"test_count" : test_count, \
				"rxtx_bytes" : rxtx_bytes})
		#db_log.info("Speedtest data usage: {}".format(results))
		cur.close()
		return results


	def get_data_usage(self):
		db_log.debug("start of get_data_usage")
                cur = self.db_conn.cursor()
                cur.execute("SELECT rxtx_bytes FROM data_usage where epoch_time = (select max(epoch_time) from data_usage)")
                col_rxtx_bytes=0
                query_results = cur.fetchall()
		cur.close()
		db_log.debug("length of query results: {}".format(len(query_results)))
		if len(query_results) > 0:
			rxtx_bytes = long(query_results[0][col_rxtx_bytes])
		else:
			rxtx_bytes = long(0)
		results={"rxtx_bytes" : rxtx_bytes}
		return results

	def get_iperf3_data(self,query_date):
		(start_timestamp,end_timestamp) = start_end_timestamps(query_date)
		cur = self.db_conn.cursor()
		cur.execute("SELECT * FROM iperf3 where epoch_time >= {} and epoch_time <= {}".format(start_timestamp,end_timestamp))
		col_time=1
		col_remote_host=2
		col_rx_Mbps=3
		col_tx_Mbps=4
		col_retransmits=5
		results=[]
		for i in cur.fetchall():
			results.append({"timestamp" : i[col_time], \
					"remote_host" : i[col_remote_host], \
					"rx_Mbps" : i[col_rx_Mbps], \
					"tx_Mbps" : i[col_tx_Mbps], \
					"retransmits" : i[col_retransmits]})
		cur.close()
		return results

	def get_ping_interface_data(self,query_date, interface, outage_only = False):
		(start_timestamp,end_timestamp) = start_end_timestamps(query_date)
		if outage_only:
			query_str = "SELECT * FROM ping where (epoch_time >= {} AND epoch_time <= {}) AND remote_host LIKE \"{}\" AND (min = 0 OR max = 0)"
		else:
			query_str = "SELECT * FROM ping where (epoch_time >= {} AND epoch_time <= {}) AND remote_host LIKE \"{}\""
		cur = self.db_conn.cursor()
		cur.execute(query_str.format(start_timestamp,end_timestamp,interface))
		col_time=1
		col_min=3
		col_avg=4
		col_max=5
		col_mdev=6
		results=[]
		for i in cur.fetchall():
			results.append({"timestamp" : i[col_time], \
					"min" : i[col_min], \
					"avg" : i[col_avg], \
					"max" : i[col_max], \
					"mdev" : i[col_mdev]})
		cur.close()
		return results

	def get_iperf3_interface_data(self,query_date, interface):
		(start_timestamp,end_timestamp) = start_end_timestamps(query_date)
		cur = self.db_conn.cursor()
		cur.execute("SELECT * FROM iperf3 where epoch_time >= {} and epoch_time <= {} and remote_host LIKE \"{}\"".format(start_timestamp,end_timestamp,interface))
		col_time=1
		col_rx_Mbps=3
		col_tx_Mbps=4
		col_retransmits=5
		results=[]
		for i in cur.fetchall():
			results.append({"timestamp" : i[col_time], \
					"rx_Mbps" : i[col_rx_Mbps], \
					"tx_Mbps" : i[col_tx_Mbps], \
					"retransmits" : i[col_retransmits]})
		cur.close()
		return results

	def get_iperf3_interfaces(self,query_date):
		start_datetime = datetime.datetime.combine(query_date,datetime.datetime.min.time())
		end_datetime = datetime.datetime.combine(query_date,datetime.datetime.max.time())
		start_epoch = float(start_datetime.strftime('%s'))
		end_epoch = float(end_datetime.strftime('%s'))
		cur = self.db_conn.cursor()
		cur.execute("SELECT DISTINCT remote_host FROM iperf3 where epoch_time >= {} and epoch_time <= {}".format(start_epoch,end_epoch))
		results=[]
		for i in cur.fetchall():
			results.append({"remote_host" : i[0]})
		cur.close()
		return results

	def get_dns_data(self,query_date):
		start_datetime = datetime.datetime.combine(query_date,datetime.datetime.min.time())
		end_datetime = datetime.datetime.combine(query_date,datetime.datetime.max.time())
		start_epoch = float(start_datetime.strftime('%s'))
		end_epoch = float(end_datetime.strftime('%s'))
		cur = self.db_conn.cursor()
		cur.execute("SELECT * FROM dns where epoch_time >= {} and epoch_time <= {}".format(start_epoch,end_epoch))
		col_time=1
		col_idns_ok=2
		col_internal_dns_query_time=3
		col_internal_dns_failures=4
		col_edns_ok=5
		col_external_dns_query_time=6
		col_external_dns_failures=7
		results=[]
		for i in cur.fetchall():
			# map integer values to booleans
			if i[col_idns_ok] == 1:
				internal_dns_ok = True
			else:
				internal_dns_ok = False
			if i[col_edns_ok] == 1:
				external_dns_ok = True
			else:
				external_dns_ok = False

			results.append({"timestamp" : i[col_time], \
					"internal_dns_ok" : internal_dns_ok, \
				        "internal_dns_query_time" : i[col_internal_dns_query_time], \
				        "internal_dns_failures" : i[col_internal_dns_failures], \
					"external_dns_ok" : external_dns_ok, \
				        "external_dns_query_time" : i[col_external_dns_query_time], \
				        "external_dns_failures" : i[col_external_dns_failures]})
		cur.close()
		return results

	def get_last_bandwidth(self):
		cur = self.db_conn.cursor()
		cur.execute("SELECT * FROM bandwidth ORDER BY epoch_time DESC LIMIT 1")
		col_time=1
		col_rx_bytes=2
		col_tx_bytes=3
		col_rx_bps=4
		col_tx_bps=5
		results=None
		for i in cur.fetchall():
			results = {"timestamp" : i[col_time], \
				   "rx_bytes" : i[col_rx_bytes], \
				   "tx_bytes" : i[col_tx_bytes], \
				   "rx_bps" : i[col_rx_bps], \
				   "tx_bps" : i[col_tx_bps]}
			break
		cur.close()
		return results

	def get_bandwidth_data(self,query_date):
		(start_timestamp,end_timestamp) = start_end_timestamps(query_date)
		cur = self.db_conn.cursor()
		cur.execute("SELECT * FROM bandwidth where epoch_time >= {} and epoch_time <= {}".format(start_timestamp,end_timestamp))
		col_time=1
		col_rx_bytes=2
		col_tx_bytes=3
		col_rx_bps=4
		col_tx_bps=5
		results=[]
		for i in cur.fetchall():
			results.append({"timestamp" : i[col_time], \
					"rx_bps" : i[col_rx_bps], \
				        "tx_bps" : i[col_tx_bps]})
		cur.close()
		return results

	def prune(self,data):
		# deletes all rows (in all tables) with an epoch_time <= latest time on given date
		timestamp = data.get("timestamp",None)
		if timestamp is not None:
			prune_date = datetime.datetime.fromtimestamp(timestamp)
		else:
			db_log.error("prune: invalid timestamp")
			return
		(start_timestamp, end_timestamp) = start_end_timestamps(prune_date)
		#select name from sqlite_master where type = 'table';
		cur = self.db_conn.cursor()
		db_log.info("pruning database rows")
		cur.execute("SELECT NAME FROM sqlite_master where type = 'table'")
		for t in cur.fetchall():
			table_name = t[0]
			cur.execute("SELECT COUNT(*) AS CNTREC FROM pragma_table_info('{}') WHERE name='epoch_time'".format(table_name))
			if cur.fetchall()[0] != 0:
				cur.execute("DELETE FROM {} WHERE epoch_time < {}".format(table_name, end_timestamp))
				#rowcount = cur.fetchall()[0][0]
				#print "Will prune {} rows from table {}".format(rowcount,table_name)
		# compact the database file
		cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
		cur.execute("VACUUM")
		cur.close()
		self.db_conn.commit()


	def data_usage_reset(self,data):
		# resets data usage to zero
		timestamp = time.time()
		cur = self.db_conn.cursor()
		query = "INSERT INTO data_usage (client_id,epoch_time,rxtx_bytes) VALUES('{}','{}','{}')".format(client_id,timestamp,str(0));
		cur.execute(query)
		cur.close()
		self.db_conn.commit()

	def close(self):
		try:
			self.db_conn.commit()
			self.db_conn.close()
		except:
			pass

class db_queue():
	queue = None
	def __init__(self):
		try:
	        	self.queue = posix_ipc.MessageQueue(DB_WRITE_QUEUE, posix_ipc.O_CREX)
		except:
        		self.queue = posix_ipc.MessageQueue(DB_WRITE_QUEUE)

	def write(self,json_object):
		self.queue.send(json.dumps(json_object))

	def read(self):
		( message, priority ) = self.queue.receive()
		try:
			json_data = json.loads(message)
		except:
			json_data = None
			db_log.error("received invalid message: {}".format(str(message)))
		return ( json_data, priority )

if __name__ == '__main__':
	db = netperf_db(NETPERF_DB)
	dbq = db_queue()
	sigterm_h = util.sigterm_handler()

	def invalid(data):
		db_log.error("Invalid message type: {}".format(data.get("type",None)))

	def function_map(type):
		switcher = {
			"bandwidth": db.log_bandwidth,
			"speedtest": db.log_speedtest,
			"ping": db.log_ping,
			"iperf3": db.log_iperf3,
			"dns": db.log_dns,
			"isp_outage": db.log_isp_outage,
			"data_usage": db.log_data_usage,
			"prune": db.prune,
			"data_usage_reset": db.data_usage_reset
		}
		return switcher.get(type, invalid)

	while not sigterm_h.terminate:
		message, priority = dbq.read()
		db_log.debug(message)
		if message is not None:
			type = message.get("type",None)
			db_log.debug("message type is: {}".format(type))
			data = message.get("data",None)
			#db_log.error("received invalid message: {}".format(str(message)))
			#continue
			db_log.debug("received message type: {} data: {}".format(type,json.dumps(data)))

		else:
			type = "undefined"
			data = {"error" : "unable to parse json object"}
			db_log.error("received undefined message")
			continue
		try:
			function_map(type)(data)
		except:
			db_log.error("error occurred while writing to the database")
	db.close()
