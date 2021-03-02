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
import sys
import subprocess
import time
import os
import datetime
import md_resync_trigger

# define commands
MDADM = '/sbin/mdadm'
SGDISK = '/sbin/sgdisk'
if not os.path.isfile(SGDISK):
    SGDISK = '/usr/sbin/sgdisk'
if not os.path.isfile(SGDISK):
    SGDISK = '/opt/hpe/lsrrb/bin/sgdisk'
SYNC = 'sync'
DD = '/bin/dd'
if not os.path.isfile(DD):
    DD = '/usr/bin/dd'
LS = 'ls'
EFIBOOTMGR = 'efibootmgr'

# define files
LOG = '/var/log/md_auto_resync.log'
MDSTAT = '/proc/mdstat'
KEY = '/tmp/md_resync.key'
MOUNTS = '/proc/mounts'
LSRRB_ESP_SOURCE_PART = '/etc/lsrrb/esp_source_part'

# define cycles
BACKUP_ESP_CYCLE = 1800 # per 30 minutes
#BACKUP_ESP_CYCLE = 30 # debugging

# print to log file
log = open(LOG, 'a')


def resync(new_disk):
    print('Start resync(' + new_disk + ')...', file =log)

    # Get the degraded md
    mdstat = open(MDSTAT, 'r')
    degraded = {}
    first_active_disk = {} # the partition table to be copied from
    for line1 in mdstat:
        if 'md' in line1:
            md = line1.split()[0]
            print(MDADM + ' --detail /dev/' + md, file=log)
            proc = subprocess.Popen([MDADM, '--detail', '/dev/' + md], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, err = proc.communicate()
            output = output.decode()
            if 'degraded' in output:
                outputsplit = output.split()
                outputindex = outputsplit.index('sync')
                target = outputsplit[outputindex+1]

                if 'nvme' in output:
                    degraded[md] = target[len(target)-2: len(target)]
                else:
                    degraded[md] = target[len(target)-1]

                if 'nvme' in output:
                    first_active_disk[md] = (target[5:len(target)-2])
                else:
                    first_active_disk[md] = (target[5:len(target)-1])

    mdstat.close()

    if not degraded:
        log.flush()
        return md_resync_trigger.ERR_NO_DEGRADED

    # STEP #1: Clean/remove the faulty disk from the degraded md
    print('STEP #1 --- ' + time.strftime("%c"), file =log)
    for md in degraded:
        print(MDADM + ' /dev/' + md + ' -f /dev/' + new_disk + degraded[md], file =log)
        subprocess.call([MDADM, '/dev/' + md, '-f', '/dev/' + new_disk + degraded[md]]) # mark as faulty

        print(MDADM + ' /dev/' + md + ' -r /dev/' + new_disk + degraded[md], file =log)
        subprocess.call([MDADM, '/dev/' + md, '-r', '/dev/' + new_disk + degraded[md]]) # remove it

        print(MDADM + ' --zero-superblock /dev/' + new_disk + degraded[md], file =log)
        subprocess.call([MDADM, '--zero-superblock', '/dev/' + new_disk + degraded[md]])

    # STEP #2: Copy the partition structure to the new disk
    print('STEP #2 --- ' + time.strftime("%c"), file =log)
    if sys.version_info[0] < 3:
        src_disk = first_active_disk.itervalues().next() # Temporarily, choose the first degraded md for Python 2.x
    else:
        src_disk = next(iter(first_active_disk.values())) # Temporarily, choose the first degraded md
    print(SGDISK + ' -Z /dev/' + new_disk, file =log)
    subprocess.call([SGDISK, '-Z', '/dev/' + new_disk], stdout=subprocess.PIPE, stderr=subprocess.PIPE) # destroy the GPT data structures
    print(SGDISK + ' -R /dev/' + new_disk + ' /dev/' + src_disk, file =log)
    subprocess.call([SGDISK, '-R', '/dev/' + new_disk, '/dev/' + src_disk], stdout=subprocess.PIPE, stderr=subprocess.PIPE) # copy the partition table
    print(SGDISK + ' -G /dev/' + new_disk, file =log)
    subprocess.call([SGDISK, '-G', '/dev/' + new_disk], stdout=subprocess.PIPE, stderr=subprocess.PIPE) # randomizes the GUID on the disk
    print(SYNC, file =log)
    subprocess.call([SYNC])

    # STEP #3: Clone the ESP to the new disk
    print('STEP #3 --- ' + time.strftime("%c"), file =log)
    if 'nvme' in src_disk:
        print(DD + ' if=/dev/' + src_disk + 'p1 of=/dev/' + new_disk + 'p1' + ' seek=1 skip=1', file =log)
        subprocess.call([DD, 'if=/dev/' + src_disk + 'p1', 'of=/dev/' + new_disk + 'p1', 'seek=1', 'skip=1'])
    else:
        print(DD + ' if=/dev/' + src_disk + '1 of=/dev/' + new_disk + '1' + ' seek=1 skip=1', file =log)
        subprocess.call([DD, 'if=/dev/' + src_disk + '1', 'of=/dev/' + new_disk + '1', 'seek=1', 'skip=1'])
    print(SYNC, file =log)
    subprocess.call([SYNC])

    # STEP #4: Re-create the EFI boot entry
    print('STEP #4 --- ' + time.strftime("%c"), file =log)
    # get UUID of the src_disk's ESP
    print(SGDISK + ' --info 1 /dev/' + src_disk, file =log)
    proc = subprocess.Popen([SGDISK, '--info', '1', '/dev/' + src_disk], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    output, err = proc.communicate()
    output = output.decode()
    target = output.splitlines()
    target = target[1]
    target = target.split()
    uuid = target[3]
    uuid = uuid.lower()
    if len(uuid) !=36:
        uuid = None
    if not uuid:
        print("Error! UUID is NULL.", file =log)
        return
    print('uuid:' + uuid, file =log)
    # get BootOrder, loader, and the Boot Entry name to be removed
    print(EFIBOOTMGR + ' -v', file =log)
    proc = subprocess.Popen([EFIBOOTMGR, '-v'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = proc.communicate()
    output = output.decode()
    print(output, file =log)
    for line in output.splitlines():
        if 'BootOrder' in line:
            orig_order = line[11:]
        if uuid in line:
            bootentry_alive = line[10:line.index('HD(')-1].rstrip()
            loader = line[line.index('File')+5:-1]
    if '-redundant' in bootentry_alive:
        bootentry_replaced = bootentry_alive[0:-10]
    else:
        bootentry_replaced = bootentry_alive + '-redundant'
    print('orig_order:' + orig_order, file =log)
    print('loader:' + loader + ', bootentry_replaced:' + bootentry_replaced, file =log)
    # remove the Boot Entry
    bootnum_removed = ''
    for line in output.splitlines():
        if 'HD(' not in line:
            continue
        if bootentry_replaced == line[10:line.index('HD(')-1].rstrip():
            bootnum_removed = line[4:8]
    print(EFIBOOTMGR + ' -b ' + bootnum_removed + ' -B', file =log)
    subprocess.call([EFIBOOTMGR, '-b', bootnum_removed, '-B'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # add a new Boot Entry and get its Boot Num as well
    print(EFIBOOTMGR + ' -c -d /dev/' + new_disk + ' -p 1 -l ' + loader + ' -L ' + bootentry_replaced, file =log)
    subprocess.call([EFIBOOTMGR, '-c', '-d', '/dev/'+new_disk, '-p', '1', '-l', loader, '-L', bootentry_replaced], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(EFIBOOTMGR + ' -v', file =log)
    proc = subprocess.Popen([EFIBOOTMGR, '-v'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = proc.communicate()
    output = output.decode()
    print(output, file =log)
    bootnum_new = ''
    for line in output.splitlines():
        if 'HD(' not in line:
            continue
        if bootentry_replaced == line[10:line.index('HD(')-1].rstrip():
            bootnum_new = line[4:8]
    # reorder the new Boot Entry
    print('bootnum_removed:' + bootnum_removed + ', bootnum_new:' + bootnum_new, file =log)
    new_order = orig_order.replace(bootnum_removed, bootnum_new)
    print(EFIBOOTMGR + ' -o ' + new_order, file =log)
    subprocess.call([EFIBOOTMGR, '-o', new_order])

    # STEP #5: Add the partitions
    print('STEP #5 --- ' + time.strftime("%c"), file =log)
    for md in degraded:
        print(MDADM + ' --manage /dev/' + md + ' --add /dev/' + new_disk + degraded[md], file =log)
        subprocess.call([MDADM, '--manage', '/dev/' + md, '--add', '/dev/' + new_disk + degraded[md]])

    return 0


def is_clean():
    # Check if the md is in clean state...
    #print >> log, 'Check if the md is in clean state...'
    mdstat = open(MDSTAT, 'r')
    content = mdstat.read()
    mdstat.close()
    if 'UU' in content:
        return True
    return False


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
                break
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
    # check for the cold-swap case
    print ('Check if cold-swap occurs...', file =log)
    mdstat = open(MDSTAT, 'r')
    content = mdstat.read()
    mdstat.close()
    print(content, file =log)

    if 'nvme' in content:
        for d in ['nvme0n1', 'nvme1n1']:
            if d not in content:
                print('python /opt/hpe/lsrrb/bin/md_resync_trigger.py ' + d, file =log)
                os.system('python /opt/hpe/lsrrb/bin/md_resync_trigger.py ' + d)
    else:
        for d in ['sda', 'sdb']:
            if d not in content:
                print('python /opt/hpe/lsrrb/bin/md_resync_trigger.py ' + d, file=log)
                os.system('python /opt/hpe/lsrrb/bin/md_resync_trigger.py ' + d)

    log.flush()

    count = 0
    while True:
        # check if there's the resync key
        if os.path.isfile(KEY) == True:
            f = open(KEY, 'r')
            new_disk = f.readline()
            print('new_disk: ' + new_disk, file=log)
            err_code = resync(new_disk)
            if err_code < 0:
                print("Error code: " + str(err_code), file=log)

            print('remove ' + KEY + '\n', file=log)
            os.remove(KEY)
            log.flush()

        # regularly backup the ESP
        if 0 == count % BACKUP_ESP_CYCLE and is_clean():
            print('[' + str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + '] backup_esp(), count: ' + str(count), file = log)
            backup_esp()
            log.flush()

        time.sleep(1)
        count += 1

log.close()

