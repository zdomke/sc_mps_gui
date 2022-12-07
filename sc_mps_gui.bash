#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")"

usage(){
    echo "LCLS-SC MPS GUI launcher"
    echo "Usage:" 1>&2
    echo "  sc_mps_gui.bash [ -c | --cud ] [ DBFILE ]" 1>&2
    echo "" 1>&2
    echo "Examples:" 1>&2
    echo "  sc_mps_gui.bash" 1>&2
    echo "  sc_mps_gui.bash  --dbfile ~/database/my_file.db" 1>&2
    echo "For the MPS CUD use:" 1>&2
    echo "  sc_mps_gui.bash  --cud" 1>&2
}
exit_abnormal(){
    usage
    exit 1
}

CUD_MODE="False"
DB_FILE=""

while [ $# -gt 0 ]
do
    case $1 in
        -d | --dbfile) DB_FILE="$2" ;;
        -c | --cud) CUD_MODE="True" ;;
        -h | --help) exit_abnormal ;;
        *) exit_abnormal
    esac
    shift
done

MACROS="P=SIOC:SYS0:MP03, T=TPG:SYS0:1:DST0, CUD=$CUD_MODE"

if [[ -n $DB_FILE ]]
then
    MACROS+=", DB_FILE=$DB_FILE"
fi

pydm --hide-nav-bar --hide-status-bar --hide-menu-bar \
    -m "$MACROS" \
    gui/mps_gui_main.py

exit 0
