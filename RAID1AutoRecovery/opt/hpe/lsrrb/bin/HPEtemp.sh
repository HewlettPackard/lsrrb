#!/bin/bash
# (c) Copyright [2017] Hewlett Packard Enterprise Development LP
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License, version 2, as
# published by the Free Software Foundation; either version 2 of the
# License.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# script to collect Temperature from SCSI/SATA drives and report
# Alerts into /var/log/HPEsdtemp.log for customers , also generates
# alart for disks when greater then 60 degrees temp.
# this script needs smartctl and sg_map packages to be installed
# on the system.
# Rev 1.1 04/26/2017


SMT=/opt/hpe/lsrrb/bin/smartctl-static
LOG=/var/log/HPEsdtemp.log
HDDS=$(/usr/bin/sg_map | awk '{ print $2}')
RED='\033[0;31m'
NC='\033[0m'

ALERT_LEVEL=60
while true; do
DATE=$(date)
	for disk in $HDDS
	do
		if [ -b $disk ]; then
			HDTEMP=$($SMT -A $disk | grep -i Temperature_Celsius | awk '{ print $10}')
			if [ $HDTEMP ]; then
		        echo " $DATE $disk $HDTEMP C " >> $LOG
		        if [ $HDTEMP -ge $ALERT_LEVEL ]; then
		           echo -e " ${RED}$DATE URGENT${NC} Check iLO System Temperature: $disk Temperature is $HDTEMP C Passed CRITICAL limit 60 C " >> $LOG
			fi 
		fi
	fi
	done
sleep 600
done
