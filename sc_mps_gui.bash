#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")"

usage(){
    echo "Run without arguments or with a filename" 1>&2
    echo "Examples:" 1>&2
    echo "  sc_mps_gui.bash" 1>&2
    echo "  sc_mps_gui.bash \$PHYSICS_TOP/mps_configuration/current/mps_config-2022-07-05-a.db" 1>&2
}
exit_abnormal(){
    usage
    exit 1
}

if [[ $# -eq 0 ]]
then
    pydm --hide-nav-bar --hide-status-bar -m "P=SIOC:SYS0:MP03, T=TPG:SYS0:1:DST0" mps_gui_main.py
elif [[ $# -eq 1 ]]
then
    pydm --hide-nav-bar --hide-status-bar -m "P=SIOC:SYS0:MP03, T=TPG:SYS0:1:DST0, DBFILE=$1" mps_gui_main.py
else
    exit_abnormal
fi
exit 0
