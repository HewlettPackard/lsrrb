#!/bin/bash

### Custom bash script for
### SmartStart Scripting Toolkit for Linux v10.40
### June 2016
### JimmyV

sleep 5s
clear
setterm -blank 0 -powersave off

MNTDIR=/tmp/$$-tmpmnt

# needed for hwquery and ifhw
ALLBOARDS=/opt/hp/hp-scripting-tools/etc/allboards.xml

# running hpdiscovery detect discs and controllers
hpdiscovery -f ${HWDISC_FILE}

check_mounts() {
     echo "Checking for any disks mounted"
     while IFS= read -r mounted; 
       do umount ${mounted}
       echo "Done..."
     done < <(mount | grep "sd" | awk '{print $1}')
     
}

check_err() {
    if [ "${1}" -ne "0" ] ; then
        echo >/dev/null 2>&1
        echo "ERROR(${1}): ${2}" >/dev/null 2>&1
        echo >/dev/null 2>&1
        exit "${1}"
    fi
}

#Test to see if Dynamic Smart Array is enabled
echo "Checking to see if system reports an enabled HPE Dynamic Smart Array Controller"
ifhw ${HWDISC_FILE} ${ALLBOARDS} "PCI:Dynamic Smart Array" 
if [ $? = 0 ];
    then
    cd ${TOOLKIT}
    echo "*** Active controller found, disabling......"
    conrep -l -f ${TOOLKIT_DATA_FILES}/dyn_raid_disable.dat
    check_err $? "Unable to disable Dynamic Smart Array"

    ### Set EV in UEFI to bypass section on reboot after disabling Dynamic RAID controller
    echo -e "*** Setting SWRAID to 1 in System ROM ***\n"
    statemgr -W SWRAID 1 
    check_err $? "Unable to set UEFI EV"

    sleep 5s


    ### End System ROM configuration
    cd ${TOOLKIT}
    echo -e "*** Completed hardware configuration...\n"
    echo -e "*** Rebooting system to continue setup...\n"
    sleep 2s
    cd ${TOOLKIT}
    reboot

  else
    echo "System reports HPE Dynamic Smart Array already disabled"
fi
sleep 2s

echo -e "*** Configuring disk partitions and file systems\n"

disk1=/dev/sda
disk2=/dev/sdb

# forcibly unmount the device in case any automounters are at work
check_mounts 

#get total memory to determine swap size
export `hwquery ${HWDISC_FILE} ${ALLBOARDS} "Total_RAM=TotalRAM"`
SwapSize=$(( ${Total_RAM} * 2 ))
#find end sector of disk
export EndSector=`sgdisk -E ${disk1}` 

sgdisk -Zog ${disk1} 
sgdisk -n 1:2048:+200M -c 1:"EFI System Partition" -t 1:ef00 ${disk1} 
#sgdisk -n 2:0:+500M -c 2:"Microsoft Basic Data" -t 2:0700 ${disk1} 
#sgdisk -n 3:0:+${SwapSize}M -c 3:"Linux Swap" -t 3:8200 ${disk1} 
#sgdisk -n 4:0:${EndSector} -c 4:"Linux" -t 4:8300 ${disk1}


# clone disks
#sgdisk -R${disk2} ${disk1}
#sgdisk -Gg ${disk2}
sgdisk --re-read ${disk1}

check_mounts

sleep 5s

echo "Creating filesystems on ${disk1}"
mkdosfs -F32 "${disk1}1"
sleep 2s
mkdir -p $MNTDIR 
echo "Copying boot files to ${disk1}1"
mount ${disk1}1 $MNTDIR 
mkdir -p $MNTDIR/efi/boot 

cp ${TOOLKIT_MNTPNT}/install/* $MNTDIR/efi/boot/

#clear EV used to set state for Dynamic RAID disable reboot
statemgr -W SWRAID 

cat <<END
Disk partitions created, installation media setup on device ${disk1}
END

#Change boot order to boot from HD first
cat <<END
Change RBSU boot order to boor from HD first
END

setbootorder hd usb floppy cdrom pxe

sync
umount -a

cat <<END
System reboot after 20 seconds
END

sleep 20s
reboot
# One time boot to first hard drive
#reboot c:

