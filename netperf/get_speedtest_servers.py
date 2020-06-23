#!/usr/bin/env python
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

import requests
from xml.dom.minidom import parse, parseString
import sys

SERVERLIST_URL="https://www.speedtest.net/speedtest-servers.php"
OUTPUT_FIELD_SEPARATOR="||"

try:
	response = requests.get(SERVERLIST_URL)
except requests.exceptions.RequestException as e:
	print "Failed to retrieve server list."
	sys.exit(1)

try:
	dom = parseString(response.content)
except:
	print "Failed to parse server list."
	sys.exit(1)

serverList = dom.getElementsByTagName("server")
serverAttributes = ["id","name","host","sponsor","country","cc","url","lat","lon"]

for server in serverList[:25]:
	serverString=""
	for a in serverAttributes:
		serverString += str(server.getAttribute(a).encode('utf-8'))
		if a != serverAttributes[-1]:
			serverString += OUTPUT_FIELD_SEPARATOR
	print (serverString)
