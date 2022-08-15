from functools import partial
from qtpy.QtCore import Slot
from qtpy.QtWidgets import QHeaderView
from epics import PV
from pydm.widgets.channel import PyDMChannel
from widgets.widget_constructors import *


# ~~~~ Summary Tab ~~~~ #
class SummaryMixin:
    # ~~~~ Summary Table ~~~~ #
    def summary_init(self):
        """Create and connect listener channels for each PV in the
        summary table. Once the channels are connected, set the column
        sizes for the table.
        """
        self.ui.summ_tbl.setRowCount(len(self.faults))

        for i, fault in enumerate(self.faults.values()):
            self.ui.summ_tbl.hideRow(i)
            ch = PyDMChannel(address="ca://{}".format(fault.name),
                             value_slot=partial(self.summ_changed, fault, i))
            self.faulted_channels.append(ch)
            
        for ch in self.faulted_channels:
            ch.connect()

        summ_header = self.ui.summ_tbl.horizontalHeader()

        summ_header.setSectionResizeMode(QHeaderView.Interactive)
        summ_header.setSectionResizeMode(0, QHeaderView.Stretch)
        summ_header.resizeSection(1, 125)

    @Slot(object, int)
    def summ_changed(self, fault, row):
        """When the channels make an initial connection and the value
        changes, then either hide or show the given row. If the row does
        not exist, then initialize it.
        """
        faulted = self.faulted_pvs.setdefault(fault.name, PV(fault.name)).value
        self.set_flt_byp(fault.description, 9, not faulted)

        if not faulted:
            self.ui.summ_tbl.hideRow(row)
        else:
            # Construct the row if it does not already exist
            if not self.ui.summ_tbl.item(row, 0):
                construct_table_row(self.ui.summ_tbl, fault, row)
                
            # Hide the row if fault is ignored
            self.ignored_pvs.setdefault(fault.ignored, PV(fault.ignored))
            if self.ignored_pvs[fault.ignored].value:
                self.ui.summ_tbl.hideRow(row)
            else:
                self.ui.summ_tbl.showRow(row)

    # ~~~~ Bypassed Faults Table ~~~~ #
    def bypass_init(self):
        """Create and connect listener channels for each PV in the
        bypass table. Once the channels are connected, set the column
        sizes for the table.
        """
        self.ui.byp_tbl.setRowCount(len(self.faults))

        for i, fault in enumerate(self.faults.values()):
            self.ui.byp_tbl.hideRow(i)
            ch = PyDMChannel(address="ca://{}".format(fault.bypassed),
                             value_slot=partial(self.byp_changed, fault, i))
            self.bypassed_channels.append(ch)

        for ch in self.bypassed_channels:
            ch.connect()

        byp_fault_header = self.ui.byp_tbl.horizontalHeader()
        byp_fault_header.setSectionResizeMode(QHeaderView.Stretch)

    @Slot(object, int)
    def byp_changed(self, fault, row):
        """When the channels make an initial connection and the value
        changes, then either hide or show the given row. If the row does
        not exist, then initialize it.
        """
        self.bypassed_pvs.setdefault(fault.bypassed, PV(fault.bypassed))
        bypassed = self.bypassed_pvs[fault.bypassed].value
        self.set_flt_byp(fault.description, 10, not bypassed)

        if not bypassed:
            self.ui.byp_tbl.hideRow(row)
        else:
            print(self.bypassed_pvs[fault.bypassed])
            # Construct the row if it does not already exist
            if not self.ui.byp_tbl.item(row, 0):
                construct_byp_table_row(self.ui.byp_tbl, fault, row)
            self.ui.byp_tbl.showRow(row)

    # ~~~~ Ignored Channels ~~~~ #
    def ignored_init(self):
        """Create and connect channels for the pvs containing the
        ignored values.
        """
        for i, fault in enumerate(self.faults.values()):
            ch = PyDMChannel(address="ca://{}".format(fault.ignored),
                             value_slot=partial(self.ignore_changed, fault, i))
            self.ignored_channels.append(ch)

        for ch in self.ignored_channels:
            ch.connect()

    @Slot(object, int)
    def ignore_changed(self, fault, row):
        """When the ignored value changes or connects for the first
        time, either hide or show the associated fault in the summary
        table.
        """
        self.ignored_pvs.setdefault(fault.ignored, PV(fault.ignored))
        ignored = self.ignored_pvs[fault.ignored].value

        if ignored:
            self.ui.summ_tbl.hideRow(row)
        elif self.ui.summ_tbl.item(row, 0):
            self.ui.summ_tbl.showRow(row)