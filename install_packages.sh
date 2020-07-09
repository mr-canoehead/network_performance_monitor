#!/bin/bash
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

apt_packages=( sqlite3 python3-posix-ipc python3-daemon python3-numpy python3-matplotlib iperf3 \
               dnsutils texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended \
               bc nginx gunicorn3 python3-pip)

declare -A pip_packages
pip_packages[Flask]=flask
pip_packages[flask-socketio]=flask_socketio
pip_packages[eventlet]=eventlet
pip_packages[requests]=requests

result=$( whiptail --title "Speedtest client selection" --menu --nocancel \
"The system performs periodic Internet speed tests against Ookla speedtest.net servers. \
There are two speedtest clients available for performing these tests:\n\n\
speedtest-cli: an open source speedtest client that may report inaccurate speeds on faster Internet connections\n\n\
Ookla Speedtest CLI: a closed source proprietary client that reports accurate speeds on faster Internet connections\n\n\
Which client do you want to install?\n\n
" 20 80 2 \
"speedtest-cli" " open source client" \
"Ookla Speedtest CLI" " closed source proprietary client" 3>&1 1>&2 2>&3 )

if [[ "$result" == "speedtest-cli" ]]; then
	# uninstall Ookla client, add speedtest-cli to the package list
	dpkg -s speedtest
	if [[ "$?" -eq 0 ]]; then
		sudo apt remove -y speedtest
	fi
	apt_packages+=( speedtest-cli )
else
	# uninstall speedtest-cli, add Ookla client + dependencies to the package list
	dpkg -s speedtest-cli > /dev/null 2>&1
	if [[ "$?" -eq 0 ]]; then
		sudo apt remove -y speedtest-cli
	fi
	INSTALL_KEY=379CE192D401AB61
	DEB_DISTRO=$(lsb_release -sc)
	sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys "$INSTALL_KEY"
	echo "deb https://ookla.bintray.com/debian ${DEB_DISTRO} main" | sudo tee  /etc/apt/sources.list.d/speedtest.list > /dev/null
	apt_packages+=( gnupg1 apt-transport-https dirmngr speedtest)
fi

all_packages_installed=true
echo "Installing required packages..."
sudo apt update
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
	python3 -c "import ${pip_packages[$pip_package]}" > /dev/null 2>&1
	if [[ "$?" -eq 0 ]]; then
		echo "	$pip_package is installed"
	else
		#try 3 times to install the package (sometimes Raspbian mirrors can be unreliable)
		package_installed=false
		for i in {1..3}
		do
			echo "	Installing pip package $pip_package..."
			echo
			pip3 install "$pip_package"
			echo
			# check that the package is now installed
			python3 -c "import ${pip_packages[$pip_package]}" > /dev/null 2>&1
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
	# if the Ookla Speedtest CLI application is installed, run it so that the user can accept the Ookla license agreement.
		dpkg -s speedtest > /dev/null 2>&1
		if [[ "$?" -eq 0 ]]; then
			whiptail --title "Ookla license agreement" --msgbox "The system will now run the Speedtest CLI application so that you can accept the Ookla license agreement." 10 80 3>&1 1>&2 2>&3
			sudo -u pi speedtest
        fi
	echo
	echo "All required packages were installed successfully."
fi

