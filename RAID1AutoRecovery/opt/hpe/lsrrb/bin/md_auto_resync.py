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
# This script regularly polls if md recovery is needed at background.
# Rev 1.1 04/26/2017

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
SYNC = 'sync'
DD = 'dd'
if not os.path.isfile(DD):
    DD = '/usr/bin/dd'
LS = 'ls'
EFIBOOTMGR = 'efibootmgr'

# define files
LOG = '/var/log/md_auto_resync.log'
MDSTAT = '/proc/mdstat'
PARTUUID = '/dev/disk/by-partuuid'
KEY = '/tmp/md_resync.key'
MOUNTS = '/proc/mounts'

# define cycles
BACKUP_ESP_CYCLE = 1800 # per 30 minutes
#BACKUP_ESP_CYCLE = 30 # debugging

# print to log file
log = file(LOG, 'a')


def resync(new_disk):
    print >> log, 'Start resync(' + new_disk + ')...'

    # Get the degraded md
    mdstat = open(MDSTAT, 'r')
    degraded = {}
    first_active_disk = {} # the partition table to be copied from
    for line1 in mdstat:
        if 'md' in line1:
            md = line1.split()[0]
            print >> log, MDADM + ' --detail /dev/' + md
            proc = subprocess.Popen([MDADM, '--detail', '/dev/' + md], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, err = proc.communicate()
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
    print >> log, 'STEP #1 --- ' + time.strftime("%c")
    for md in degraded:
        print >> log, MDADM + ' /dev/' + md + ' -f /dev/' + new_disk + degraded[md]
        subprocess.call([MDADM, '/dev/' + md, '-f', '/dev/' + new_disk + degraded[md]]) # mark as faulty
        
        print >> log, MDADM + ' /dev/' + md + ' -r /dev/' + new_disk + degraded[md]
        subprocess.call([MDADM, '/dev/' + md, '-r', '/dev/' + new_disk + degraded[md]]) # remove it

        print >> log, MDADM + ' --zero-superblock /dev/' + new_disk + degraded[md]
        subprocess.call([MDADM, '--zero-superblock', '/dev/' + new_disk + degraded[md]])

    # STEP #2: Copy the partition structure to the new disk
    print >> log, 'STEP #2 --- ' + time.strftime("%c")
    src_disk = first_active_disk.itervalues().next() # Temporarily, choose the first degraded md
    print >> log, SGDISK + ' -Z /dev/' + new_disk
    subprocess.call([SGDISK, '-Z', '/dev/' + new_disk], stdout=subprocess.PIPE, stderr=subprocess.PIPE) # destroy the GPT data structures
    print >> log, SGDISK + ' -R /dev/' + new_disk + ' /dev/' + src_disk
    subprocess.call([SGDISK, '-R', '/dev/' + new_disk, '/dev/' + src_disk], stdout=subprocess.PIPE, stderr=subprocess.PIPE) # copy the partition table
    print >> log, SGDISK + ' -G /dev/' + new_disk
    subprocess.call([SGDISK, '-G', '/dev/' + new_disk], stdout=subprocess.PIPE, stderr=subprocess.PIPE) # randomizes the GUID on the disk
    print >> log, SYNC
    subprocess.call([SYNC])

    # STEP #3: Clone the ESP to the new disk
    print >> log, 'STEP #3 --- ' + time.strftime("%c")
    if 'nvme' in src_disk:
	print >> log, DD + ' if=/dev/' + src_disk + 'p1 of=/dev/' + new_disk + 'p1'
    	subprocess.call([DD, 'if=/dev/' + src_disk + 'p1', 'of=/dev/' + new_disk + 'p1'])
    else:
    	print >> log, DD + ' if=/dev/' + src_disk + '1 of=/dev/' + new_disk + '1'
    	subprocess.call([DD, 'if=/dev/' + src_disk + '1', 'of=/dev/' + new_disk + '1'])
    print >> log, SYNC
    subprocess.call([SYNC])

    # STEP #4: Re-create the EFI boot entry
    print >> log, 'STEP #4 --- ' + time.strftime("%c")
    # get UUID of the src_disk's ESP
    print >> log, LS + ' -l ' + PARTUUID
    proc = subprocess.Popen([LS, '-l', PARTUUID], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = proc.communicate()
    uuid = None
    for line in output.splitlines():
        if 'nvme' in src_disk:
            if (src_disk + 'p1') in line:
                uuid = line.split()[8]
                break
        else:
            if (src_disk + '1') in line:
                uuid = line.split()[8]
                break
    if not uuid:
        print >> log, "Error! UUID is NULL."
        return
    print >> log, 'uuid:' + uuid
    # get BootOrder, loader, and the Boot Entry name to be removed
    print >> log, EFIBOOTMGR + ' -v'
    proc = subprocess.Popen([EFIBOOTMGR, '-v'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = proc.communicate()
    print >> log, output
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
    print >> log, 'orig_order:' + orig_order
    print >> log, 'loader:' + loader + ', bootentry_replaced:' + bootentry_replaced
    # remove the Boot Entry
    bootnum_removed = ''
    for line in output.splitlines():
        if 'HD(' not in line:
            continue
        if bootentry_replaced == line[10:line.index('HD(')-1].rstrip():
            bootnum_removed = line[4:8]
    print >> log, EFIBOOTMGR + ' -b ' + bootnum_removed + ' -B'
    subprocess.call([EFIBOOTMGR, '-b', bootnum_removed, '-B'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # add a new Boot Entry and get its Boot Num as well
    print >> log, EFIBOOTMGR + ' -c -d /dev/' + new_disk + ' -p 1 -l ' + loader + ' -L ' + bootentry_replaced
    subprocess.call([EFIBOOTMGR, '-c', '-d', '/dev/'+new_disk, '-p', '1', '-l', loader, '-L', bootentry_replaced], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print >> log, EFIBOOTMGR + ' -v'
    proc = subprocess.Popen([EFIBOOTMGR, '-v'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = proc.communicate()
    print >> log, output
    bootnum_new = ''
    for line in output.splitlines():
        if 'HD(' not in line:
            continue
        if bootentry_replaced == line[10:line.index('HD(')-1].rstrip():
            bootnum_new = line[4:8]
    # reorder the new Boot Entry
    print >> log, 'bootnum_removed:' + bootnum_removed + ', bootnum_new:' + bootnum_new
    new_order = orig_order.replace(bootnum_removed, bootnum_new)
    print >> log, EFIBOOTMGR + ' -o ' + new_order
    subprocess.call([EFIBOOTMGR, '-o', new_order])

    # STEP #5: Add the partitions
    print >> log, 'STEP #5 --- ' + time.strftime("%c")
    for md in degraded:
        print >> log, MDADM + ' --manage /dev/' + md + ' --add /dev/' + new_disk + degraded[md]
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
    mounts = open(MOUNTS, 'r')
    for line in mounts:
        if '/boot/efi' in line:
            src = line.split()[0]
    mounts.close()

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

        print >> log, MDADM + ' --detail /dev/' + md
        proc = subprocess.Popen([MDADM, '--detail', '/dev/' + md], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, err = proc.communicate()
        for line in output.splitlines():
            if 'active sync' in line:
                if src[:-1] == line.split()[6][:-1]:
                    part_of_md = True
                else:
                    dst = line.split()[6][:-1] + '1'
        if not part_of_md:
            print >> log, 'Error! The md changed, and /boot/efi is not correctly mounted. src: ' + src
            return
    
    # Check if esp backup is necessary (TBD)

    # Start the backup
    if src and dst:
        print >> log, DD + ' if=' + src + ' of=' + dst
        subprocess.call([DD, 'if=' + src, 'of=' + dst])
        print >> log, SYNC
        subprocess.call([SYNC])


if __name__ == "__main__":
    # check for the cold-swap case
    print >> log, 'Check if cold-swap occurs...'
    mdstat = open(MDSTAT, 'r')
    content = mdstat.read()
    mdstat.close()
    print >> log, content

    if 'nvme' in content:
        for d in ['nvme0n1', 'nvme1n1']:
            if d not in content:	
                print >> log, 'python /opt/hpe/lsrrb/bin/md_resync_trigger.py ' + d
                os.system('python /opt/hpe/lsrrb/bin/md_resync_trigger.py ' + d)
    else:
        for d in ['sda', 'sdb']:
            if d not in content:
                print >> log, 'python /opt/hpe/lsrrb/bin/md_resync_trigger.py ' + d
                os.system('python /opt/hpe/lsrrb/bin/md_resync_trigger.py ' + d)
    
    log.flush()

    count = 0
    while True:
        # check if there's the resync key
        if os.path.isfile(KEY) == True:
            f = file(KEY, 'r')
            new_disk = f.readline()
            print >> log, 'new_disk: ' + new_disk
            err_code = resync(new_disk)
            if err_code < 0:
                print >> log, "Error code: " + str(err_code)

            print >> log, 'remove ' + KEY + '\n'
            os.remove(KEY)
            log.flush()

        # regularly backup the ESP
        if 0 == count % BACKUP_ESP_CYCLE and is_clean():
            print >> log, '[' + str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + '] backup_esp(), count: ' + str(count)
            backup_esp()
            log.flush()

        time.sleep(1)
        count += 1

log.close()
