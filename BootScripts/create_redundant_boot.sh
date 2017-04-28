#!/bin/bash

while true; do
    REDUNDANT_ENTRY=`efibootmgr -v | grep "ubuntu-redundant" | cut -c 5-8`
    if [ "x$REDUNDANT_ENTRY" == "x" ]; then
        break
    else
        echo "Removing previous added redundant boot entry: $REDUNDANT_ENTRY"
        efibootmgr -b $REDUNDANT_ENTRY -B
    fi
done

BOOT_ORDER=`efibootmgr -v | grep "BootOrder" | cut -c 17-`
MAIN_Ubuntu=`efibootmgr -v | grep "ubuntu" | cut -c 5-8`
echo "Adding UEFI boot entry"
efibootmgr -c -d /dev/sdb -p 1 -l \\EFI\\ubuntu\\shimx64.efi -L "ubuntu-redundant"
REDUNDANT_Ubuntu=`efibootmgr -v | grep "ubuntu-redundant" | cut -c 5-8`
echo "Reordering UEFI boot entries"
efibootmgr -o $MAIN_Ubuntu,$REDUNDANT_Ubuntu,$BOOT_ORDER
