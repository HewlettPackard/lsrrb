Name:          lsrrb
Version:       1.2.0
Release:       6
License:       GPLv3 
Group:         System Environment/Daemons
BuildArch:     x86_64
Summary:       Linux Software Raid Redundant Boot
URL:           http://www.hpe.com/go/proliantlinux
Vendor:        Hewlett-Packard Enterprise
Packager:      Hewlett-Packard Enterprise Linux_SWdeliverables@external.groups.hpe.com

Obsoletes:     minnow

%define _unpackaged_files_terminate_build 0

%description
This package contains scripts and udev rules to mirror the boot volume on HPE ProLiant servers and sets up redundant UEFI boot variables which provide fail-over at boot time.


%files


%dir %attr(0755, root, root) "/opt/hpe"
%dir %attr(0755, root, root) "/opt/hpe/lsrrb"
%dir %attr(0755, root, root) "/opt/hpe/lsrrb/bin"
%attr(0755, root, root) "/opt/hpe/lsrrb/bin/backup_esp.py"
%attr(0755, root, root) "/opt/hpe/lsrrb/bin/lsrrb.sh"
%attr(0755, root, root) "/opt/hpe/lsrrb/bin/HPEtemp.sh"
%attr(0755, root, root) "/opt/hpe/lsrrb/bin/md_resync_trigger.py"
%attr(0755, root, root) "/opt/hpe/lsrrb/bin/md_auto_resync.py"
%attr(0755, root, root) "/opt/hpe/lsrrb/bin/smartctl-static"
%dir %attr(0755, root, root) "/opt/hpe/lsrrb/share/"
%dir %attr(0755, root, root) "/opt/hpe/lsrrb/share/doc"
%attr(0644, root, root) "/opt/hpe/lsrrb/share/doc/README"
%attr(0644, root, root) "/opt/hpe/lsrrb/share/doc/LICENSE"
%attr(0644, root, root) "/etc/udev/rules.d/10-lsrrb.rules"
%attr(0755, root, root) "/etc/systemd/system/lsrrb.service"
%attr(0644, root, root) "/etc/logrotate.d/HPEsdtemplog"
#NOTE:  delete ./etc/init.d/lsrrbd, not used in rpms


%pre -p /bin/sh
:


%post -p /bin/sh
sync
systemctl -q enable lsrrb.service
systemctl start lsrrb.service


%preun -p /bin/sh
if [ $1 -eq 0 ] ; then 
        # Package removal, not upgrade 
        /usr/bin/systemctl --no-reload disable lsrrb.service > /dev/null 2>&1 || : 
        /usr/bin/systemctl stop lsrrb.service > /dev/null 2>&1 || : 
fi 


%postun -p /bin/sh
/usr/bin/systemctl daemon-reload >/dev/null 2>&1 || : 
if [ $1 -ge 1 ] ; then 
        # Package upgrade, not uninstall 
        /usr/bin/systemctl try-restart lsrrb.service >/dev/null 2>&1 || : 
fi 


%changelog
* Sun Aug 27 2017 HPE Linux Development <Linux_SWdeliverables@external.groups.hpe.com> 1.2.0-6
- Fix PARTUUID logic to fit recent libefivar change
* Tue Aug 15 2017 HPE Linux Development <Linux_SWdeliverables@external.groups.hpe.com> 1.2.0-5
- better way to parse PARTUUID		clayc
* Wed Jul 26 2017 HPE Linux Development <Linux_SWdeliverables@external.groups.hpe.com> 1.2.0-4
- add ESP mount options		clayc
* Thu Jul 13 2017 HPE Linux Development <Linux_SWdeliverables@external.groups.hpe.com> 1.2.0-3
- bug fix for mounting /boot/efi	clayc
* Fri Jul 07 2017 HPE Linux Development <Linux_SWdeliverables@external.groups.hpe.com> 1.2.0-3
- minor bug fix for dd    clayc
* Tue May 23 2017 HPE Linux Development <Linux_SWdeliverables@external.groups.hpe.com> 1.2.0-1
- add /opt/hpe/lsrrb/bin/backup_esp.py   craiger
* Thu Apr 27 2017 HPE Linux Development <Linux_SWdeliverables@external.groups.hpe.com> 1.2.0-1
- Rename to lsrrb.  craiger
* Fri Feb 17 2017 HPE Linux Development <Linux_SWdeliverables@external.groups.hpe.com> 1.1.0-1
- Add smartctl-static executable.   craiger
* Tue Oct 11 2016 HPE Linux Development <Linux_SWdeliverables@external.groups.hpe.com> 1.0.0-1
- Add README, RC passed, upgrading version to 1.0.0 0. craiger
* Mon Oct 10 2016 HPE Linux Development <Linux_SWdeliverables@external.groups.hpe.com> 0.0.99-6
* Tue Oct 11 2016 HPE Linux Development <Linux_SWdeliverables@external.groups.hpe.com> 0.0.99-7
- File permissions, script update. craiger
* Mon Oct 10 2016 HPE Linux Development <Linux_SWdeliverables@external.groups.hpe.com> 0.0.99-6
- Few script changes, layout, file perms. craiger
* Tue Sep 27 2016 HPE Linux Development <Linux_SWdeliverables@external.groups.hpe.com> 0.0.99-4
- updated file payload. add bin to paths. craiger
* Fri Sep 23 2016 HPE Linux Development <Linux_SWdeliverables@external.groups.hpe.com> 0.0.99-4
- updated file payload. add hpe to paths. craiger
* Wed Sep 14 2016 HPE Linux Development <Linux_SWdeliverables@external.groups.hpe.com> 0.0.99-3
- updated file payload.  craiger
* Fri Sep 9 2016 HPE Linux Development <Linux_SWdeliverables@external.groups.hpe.com> 0.0.99-2
- remove kickstart content, systemd logic, repackage.  craiger
* Thu Aug 25 2016 HPE Linux Development <Linux_SWdeliverables@external.groups.hpe.com> 0.0.99
- INITIAL packaging.  craiger

