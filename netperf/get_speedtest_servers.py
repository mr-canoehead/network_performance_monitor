#!/usr/bin/env python3
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

import requests
from xml.dom.minidom import parse, parseString
import sys
import platform

SERVERLIST_URL="https://www.speedtest.net/speedtest-servers-static.php"
OUTPUT_FIELD_SEPARATOR="||"

ua_info = (
        'Mozilla/5.0',
        '(%s; U; %s; en-us)' % (platform.system(), platform.architecture()[0]),
        'Python/%s' % platform.python_version(),
        '(KHTML, like Gecko)',
        'netperf/1.0'
)

USER_AGENT = ' '.join(ua_info)

headers = {
    'User-Agent': USER_AGENT
}

try:
	response = requests.get(SERVERLIST_URL, headers=headers)
except requests.exceptions.RequestException as e:
	print ("Failed to retrieve server list.")
	sys.exit(1)
try:
	dom = parseString(response.content)
except:
	print ("Failed to parse server list.")
	sys.exit(1)

serverList = dom.getElementsByTagName("server")
serverAttributes = ["id","name","host","sponsor","country","cc","url","lat","lon"]

for server in serverList[:25]:
	serverString=""
	for a in serverAttributes:
		serverString += str(server.getAttribute(a))
		if a != serverAttributes[-1]:
			serverString += OUTPUT_FIELD_SEPARATOR
	print (serverString)
