#!/bin/bash
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

# This script is used to manage the scheduled tasks, including network performance tests, database pruning,
# and report generation. The tasks are scheduled via systemd timers, each timer triggers a corresponding
# service unit file.

username=$(/opt/netperf/netperf_settings.py --get username)

usage_info=\
"This script is used to manage the systemd timer and unit files that run various scheduled tasks for the $username user
including network speed tests, database cleanup, and report generation.

usage: $0 <command>

supported commands:
	start    enables and starts all installed timers
	stop     disables and stops all installed timers
	show     lists installed timers
	reload   reloads the timer configuration files (used for applying changes made to the task schedules)
	install  installs timers by creating links in /etc/systemd/user to the files in /opt/netperf/config/systemd/tasks"

TASKS=( netperf-test-isp netperf-test-local netperf-test-dns netperf-test-ping netperf-prune-db netperf-report )
SOURCE_DIR="/opt/netperf/config/systemd/tasks"
TARGET_DIR="/etc/systemd/user"
uid=$(id -u "$username")
sudo systemctl start user@"$uid"
command="$1"
show_schedules=false
reload=false
case "$command" in
	"start")
		startstop="start"
		enabledisable="enable"
		show_schedules=true
		reload=true
		printf "Enabling and starting Network Performance Monitor tasks.\n"
		;;
	"stop")
		startstop="stop"
		enabledisable="disable"
		printf "Disabling and stopping Network Performance Monitor tasks.\n"
		;;
	"show")
		show_schedules=true
		;;
	"reload")
		show_schedules=true
		reload=true
		printf "Reloading Network Performance Monitor task configuration files.\n"
		;;
	"install")
		show_schedules=true
		reload=true
		printf "Installing  Network Performance Monitor tasks.\n"
		;;
	*)
		printf "%b%s\n" "$usage_info"
		#printf "Usage info:\n$0 <start|stop|reload|show|install>\n"
		exit 1
		;;
esac

if [[ $EUID -ne 0 ]]; then
	script_name=$(basename $0)
	printf "This script must be run as root, e.g:\nsudo ./%s" "$script_name"
	exit 1
fi

cmd_prefix=$(printf "sudo -u ${username} DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$uid/bus")

if [[ "$command" =~ ("start"|"stop") ]]; then
	for timer in "${TASKS[@]}"; do
		eval "${cmd_prefix} systemctl --user ${enabledisable} ${timer}.timer > /dev/null 2> /dev/null"
		eval "${cmd_prefix} systemctl --user ${startstop} ${timer}.timer > /dev/null 2> /dev/null"
	done
fi

if [[ "$command" == "install" ]]; then
	for task in "${TASKS[@]}"; do
		source_unit_file="$SOURCE_DIR/${task}.service"
		source_timer_file="$SOURCE_DIR/${task}.timer"
		target_unit_link="$TARGET_DIR/${task}.service"
		target_timer_link="$TARGET_DIR/${task}.timer"
		if ! [[ -f "$source_unit_file" ]]; then
			printf "Error: unit file $source_unit_file not found.\n"
			exit 1
		fi
		if ! [[ -f "$source_timer_file" ]]; then
			printf "Error: timer file $source_timer_file not found.\n"
			exit 1
		fi
		sudo ln -s "$source_unit_file" "$target_unit_link" 2> /dev/null
		sudo ln -s "$source_timer_file" "$target_timer_link" 2> /dev/null
		eval "${cmd_prefix} systemctl --user enable ${task}.timer > /dev/null" 2> /dev/null
	done
fi

if [[ "$reload" == true ]]; then
	eval "${cmd_prefix} systemctl --user daemon-reload 1> /dev/null 2> /dev/null"
fi

if [[ "$show_schedules" == true ]]; then
	printf "Network Performance Monitor tasks:\n"
	eval "${cmd_prefix} systemctl --user list-timers --all 2> /dev/null"
fi
