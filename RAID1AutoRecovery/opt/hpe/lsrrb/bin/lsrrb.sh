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
# Rev 1.1 04/26/2017
#
/opt/hpe/lsrrb/bin/md_auto_resync.py &
/opt/hpe/lsrrb/bin/HPEtemp.sh &
