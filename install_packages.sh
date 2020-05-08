#!/bin/bash
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

apt_packages=( sqlite3 bridge-utils python-posix-ipc python-daemon python-numpy python-matplotlib iperf3 \
               speedtest-cli dnsutils texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended \
               git bc nginx gunicorn python-pip)

declare -A pip_packages
pip_packages[Flask]=flask
pip_packages[flask-socketio]=flask_socketio
pip_packages[eventlet]=eventlet

all_packages_installed=true
echo "Installing required packages..."
for apt_package in "${apt_packages[@]}"
do
	# test if package is already installed
	dpkg -s "$apt_package" > /dev/null 2>&1
	if [[ "$?" -eq 0 ]]; then
		echo "	$apt_package is installed"
	else
		#try 3 times to install the package (sometimes Raspbian mirrors can be unreliable)
		package_installed=false
		for i in {1..3}
		do
			echo "	Installing package $apt_package..."
			echo
			sudo apt install -y "$apt_package"
			echo
			# check that the package is now installed
			dpkg -s "$apt_package" > /dev/null 2>&1
			if [[ "$?" -eq 0 ]]; then
				echo "	$apt_package is installed"
				package_installed=true
				break
			fi
		done
		if [[ "$package_installed" == "false" ]]; then
			echo "	Failed to install package $apt_package"
			all_packages_installed=false
		fi
	fi
done

for pip_package in "${!pip_packages[@]}"
do
	# test if package is already installed
	python -c "import ${pip_packages[$pip_package]}" > /dev/null 2>&1
	if [[ "$?" -eq 0 ]]; then
		echo "	$pip_package is installed"
	else
		#try 3 times to install the package (sometimes Raspbian mirrors can be unreliable)
		package_installed=false
		for i in {1..3}
		do
			echo "	Installing pip package $pip_package..."
			echo
			pip install "$pip_package"
			echo
			# check that the package is now installed
			python -c "import ${pip_packages[$pip_package]}" > /dev/null 2>&1
			if [[ "$?" -eq 0 ]]; then
				echo "	$pip_package is installed"
				package_installed=true
				break
			fi
		done
		if [[ "$package_installed" == "false" ]]; then
			echo "	Failed to install pip package $pip_package"
			all_packages_installed=false
		fi
	fi
done

if [[ "$all_packages_installed" == "false" ]]; then
	echo 
	echo "Error: One or more required packages failed to install. Check your Internet connection from this machine, or switch mirrors."
	echo "       Then run this script again."
else
	echo
	echo "All required packages were installed successfully."
fi

