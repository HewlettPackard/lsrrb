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
# This script is invoked by the udev rule and does preliminary check
# to indicate recovery is necessary by generating the resync key.
# Rev 1.1 04/26/2017
from __future__ import print_function
from __future__ import unicode_literals
import sys
import subprocess
import time
import os

# define error code
ERR_NO_DEGRADED = -1
ERR_RECOVERY = -2
ERR_USED_DISK = -3
ERR_BAD_DISK = -4
ERR_MISMATCH_SIZE = -5
ERR_KEY_EXISTS = -6

# define commands
MDADM = '/sbin/mdadm'
SMARTCTL = '/opt/hpe/lsrrb/bin/smartctl-static'
if os.path.isfile('/sbin/gdisk'):
    GDISK = '/sbin/gdisk'
elif os.path.isfile('/usr/sbin/gdisk'):
    GDISK = '/usr/sbin/gdisk'
else:
    GDISK = '/opt/hpe/lsrrb/bin/gdisk'
# define files
LOG = '/var/log/md_resync_trigger.log'
MDSTAT = '/proc/mdstat'
KEY = '/tmp/md_resync.key'

# print to log file
log = open(LOG, 'a')

def check(new_disk):
    print('Start check(' + new_disk + ')...', file=log)

    # CHECK #1: Is md in degraded mode?
    print('CHECK #1 --- ' + time.strftime("%c"), file=log)
    mdstat = open(MDSTAT, 'r')
    content = mdstat.read()
    mdstat.close()
    print(content, file=log)
    if 'UU' in content:
        log.flush()
        return ERR_NO_DEGRADED
    if 'recovery' in content:
        log.flush()
        return ERR_RECOVERY

    degraded = {}
    active_disk = {}
    lines = content.split('\n')
    for line1 in lines:
        if 'md' in line1:
            md = line1.split()[0]
            print(MDADM + ' --detail /dev/' + md, file=log)
            proc = subprocess.Popen([MDADM, '--detail', '/dev/' + md], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, err = proc.communicate()
            output = output.decode()
            print(output, file=log)
            if 'degraded' in output:
                outputsplit = output.split()
                outputindex = outputsplit.index('sync') #Status = syncing??
                target = outputsplit[outputindex+1]

                if 'nvme' in output:
                    degraded[md] = target[len(target)-2:len(target)]
                else:
                    degraded[md] = target[len(target)-1]

                print('md: ' + md + ', degraded[md]: ' + degraded[md], file=log)
                active_disk[md] = []
                if 'nvme' in output:
                    active_disk[md].append(target[5:len(target)-2]) # 5 = length of "/dev/"
                else:
                    active_disk[md].append(target[5:len(target)-1]) # 5 = length of "/dev/"
                print('active_disk[md]: ' + str(active_disk[md]), file=log)

            if new_disk in active_disk[md]:
                log.flush()
                return ERR_USED_DISK

    # CHECK #2: Is it healthy?
    print('CHECK #2 --- ' + time.strftime("%c"), file=log)
    print(SMARTCTL + ' -H /dev/' + new_disk, file=log)
    proc = subprocess.Popen([SMARTCTL, '-H', '/dev/' + new_disk], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = proc.communicate()
    output = output.decode()
    print(output, file=log)

    if 'PASSED' not in output:
        log.flush()
        return ERR_BAD_DISK

    # CHECK #3: Is the capacity equal to the smallest one in the array?
    print('CHECK #3 --- ' + time.strftime("%c"), file=log)
    print(GDISK + ' -l /dev/' + new_disk, file=log)
    proc = subprocess.Popen([GDISK, '-l', '/dev/' + new_disk], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = proc.communicate()
    output = output.decode()
    print(output, file=log)
    size_newdisk_index = output.split().index("GiB")
    new_cap = output.split()[size_newdisk_index - 1]
    min_cap = 0
    for md in degraded:
        # Check if the new disk belongs to this degraded md (TBD. currently, always choose the first degraded md)
        if True:
            for disk in active_disk[md]:
                print(GDISK + ' -l /dev/'+ disk, file=log)
                proc = subprocess.Popen([GDISK, '-l', '/dev/' + disk], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output, err = proc.communicate()
                output = output.decode()
                size_disk_index = output.split().index("GiB")
                if min_cap < output.split()[size_disk_index - 1]:
                    min_cap = output.split()[size_disk_index -1]
                    break
    print('new_cap: '+new_cap+', min_cap: '+min_cap, file=log)
    if new_cap < min_cap or new_cap > min_cap:
        # Allow the larger capacity (TBD)
        log.flush()
        return ERR_MISMATCH_SIZE

    # CHECK #4: Does the resync key exist?
    print('CHECK #4 --- ' + time.strftime("%c"), file=log)
    if os.path.isfile(KEY) == True:
        log.flush()
        return ERR_KEY_EXISTS

    return 0

if __name__ == "__main__":
    # the inserted new disk
    new_disk = sys.argv[1]

    err_code = check(new_disk)
    if err_code < 0:
        print("Error code: " + str(err_code), file=log)
    else:
        # generate the resync 'key'
        print('Generate ' + KEY + '\n', file=log)
        f = open(KEY, 'w')
        f.write(new_disk)
        f.close()
    log.flush()
log.close()
