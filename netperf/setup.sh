#!/bin/bash
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

# This is the initial setup script for configuring the Network Performance Monitor.
# It is used to set the data storage path and data usage quota (if applicable)
# It then calls the script setup_interfaces.sh which configures the network 
# interfaces used by the system.

TITLE="Network Performance Monitor Configuration"
CONFIG_APP="/opt/netperf/netperf_settings.py"

# check that the script is being run as root
if [[ $EUID -ne 0 ]]; then
        echo "This script must be run as root, e.g:"
        echo "sudo ./$(basename $0)"
        exit 1
fi

# check that Predictable Network Interface Names is enabled
if [[ -L "/etc/systemd/network/99-default.link" ]]; then
	whiptail --title "$TITLE" --msgbox "Error: the Network Performance Monitor requires that Predictable Network Interface Names be enabled. It is not currently enabled. Please run raspi-config again and select the option:\n\n2 Network Options\n    N3 Network interface names - Enable/Disable predictable network interface names\n        Choose 'Yes'\n\nThis setting requires a reboot to take effect, after enabling Predictable Network Interface Names please reboot the system and run this setup script again." 15 100 3>&1 1>&2 2>&3
	exit 1
fi

valid_dir=false
write_access=false
cancel=false
until [[ ( "$valid_dir" == true && "$write_access" == true ) || "$cancel" == true ]]
do
	data_root=$( python "$CONFIG_APP" --get data_root )
	data_root=$( whiptail --title "$TITLE" --inputbox "Enter the data storage path:" 10 60 "$data_root" 3>&1 1>&2 2>&3 )
	if [[ "$?" -eq 1 ]]; then
		cancel=true
		break
	fi

	if [[ "$cancel" != true ]]; then
		# strip any trailing spaces and trailing slashes
		data_root=$( echo "$data_root" | sed 's/[ /]*$//g' )
		# check that path is a directory:
		if [[ -d "$data_root" ]]; then
			valid_dir=true
		else
			valid_dir=false
		fi
		if [[ "$valid_dir" != true ]]; then
			whiptail --title "$TITLE" --yesno --yes-button "Ok" --no-button "Exit" "Error: The specified directory does not exist.\n\nChoose 'Ok' to enter a different directory name, or choose 'Exit' to leave the configuration script so that you can correct this issue." 12 70 3>&1 1>&2 2>&3
			if [[ "$?" -eq 1 ]]; then
				exit 0
			fi
		fi
	fi

	# verify that the directory is not located on the SD card
	findmnt -n -o SOURCE --target "$data_root" | grep mmcblk0 > /dev/null
	if [[ "$?" -eq 0 ]]; then
			whiptail --title "$TITLE" --yesno --yes-button "Continue" --no-button "Exit" --defaultno "Warning: the specified directory is located on the SD card.\n\nIt is highly recommended that you use an external USB 3 storage device for the data storage directory. The Network Performance Monitor performes a high number of database writes; storing the database on the SD card will reduce its lifespan.\n\nChoose 'Continue' to proceed using this directory, or choose 'Exit' to leave the configuration script so that you can correct this issue." 15 80 3>&1 1>&2 2>&3
			if [[ "$?" -eq 1 ]]; then
				exit 0
			fi
	fi

	if [[ "$valid_dir" == true ]]; then
		username="pi"
		if read -a dirVals < <(stat -Lc "%U %G %A" "$data_root") && (
		( [ "$dirVals" == "$username" ] && [ "${dirVals[2]:2:1}" == "w" ] ) ||
		( [ "${dirVals[2]:8:1}" == "w" ] ) ||
		( [ "${dirVals[2]:5:1}" == "w" ] && (gMember=($(groups "$username")) &&
		[[ "${gMember[*]:2}" =~ ^(.* |)"${dirVals[1]}"( .*|)$ ]]
		) ) )
		then
			write_access=true
		else
			whiptail --title "$TITLE" --yesno --yes-button "Ok" --no-button "Exit" "Error: The 'pi' user does not have write access to the specified directory.\n\nChoose 'Ok' to enter a different directory name, or choose 'Exit' to leave the configuration script so that you can correct this issue." 10 80 3>&1 1>&2 2>&3
			if [[ "$?" -eq 1 ]]; then
				exit 0
			fi
			write_access=false
		fi
	fi
