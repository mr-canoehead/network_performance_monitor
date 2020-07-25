#!/bin/bash
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

source /opt/netperf/scriptutils.sh

raspbian_os_packages=( sqlite3 python3-daemon python3-numpy python3-matplotlib iperf3 \
                       dnsutils texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended \
                       bc nginx gunicorn3 python3-pip)

centos_os_packages=( epel-release gcc sqlite python3-daemon python3-matplotlib python36-devel iperf3 \
                     bind-utils iw wpa_supplicant bc nginx python3-gunicorn python3-pip libqhull texlive-latex \
                     texlive-collection-latexrecommended texlive-titlesec )

pip_packages=( posix_ipc flask flask-socketio eventlet requests )

printf "\nInstalling software packages required for the Network Performance Monitor project.\n\n"

os_id=$( get_os_id )
printf "System type: $os_id\n\n"

if [[ "$os_id" == "centos" ]]; then
	# enable PowerTools repository for libqhull (required for python3-matplotlib on CentOS systems)
	printf "Installing dnf-plugins-core...\n"
	install_os_package dnf-plugins-core > /dev/null
	printf "Enabling PowerTools repository...\n"
	dnf config-manager --set-enabled PowerTools
	os_packages=("${centos_os_packages[@]}")
	# check if SELinux is enforced on this system
	sel_enforced=$( selinux_enforced )
	if [[ "$sel_enforced" == true ]]; then
		# add package that contains the 'semanage' tool
		os_packages+=( policycoreutils-python-utils )
	fi
else
	if [[ "$os_id" == "raspbian" ]]; then
		os_packages=("${raspbian_os_packages[@]}")
	else
		printf "Unsupported operating system: $os_od\n"
		exit 1
	fi
fi

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
	package_installed=$( os_package_installed speedtest )
	if [[ "$package_installed" == true ]]; then
		printf "Removing Ookla Speedtest CLI client...\n"
		remove_os_package speedtest
	fi
	pip_packages+=( speedtest-cli )
else
	# uninstall speedtest-cli, add Ookla client + dependencies to the package list
	package_installed=$( pip_package_installed speedtest-cli )
	if [[ "$package_installed" == true ]]; then
		printf "Removing speedtest-cli client...\n"
		remove_pip_package speedtest-cli > /dev/null
	fi
	if [[ "$os_id" == "centos" ]]; then
		printf "Adding Ookla repository...\n"
		package_installed=$( os_package_installed wget )
		if [[ "$package_installed" == false ]]; then
			printf "Installing wget...\n"
			install_os_package wget > /dev/null
		fi
		wget https://bintray.com/ookla/rhel/rpm -O bintray-ookla-rhel.repo > /dev/null 2>&1
		mv bintray-ookla-rhel.repo /etc/yum.repos.d/ > /dev/null 2>&1
		os_packages+=( speedtest )
	else
		if [[ "$os_id" == "raspbian" ]]; then
			printf "Adding Ookla repository...\n"
			INSTALL_KEY=379CE192D401AB61
			DEB_DISTRO=$(lsb_release -sc)
			sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys "$INSTALL_KEY"
			echo "deb https://ookla.bintray.com/debian ${DEB_DISTRO} main" | sudo tee  /etc/apt/sources.list.d/speedtest.list > /dev/null
			os_packages+=( gnupg1 apt-transport-https dirmngr speedtest)
		fi
	fi
fi

printf "Updating repository cache...\n"
update_repository_cache

all_packages_installed=true

printf "Installing required packages...\n"
for os_package in "${os_packages[@]}"
do
	# test if package is already installed
	result=$( os_package_installed "$os_package" )
	if [[ "$result" == true ]]; then
		printf "	$os_package is installed\n"
	else
		#try 3 times to install the package (sometimes Raspbian mirrors can be unreliable)
		package_installed=false
		for i in {1..3}
		do
			printf "	Installing package $os_package... "
			install_os_package "$os_package" > /dev/null
			# check that the package is now installed
			result=$( os_package_installed "$os_package" )
			if [[ "$result" == true ]]; then
				printf " done.\n"
				package_installed=true
				break
			fi
		done
		if [[ "$package_installed" == "false" ]]; then
			printf " error, installation failed.\n"
			all_packages_installed=false
		fi
	fi
done

for pip_package in "${pip_packages[@]}"
do
	# test if package is already installed
	installed=$( pip_package_installed "$pip_package" )
	if [[ "$installed" == true ]]; then
		echo "	$pip_package is installed"
	else
		#try 3 times to install the package (sometimes Raspbian mirrors can be unreliable)
		package_installed=false
		for i in {1..3}
		do
			printf "	Installing pip package $pip_package..."
			install_pip_package "$pip_package" > /dev/null
			# check that the package is now installed
			installed=$( pip_package_installed "$pip_package" )
			if [[ "$installed" == true ]]; then
				printf " done.\n"
				package_installed=true
				break
			fi
		done
		if [[ "$package_installed" == "false" ]]; then
			echo "	error, installation failed.\n"
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
		result=$( os_package_installed speedtest )
		if [[ "$result" == true ]]; then
			whiptail --title "Ookla license agreement" --msgbox "The system will now run the Speedtest CLI application so that you can accept the Ookla license agreement." 10 80 3>&1 1>&2 2>&3
			sudo -u pi speedtest
        fi
	echo
	echo "All required packages were installed successfully."
fi

