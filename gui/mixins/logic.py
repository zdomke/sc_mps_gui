from functools import partial
from epics import PV
from epics.dbr import DBE_VALUE
from qtpy.QtCore import (Qt, Slot, QModelIndex)
from qtpy.QtWidgets import QHeaderView
from models_pkg.logic_model import (LogicTableModel, LogicSortFilterModel,
                                    LogicItemDelegate)


class LogicMixin:
    def logic_init(self):
        """Initializer for everything in Logic tab: Logic Table Model,
        Logic Item Delegatw, and Selection Details."""
        self.tbl_model = LogicTableModel(self, self.faults,
                                         self.model.config.Session)
        self.delegate = LogicItemDelegate(self)

        self.logic_model = LogicSortFilterModel(self)
        self.logic_model.setSourceModel(self.tbl_model)
        self.logic_model.setFilterByColumn(0, "")
        self.ui.logic_tbl.setModel(self.logic_model)
        self.ui.logic_tbl.setSortingEnabled(True)
        self.ui.logic_tbl.sortByColumn(0, Qt.AscendingOrder)
        self.ui.logic_tbl.hideColumn(9)
        self.ui.logic_tbl.hideColumn(10)
        self.ui.logic_tbl.setItemDelegate(self.delegate)

        self.hdr = self.ui.logic_tbl.horizontalHeader()
        self.hdr.setSectionResizeMode(QHeaderView.Interactive)
        self.hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        self.hdr.resizeSection(1, 125)
        self.hdr.resizeSection(8, 70)
        self.hdr.resizeSection(11, 70)

        self.state_pvs = []
        self.byp_pvs = []
        self.ign_pvs = []
        self.act_pvs = []

        for i, fault in enumerate(self.faults):
            state_pv = PV(f"{fault.name}_TEST",
                          callback=partial(self.send_new_val, row=i),
                          auto_monitor=DBE_VALUE)
            self.state_pvs.append(state_pv)
            byp_pv = PV(f"{fault.name}_SCBYPS",
                        callback=partial(self.send_new_val, row=i),
                        auto_monitor=DBE_VALUE)
            self.byp_pvs.append(byp_pv)
            ign_pv = PV(f"{fault.name}_IGNORED",
                        callback=partial(self.send_new_val, row=i),
                        auto_monitor=DBE_VALUE)
            self.ign_pvs.append(ign_pv)
            act_pv = PV(f"{fault.name}_ACTIVE",
                        callback=partial(self.send_new_val, row=i),
                        auto_monitor=DBE_VALUE)
            self.act_pvs.append(act_pv)

        self.show_row_count()
        self.show_inactive(0)

    def logic_slot_connections(self):
        """Establish slot connections for the logic model and logic tab."""
        # Establish connections for inactive checkbox and filter box
        self.ui.inactive_chck.stateChanged.connect(self.show_inactive)
        self.ui.logic_filter_edt.textChanged.connect(
            partial(self.logic_model.setFilterByColumn, 0))

        # Establish connections for showing the row count
        self.logic_model.rowsRemoved.connect(self.show_row_count)
        self.logic_model.rowsInserted.connect(self.show_row_count)
        self.logic_model.layoutChanged.connect(self.show_row_count)

    def send_new_val(self, value: int, pvname: str, row: int, **kw):
        """Function to emit the appropriate signal based on the pvname."""
        if pvname[-5:] == "_TEST":
            self.tbl_model.new_row_signal.emit(value, row)
        elif pvname[-7:] == "_SCBYPS":
            self.tbl_model.new_byp_signal.emit(pvname[:-7], value, row)
        elif pvname[-8:] == "_IGNORED":
            self.tbl_model.new_act_signal.emit(value, row)
        elif pvname[-7:] == "_ACTIVE":
            self.tbl_model.new_ign_signal.emit(value, row)

    @Slot(int)
    def show_inactive(self, state):
        """Slot called when Inactive Checkbox is toggled. Determines if
        the inactive faults are shown. Only show faults that are active,
        this not including faults that could not establish a connection."""
        if not state:
            self.ui.logic_tbl.hideColumn(11)
            self.logic_model.setFilterByColumn(11, "Y")
        else:
            self.ui.logic_tbl.showColumn(11)
            self.logic_model.removeFilterByColumn(11)

    @Slot()
    def show_row_count(self):
        """When the number of displayed rows changes, update the row
        count at the bottom of the tab."""
        rows = self.logic_model.rowCount(QModelIndex())
        self.ui.num_flts_lbl.setText("Displaying {} / {} Faults"
                                     .format(rows, self.total_faults))
