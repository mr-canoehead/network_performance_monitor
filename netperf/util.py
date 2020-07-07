#!/usr/bin/env python3
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

from subprocess import check_output,Popen,STDOUT,PIPE
import numpy as np
import signal

def nz_values(arr):
# return an array containing all non-zero values in the source array
	nztuples = np.nonzero(arr)
	nzvalues = []
	for i in nztuples[0]:
		nzvalues.append(arr[i])
	return nzvalues

def get_client_id():
	cmd = "sum /etc/machine-id | cut -f 1 -d ' '"
	ps = Popen(cmd,shell=True,stdout=PIPE,stderr=STDOUT)
	(sn_str,return_code) = ps.communicate()
	return (sn_str.decode()).rstrip("\n")

class sigterm_handler():
	def sh(self,signalNumber, frame):
		self.terminate = True
	def __init__(self):
		self.terminate = False
		signal.signal(signal.SIGTERM, self.sh)

