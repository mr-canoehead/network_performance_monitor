#!/bin/bash
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

declare -a packages
packages+=( "sqlite3" )
packages+=( "bridge-utils" )
packages+=( "python-posix-ipc" )
packages+=( "python-daemon" )
packages+=( "python-numpy" )
packages+=( "python-matplotlib" )
packages+=( "iperf3" )
packages+=( "speedtest-cli" )
packages+=( "dnsutils" )
packages+=( "texlive-latex-recommended" )
packages+=( "texlive-latex-extra" )
packages+=( "texlive-fonts-recommended" )
packages+=( "git" )
packages+=( "bc" )

all_packages_installed=true
echo "Installing required packages..."
for apt_package in "${packages[@]}"
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
if [[ "$all_packages_installed" == "false" ]]; then
	echo 
	echo "Error: One or more required packages failed to install. Check your Internet connection from this machine, or switch mirrors."
	echo "       Then run this script again."
fi

