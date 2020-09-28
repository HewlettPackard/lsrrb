#!/usr/bin/env python
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
# This script regularly polls if md recovery is needed at background.
# Rev 1.2 05/19/2017

from __future__ import print_function
from __future__ import unicode_literals
import subprocess
import os
import datetime

MDADM = '/sbin/mdadm'
SYNC = 'sync'
DD = '/bin/dd'
if not os.path.isfile(DD):
    DD = '/usr/bin/dd'
LSRRB_ESP_SOURCE_PART = '/etc/lsrrb/esp_source_part'
LOG = '/var/log/md_auto_resync.log'
MDSTAT = '/proc/mdstat'

# print to log file
log = open(LOG, 'a')

def backup_esp():
    # Identify the src to do backup
    src = None
    esp_src = open(LSRRB_ESP_SOURCE_PART, 'r')
    src = esp_src.readline().strip()

    # Get the dst
    dst = None
    if src:
        mdstat = open(MDSTAT, 'r')
        md = None
        part_of_md = False
        for line in mdstat:
            if 'active raid1' in line:
                md = line.split()[0]
        mdstat.close()

        print(MDADM + ' --detail /dev/' + md, file =log)
        proc = subprocess.Popen([MDADM, '--detail', '/dev/' + md], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, err = proc.communicate()
        output = output.decode()
        for line in output.splitlines():
            if 'active sync' in line:
                if src[:-1] == line.split()[6][:-1]:
                    part_of_md = True
                else:
                    dst = line.split()[6][:-1] + '1'
        if not part_of_md:
            print('Error! The md changed, and /boot/efi is not correctly mounted. src: ' + src, file =log)
            return

    # Check if esp backup is necessary (TBD)

    # Start the backup
    if src and dst:
        print(DD + ' if=' + src + ' of=' + dst + ' seek=1 skip=1', file =log)
        subprocess.call([DD, 'if=' + src, 'of=' + dst, 'seek=1', 'skip=1'])
        print(SYNC, file =log)
        subprocess.call([SYNC])

if __name__ == "__main__":
    print('[' + str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + '] backup_esp()', file =log)
    backup_esp()
    log.flush()

log.close()
