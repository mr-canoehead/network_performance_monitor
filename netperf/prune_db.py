#!/usr/bin/env python
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

import sys
import util
from datetime import datetime, timedelta
from netperf_db import db_queue

dbq = db_queue()
today = datetime.now()
prune_date = today - timedelta(days=8)
timestamp = (prune_date - datetime(1970,1,1)).total_seconds()
message = { "type" : "prune",\
	    "data" : { "timestamp" : timestamp } }
dbq.write(message)
