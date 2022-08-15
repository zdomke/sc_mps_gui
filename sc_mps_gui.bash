#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")"

usage(){
    echo "Usage:" 1>&2
    echo "  sc_mps_gui.bash [ DBFILE ]" 1>&2
    echo "" 1>&2
    echo "Examples:" 1>&2
    echo "  sc_mps_gui.bash" 1>&2
    echo "  sc_mps_gui.bash ~/database/my_file.db" 1>&2
}
exit_abnormal(){
    usage
    exit 1
}

if [[ $# -eq 0 ]]
then
    pydm --hide-nav-bar \
        --hide-status-bar \
        -m "P=SIOC:SYS0:MP03, T=TPG:SYS0:1:DST0" \
        gui/mps_gui_main.py
elif [[ $# -eq 1 ]]
then
    pydm --hide-nav-bar \
        --hide-status-bar \
        -m "P=SIOC:SYS0:MP03, T=TPG:SYS0:1:DST0, DBFILE=$1" \
        gui/mps_gui_main.py
else
    exit_abnormal
fi
exit 0
