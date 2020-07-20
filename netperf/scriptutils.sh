#!/bin/bash
# This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
# See the file LICENSE for full license details.

function get_os_id(){
        local os_id=$( cat /etc/os-release | sed -rn 's/^\s+?(ID=)\s+?(.*)/\2/p' | sed 's/\"//g' )
        printf "$os_id"
}

function os_package_installed (){
        local os_package="$1"
        local os_id=$( get_os_id )
        local result=false
        local retcode=1
        if [[ "$os_package" != "" ]]; then
                if [[ "$os_id" == "centos" ]]; then
                        rpm -q "$os_package" > /dev/null 2>&1
                        if [[ "$?" -eq 0 ]]; then
                                result=true
                                retcode=0
                        fi
                else
                        if [[ "$os_id" =~ ^(raspbian|debian)$ ]]; then
                                dpkg -s "$os_package" > /dev/null 2>&1
                                if [[ "$?" -eq 0 ]]; then
                                        result=true
                                        retcode=0
                                fi
                        else
                                result="unsupported_os"
                        fi
                fi
        else
                result="error"
        fi
        printf "$result"
        return "$retcode"
}

function install_os_package (){
	local os_package="$1"
	local os_id=$( get_os_id )
	local return_code
	local result="ok"
	if [[ "$os_id" == "centos" ]]; then
		dnf install -y "$os_package" > /dev/null 2>&1
		return_code="$?"
	else
		if [[ "$os_id" == "raspbian" ]]; then
			apt install -y "$os_package" > /dev/null 2>&1
			return_code="$?"
		else
			result="unsupported_os"
			return_code=1
		fi
	fi
	if [[ "$return_code" -eq 0 ]]; then
		result="ok"
	else
		result="error"
	fi
	printf "$result"
	return "$return_code"
}

function remove_os_package (){
	local os_package="$1"
	local os_id=$( get_os_id )
	local return_code
	local result="ok"
	if [[ "$os_id" == "centos" ]]; then
		sudo dnf remove -y "$os_package" > /dev/null 2>&1
		return_code="$?"
	else
		if [[ "$os_id" == "raspbian" ]]; then
			sudo apt remove -y "$os_package" > /dev/null 2>&1
			return_code="$?"
		else
			result="unsupported_os"
			return_code=1
		fi
	fi
	if [[ "$return_code" -eq 0 ]]; then
		result="ok"
	else
		result="error"
	fi
	printf "$result"
	return "$return_code"
}

function update_repository_cache (){
        local os_id=$( get_os_id )
        if [[ "$os_id" == "centos" ]]; then
                dnf check-update > /dev/null
        else
                if [[ "$os_id" == "raspbian" ]]; then
                        apt update > /dev/null
                fi
        fi
}

function pip_package_installed (){
	local pip_package="$1"
	local installed
	pip3 show "$pip_package" > /dev/null 2>&1
        if [[ "$?" -eq 0 ]]; then
		installed=true
	else
		installed=false
	fi
	printf "$installed"
}


function install_pip_package (){
	local pip_package="$1"
	pip3 install "$pip_package"
	if [[ "$?" -eq 0 ]]; then
		printf "ok"
	else
		printf "error"
	fi
}

function selinux_enforced (){
	local enforced=false
	type getenforce > /dev/null 2>&1
	if [[ "$?" -eq 0 ]]; then
		result=$( getenforce )
		if [[ "$result" == "Enforcing" ]]; then
			enforced=true
		fi
	fi
	printf "$enforced"
}

function firewalld_active (){
	local active=false
	systemctl status firewalld | grep 'active (running)' > /dev/null
	if [[ "$?" -eq 0 ]]; then
		active=true
	fi
	printf "$active"
}
