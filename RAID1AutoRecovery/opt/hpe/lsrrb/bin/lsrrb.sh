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
# Rev 1.2 05/19/2017
#
SGDISK="/sbin/sgdisk"
if [[ ! -f "$SGDISK" ]]
then
    SGDISK="/usr/sbin/sgdisk"
fi
if [[ ! -f "$SGDISK" ]]
then
    SGDISK="/opt/hpe/lsrrb/bin/sgdisk"
fi

if [[ ! -d /etc/lsrrb ]]; then
    echo "/etc/lsrrb doesn't exist, lsrrb will not be activated"
    exit 1
fi

BOOTCURRENT=`efibootmgr -v | grep BootCurrent | cut -c 14-`
ESP_SOURCE_PARTUUID_STRING=`efibootmgr -v | grep Boot$BOOTCURRENT`
if [[ $ESP_SOURCE_PARTUUID_STRING == *"GPT"* ]]; then
    ESP_SOURCE_PARTUUID=`echo $ESP_SOURCE_PARTUUID_STRING | cut -d"," -f3`
else
    ESP_SOURCE_PARTUUID=`echo $ESP_SOURCE_PARTUUID_STRING | cut -d"," -f4 | cut -d")" -f1`
fi

SDA_PARTUUID=`$SGDISK --info 1 /dev/sda | grep "unique" | tr /A-Z/ /a-z/ | cut -d" " -f4`
SDB_PARTUUID=`$SGDISK --info 1 /dev/sdb | grep "unique" | tr /A-Z/ /a-z/ | cut -d" " -f4`


if [[ $SDA_PARTUUID == $ESP_SOURCE_PARTUUID ]]; then
    ESP_SOURCE_PART="/dev/sda1"
fi
if [[ $SDB_PARTUUID == $ESP_SOURCE_PARTUUID ]]; then
    ESP_SOURCE_PART="/dev/sdb1"
fi

echo $ESP_SOURCE_PART > /etc/lsrrb/esp_source_part
echo $ESP_SOURCE_PARTUUID > /etc/lsrrb/esp_source_partuuid

umount /boot/efi
mount -o defaults,uid=0,gid=0,umask=0077,shortname=winnt $ESP_SOURCE_PART /boot/efi

/opt/hpe/lsrrb/bin/md_auto_resync.py &
/opt/hpe/lsrrb/bin/HPEtemp.sh &