done
if [[ "$cancel" == true ]]; then
	exit 0
fi
whiptail --title "$TITLE" --yesno "Warning: Internet speed tests consume data.\n\nIf your Internet service does not have unlimited data, you may wish to configure a data usage quota for Internet speed tests. With a usage quota configured, the system will stop performing Internet speed tests when the usage quota is reached. Internet speed tests will resume when the data usage total is reset.\n\nDo you want to configure an Internet speed test quota to limit the amount of data used by the system?" 17 80 3>&1 1>&2 2>&3
if [[ "$?" == "0" ]]; then
	valid_quota=false
	until [[ "$valid_quota" == "true" ]]; do
		data_usage_quota_GB=$( whiptail --title "$TITLE" --inputbox "Enter the data usage quota in Gigabytes:" 10 60 20 3>&1 1>&2 2>&3)
		re='^[0-9]+$'
		if ! [[ "$data_usage_quota_GB" =~ $re ]] ; then
			valid_quota=false
			whiptail --title "$TITLE" --msgbox "Invalid number, please try again." 10 40 3>&1 1>&2 2>&3
		else
			valid_quota=true
		fi
	done
	whiptail --title "$TITLE" --msgbox "Data usage quota will be set to $data_usage_quota_GB GB." 10 60 3>&1 1>&2 2>&3
	enforce_quota="True"
else
	whiptail --title "$TITLE" --msgbox "The system will be run without a data usage quota. Be aware that this may result in high data usage if the system is allowed to run continuously for an extended period of time. The Internet speed test usage metrics are shown on the daily report." 10 80 3>&1 1>&2 2>&3
	data_usage_quota_GB=0
	enforce_quota="False"
fi

# create the log directory if it doesn't exist:
if [[ ! -d "$data_root/log" ]]; then
	sudo -u pi mkdir "$data_root/log"
	# create the initial log file as the 'pi' user
	sudo -u pi touch "$data_root/log/netperf.log"
fi

# copy the dashboard website configuration file
cp /opt/netperf/dashboard/config/nginx/netperf-dashboard /etc/nginx/sites-available
ln -s /etc/nginx/sites-available/netperf-dashboard /etc/nginx/sites-enabled/netperf-dashboard

# disable the default nginx website (it conflicts with the dashboard app website):
unlink /etc/nginx/sites-enabled/default

# copy the dashboard systemd unit file and enable the service
cp /opt/netperf/dashboard/config/systemd/netperf-dashboard.service /etc/systemd/system
systemctl enable netperf-dashboard.service

# save the settings to the configuration file:
python "$CONFIG_APP" --set data_root --value "$data_root"
python "$CONFIG_APP" --set data_usage_quota_GB --value "$data_usage_quota_GB"
python "$CONFIG_APP" --set enforce_quota --value "$enforce_quota"

# create the reports directory if it doesn't exist:
report_path=$( "$CONFIG_APP" --get report_path )
if [[ ! -d "$report_path" ]]; then
        sudo -u pi mkdir -p "$report_path"
fi

# link the reports directory to the dashboard html directory:
ln -s "$report_path" /opt/netperf/dashboard/html/reports

# detect which speedtest client is installed:
dpkg -s speedtest-cli > /dev/null 2>&1
if [[ "$?" -eq 0 ]]; then
	speedtest_client="speedtest-cli"
else
	dpkg -s speedtest > /dev/null 2>&1
	if [[ "$?" -eq 0 ]]; then
		speedtest_client="ookla"
	else
		echo "Error: a speedtest client is not installed. Please run the package installer script."
		exit 1
	fi
fi
python "$CONFIG_APP" --set speedtest_client --value "$speedtest_client"

# run the interface setup script:
source /opt/netperf/setup_interfaces.sh
