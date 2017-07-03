# Step 1: Remove Minnow
Description: Stop Minnow service and remove Minnow package

    # systemctl stop minnow
    # rpm -qa | grep minnow
    minnow-1.1.0-2.x86_64
    # rpm -e minnow-1.1.0-2.x86_64
    # rm -rf /opt/hpe/minnow

# Step 2: Prerequisite for LSRRB package installation
Description: In LSRRB we added a mechanism to make sure that an accident rpm package installtion will not execute. If those prerequisites can not be satsified, LSRRB won't run. So here we need to satisfy the LSRRB prerequisites. These prequisite can be found in the new KickStart file.

Generate a bash script (upgrade_lsrrb.sh) containing the following lines:

    #!/bin/bash
    
    mkdir -p /etc/lsrrb
    PARTUUID=`sgdisk --info 1 /dev/sda | grep "unique" | tr /A-Z/ /a-z/ | cut -d" " -f4`
    echo "/dev/sda1" > /etc/lsrrb/esp_source_part
    echo $PARTUUID > /etc/lsrrb/esp_source_partuuid

* Note: the above lines assume /dev/sda1 is the current booting volume. Replace with correct one when needed.

# Step 3: Install LSRRB package

  \# rpm -ivh lsrrb-1.2.0-2.x86_64.rpm
