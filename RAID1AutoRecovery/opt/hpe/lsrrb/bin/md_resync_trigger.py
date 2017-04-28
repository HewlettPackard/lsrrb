#!/usr/bin/python
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
GDISK = '/sbin/gdisk'
if not os.path.isfile(GDISK):
    GDISK = '/usr/sbin/gdisk'

# define files
LOG = '/var/log/md_resync_trigger.log'
MDSTAT = '/proc/mdstat'
KEY = '/tmp/md_resync.key'

# print to log file
log = file(LOG, 'a')

def check(new_disk):
    print >> log, 'Start check(' + new_disk + ')...'

    # CHECK #1: Is md in degraded mode?
    print >> log, 'CHECK #1 --- ' + time.strftime("%c")
    mdstat = open(MDSTAT, 'r')
    content = mdstat.read()
    mdstat.close()
    print >> log, content
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
            print >> log, MDADM + ' --detail /dev/' + md
            proc = subprocess.Popen([MDADM, '--detail', '/dev/' + md], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, err = proc.communicate()
            print >> log, output
            if 'degraded' in output:
                outputsplit = output.split()
                outputindex = outputsplit.index('sync') #Status = syncing??
                target = outputsplit[outputindex+1]

                if 'nvme' in output:
                    degraded[md] = target[len(target)-2:len(target)]
                else:
		    degraded[md] = target[len(target)-1]

                print >> log, 'md: ' + md + ', degraded[md]: ' + degraded[md]
                active_disk[md] = []
                if 'nvme' in output:
                    active_disk[md].append(target[5:len(target)-2]) # 5 = length of "/dev/"
                else:
                    active_disk[md].append(target[5:len(target)-1]) # 5 = length of "/dev/"
                print >> log, 'active_disk[md]: ' + str(active_disk[md])
            
            if new_disk in active_disk[md]:
                log.flush()
                return ERR_USED_DISK

    # CHECK #2: Is it healthy?
    print >> log, 'CHECK #2 --- ' + time.strftime("%c")
    print >> log, SMARTCTL + ' -H /dev/' + new_disk
    proc = subprocess.Popen([SMARTCTL, '-H', '/dev/' + new_disk], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = proc.communicate()
    print >> log, output
   
    if 'PASSED' not in output:
        log.flush()
        return ERR_BAD_DISK

    # CHECK #3: Is the capacity equal to the smallest one in the array?
    print >> log, 'CHECK #3 --- ' + time.strftime("%c")
    print >> log, GDISK + ' -l /dev/' + new_disk
    proc = subprocess.Popen([GDISK, '-l', '/dev/' + new_disk], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = proc.communicate()
    print >> log, output
    size_newdisk_index = output.split().index("GiB")
    new_cap = output.split()[size_newdisk_index - 1]
    min_cap = 0
    for md in degraded:
        # Check if the new disk belongs to this degraded md (TBD. currently, always choose the first degraded md)
        if True:
            for disk in active_disk[md]:
                print >> log, GDISK + ' -l /dev/'+ disk 
                proc = subprocess.Popen([GDISK, '-l', '/dev/' + disk], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output, err = proc.communicate()
                size_disk_index = output.split().index("GiB")
                if min_cap < output.split()[size_disk_index - 1]:
                    min_cap = output.split()[size_disk_index -1]
                    break
    print >> log, 'new_cap: '+new_cap+', min_cap: '+min_cap
    if new_cap < min_cap or new_cap > min_cap:
        # Allow the larger capacity (TBD)
        log.flush()
        return ERR_MISMATCH_SIZE

    # CHECK #4: Does the resync key exist?
    print >> log, 'CHECK #4 --- ' + time.strftime("%c")
    if os.path.isfile(KEY) == True:
        log.flush()
        return ERR_KEY_EXISTS

    return 0
    
if __name__ == "__main__":
    # the inserted new disk
    new_disk = sys.argv[1]

    err_code = check(new_disk)
    if err_code < 0:
        print >> log, "Error code: " + str(err_code)
    else:
        # generate the resync 'key'
        print >> log, 'Generate ' + KEY + '\n'
        f = file(KEY, 'w')
        f.write(new_disk)
        f.close()
    log.flush()
log.close()
