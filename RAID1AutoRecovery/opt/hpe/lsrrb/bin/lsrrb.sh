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
if [ ! -d /etc/lsrrb ]; then
	echo "/etc/lsrrb doesn't exist, lsrrb will not be activated"
	exit 1
fi

BOOTCURRENT=`efibootmgr -v | grep BootCurrent | cut -c 14-`
ESP_SOURCE_PARTUUID=`efibootmgr -v | grep $BOOTCURRENT | grep EFI | sed -n 's/^.*HD(\s*\(\S*\))File.*$/\1/p' | cut -d"," -f4`
ESP_SOURCE_PART=`blkid | grep $ESP_SOURCE_PARTUUID | cut -d":" -f1`

echo $ESP_SOURCE_PART > /etc/lsrrb/esp_source_part
echo $ESP_SOURCE_PARTUUID > /etc/lsrrb/esp_source_partuuid

umount /boot/efi
mount PARTUUID=$ESP_SOURCE_PARTUUID /boot/efi

/opt/hpe/lsrrb/bin/md_auto_resync.py &
/opt/hpe/lsrrb/bin/HPEtemp.sh &
