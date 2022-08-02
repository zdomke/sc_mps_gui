from os import path
from functools import partial
from qtpy.QtCore import Slot
from qtpy.QtWidgets import (QHeaderView, QAbstractItemView)
from epics import PV
from pydm import Display
from pydm.widgets.channel import PyDMChannel
from widget_constructors import *
from mps_model import MPSModel
from selection_detail import SelectionDetail


class MpsGuiDisplay(Display):
    def __init__(self, parent=None, args=[], macros=None):
        super(MpsGuiDisplay, self).__init__(parent=parent, args=args,
                                            macros=macros)
        if 'DBFILE' in macros:
            self.model = MPSModel(macros['DBFILE'])
        else:
            self.model = MPSModel()
        self.faults = self.model.get_faults()
        
        self.faulted_channels = []
        self.bypassed_channels = []
        self.ignored_channels = []
        self.faulted_pvs = {}
        self.bypassed_pvs = {}
        self.ignored_pvs = {}

        self.summary_init()
        self.bypass_init()
        self.ignored_init()
        self.logic_init()

        self.ui.filter_edt.textChanged.connect(self.search_logic_table)
        self.ui.logic_tbl.itemSelectionChanged.connect(self.fault_selected)


    # ~~~~ Summary Tab ~~~~ #
     # ~~ Summary Table ~~ #
    def summary_init(self):
        """Create and connect listener channels for each PV in the
        summary table. Once the channels are connected, set the column
        sizes for the table.
        """
        self.ui.summ_tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.summ_tbl.setRowCount(len(self.faults))

        for i, fault in enumerate(self.faults):
            self.ui.summ_tbl.hideRow(i)
            ch = PyDMChannel(address="ca://{}".format(fault.name),
                             value_slot=partial(self.summ_changed, fault, i))
            self.faulted_channels.append(ch)
            
        for channel in self.faulted_channels:
            channel.connect()

        summ_header = self.ui.summ_tbl.horizontalHeader()

        summ_header.setResizeMode(QHeaderView.Interactive)
        summ_header.setResizeMode(0, QHeaderView.Stretch)
        summ_header.resizeSection(1, 125)

    @Slot(object, int)
    def summ_changed(self, fault, row):
        """When the channels make an initial connection and the value
        changes, then either hide or show the given row. If the row does
        not exist, then initialize it.
        """
        faulted = self.faulted_pvs.setdefault(fault.name, PV(fault.name)).value

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

     # ~~ Bypassed Faults Table ~~ #
    def bypass_init(self):
        """Create and connect listener channels for each PV in the
        bypass table. Once the channels are connected, set the column
        sizes for the table.
        """
        self.ui.byp_tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.byp_tbl.setRowCount(len(self.faults))

        for i, fault in enumerate(self.faults):
            self.ui.byp_tbl.hideRow(i)
            ch = PyDMChannel(address="ca://{}".format(fault.bypassed),
                             value_slot=partial(self.byp_changed, fault, i))
            self.bypassed_channels.append(ch)

        for channel in self.bypassed_channels:
            channel.connect()

        byp_fault_header = self.ui.byp_tbl.horizontalHeader()
        byp_fault_header.setResizeMode(QHeaderView.Stretch)

    @Slot(object, int)
    def byp_changed(self, fault, row):
        """When the channels make an initial connection and the value
        changes, then either hide or show the given row. If the row does
        not exist, then initialize it.
        """
        self.bypassed_pvs.setdefault(fault.bypassed, PV(fault.bypassed))
        bypassed = self.bypassed_pvs[fault.bypassed].value

        if not bypassed:
            self.ui.byp_tbl.hideRow(row)
        else:
            print(self.bypassed_pvs[fault.bypassed])
            # Construct the row if it does not already exist
            if not self.ui.byp_tbl.item(row, 0):
                construct_byp_table_row(self.ui.byp_tbl, fault, row)
            self.ui.byp_tbl.showRow(row)

     # ~~ Ignored Channels ~~ #
    def ignored_init(self):
        """Create and connect channels for the pvs containing the
        ignored values.
        """
        for i, fault in enumerate(self.faults):
            ch = PyDMChannel(address="ca://{}".format(fault.ignored),
                             value_slot=partial(self.ignore_changed, fault, i))
            self.ignored_channels.append(ch)

        for channel in self.ignored_channels:
            channel.connect()

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

    # ~~~~ Logic Tab ~~~~ #
     # ~~ Search Bar ~~ #
    @Slot(str)
    def search_logic_table(self, text):
        """When text is entered in the search bar, only show rows where
        the fault's description contains the given text.
        """
        for i in range(len(self.faults)):
            if text.lower() in self.ui.logic_tbl.item(i, 0).text().lower():
                self.ui.logic_tbl.showRow(i)
            else:
                self.ui.logic_tbl.hideRow(i)

     # ~~ Logic Table ~~ #
    def logic_init(self):
        """For every fault, construct a row in the logic table
        containing information on that fault.
        """
        self.ui.logic_tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.logic_tbl.setRowCount(len(self.faults))

        for i, fault in enumerate(self.faults):
            construct_table_row(self.ui.logic_tbl, fault, i, True)

        faults_header = self.ui.logic_tbl.horizontalHeader()

        faults_header.setResizeMode(QHeaderView.Interactive)
        faults_header.setResizeMode(0, QHeaderView.Stretch)
        faults_header.resizeSection(1, 125)

        self.details = SelectionDetail(parent=self, mps_model=self.model)
        self.details.deselect.connect(self.details_closed)
        self.ui.logic_layout.addWidget(self.details, 2)

    @Slot()
    def fault_selected(self):
        """Slot to be called when the logic_tbl selections change"""
        row = self.ui.logic_tbl.currentRow()
        self.details.set_fault(self.faults[row])
        if self.details.isHidden:
            self.details.show()

    @Slot()
    def details_closed(self):
        """Called when the Selection Details section is closed"""
        self.ui.logic_tbl.clearSelection()
        self.details.hide()

    # ~~~~ PyDM UI File Management ~~~~ #
    @staticmethod
    def ui_filename():
        return 'mps_gui_main.ui'

    def ui_filepath(self):
        return path.join(path.dirname(path.realpath(__file__)),
                         self.ui_filename())
