#!/usr/bin/env python3
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

import sys
import util
from datetime import datetime, timedelta
from netperf_db import db_queue
from util import get_client_id

client_id = get_client_id()

dbq = db_queue()

message = { "type" : "data_usage_reset",\
	    "data" : { "client_id" : client_id } }
dbq.write(message)
