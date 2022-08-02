from qtpy.QtCore import Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (QWidget, QTableWidgetItem, QVBoxLayout)
from pydm.widgets.label import PyDMLabel
from pydm.widgets.byte import PyDMByteIndicator


# ~~~~ Widget Constructors ~~~~ #

def construct_state_widget(fault):
    """Create a widget to display the current state of the fault and the
    associated PyDMByteIndicator. The widget is returned.
    """
    state_layout = QVBoxLayout()
    state_layout.setSpacing(0)
    state_layout.setContentsMargins(0, 0, 0, 0)

    fault_state = PyDMLabel(init_channel="ca://{}".format(fault.state))
    fault_state.setAlignment(Qt.AlignCenter)
    fault_state.alarmSensitiveBorder = False
    fault_state.alarmSensitiveContent = True
    state_layout.addWidget(fault_state)
    
    if fault.visible:
        address = "ca://{}_MBBI".format(fault.name)
        byte_state = PyDMByteIndicator(init_channel=address)
        byte_state.numBits = 8
        byte_state.onColor = Qt.red
        byte_state.showLabels = False
        byte_state.orientation = Qt.Horizontal
        state_layout.addWidget(byte_state)
    
    state = QWidget()
    state.setLayout(state_layout)

    return state

def construct_cell_widget(pv):
    """Initialize a PyDMLabel for the associated column and return the
    widget created.
    """
    lbl = PyDMLabel(init_channel="ca://{}".format(pv))
    lbl.setAlignment(Qt.AlignCenter)
    lbl.alarmSensitiveBorder = False
    lbl.alarmSensitiveContent = True

    return lbl

def construct_bypass_widget(fault):
    """Create a button to open the bypass display for the associated
    fault and create a rectangle that alarms when the bypassed fault is
    about to expire. Return the widget created.
    """
    bypass_layout = QVBoxLayout()
    bypass_layout.setSpacing(0)
    bypass_layout.setContentsMargins(0, 0, 0, 0)

    address = "ca://{}.RVAL".format(fault.bypassed)
    bypass_ind = PyDMByteIndicator(init_channel=address)
    bypass_ind.numBits = 1
    bypass_ind.circles = True
    bypass_ind.onColor = Qt.red
    bypass_ind.offColor = QColor(0, 0, 0, 50)
    bypass_ind.showLabels = False
    bypass_layout.addWidget(bypass_ind)

    bypass = QWidget()
    bypass.setLayout(bypass_layout)

    return bypass

def construct_byp_table_row(table, fault, row):
    """In the bypass table, create the widgets and populate the cells of
    a given row with information from the associated fault. The rows
    consist of 3 widgets:
    Fault Description, Fault State, Fault Bypass Expiration.
    """
    item = QTableWidgetItem(fault.description)
    flags = item.flags()
    flags = flags ^ Qt.ItemIsEditable
    item.setFlags(flags)
    table.setItem(row, 0, item)

    lbl = PyDMLabel(init_channel="ca://{}".format(fault.state))
    lbl.setAlignment(Qt.AlignCenter)
    lbl.alarmSensitiveBorder = False
    table.setCellWidget(row, 1, lbl)

    lbl = PyDMLabel(init_channel="ca://{}_END".format(fault.bypassed[:-1]))
    lbl.setAlignment(Qt.AlignCenter)
    lbl.alarmSensitiveBorder = False
    table.setCellWidget(row, 2, lbl)

def construct_table_row(table, fault, row, fault_table=False):
    """In the summary table and logic table, create the widgets and
    populate the cells of a given row with information from the
    associated fault. The rows consist of 9 widgets: Fault Description,
    Fault State, 6 Fault Destination States, and the Bypass Widget.
    """
    item = QTableWidgetItem(fault.description)
    flags = item.flags()
    flags = flags ^ Qt.ItemIsEditable
    item.setFlags(flags)
    table.setItem(row, 0, item)

    state = construct_state_widget(fault)
    table.setCellWidget(row, 1, state)
    
    for j in range(len(fault.destinations)):
        cell = construct_cell_widget(fault.destinations[j])
        table.setCellWidget(row, j+2, cell)

    if fault_table:
        bypass = construct_bypass_widget(fault)
        table.setCellWidget(row, 8, bypass)
