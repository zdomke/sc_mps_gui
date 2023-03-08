from functools import partial
from epics import PV
from epics.dbr import DBE_VALUE
from qtpy.QtCore import (Qt, Slot)
from qtpy.QtWidgets import QHeaderView
from models_pkg.logic_model import (LogicTableModel, MPSSortFilterModel,
                                    MPSItemDelegate)


class LogicMixin:
    def logic_init(self, cud_mode=False):
        """Initializer for everything in Logic tab: Logic Table Model,
        Logic Item Delegate, and Selection Details."""
        self.tbl_model = LogicTableModel(self, self.model, self.model.config.Session)
        self.delegate = MPSItemDelegate(self)

        self.logic_model = MPSSortFilterModel(self)
        self.logic_model.setSourceModel(self.tbl_model)

        self.pvs = []

        if not cud_mode:
            self.logic_model.setFilterByColumn(0, "")
            self.ui.logic_tbl.setModel(self.logic_model)
            self.ui.logic_tbl.sortByColumn(0, Qt.AscendingOrder)
            for i in range(self.tbl_model.conind[0], self.tbl_model.aind):
                self.ui.logic_tbl.hideColumn(i)
            self.ui.logic_tbl.setItemDelegate(self.delegate)

            hdr = self.ui.logic_tbl.horizontalHeader()
            hdr.setSectionResizeMode(QHeaderView.Interactive)
            hdr.setSectionResizeMode(0, QHeaderView.Stretch)
            hdr.resizeSection(1, 125)
            hdr.resizeSection(self.tbl_model.bind, 70)
            hdr.resizeSection(self.tbl_model.aind, 70)

            self.show_inactive(0)
            self.show_row_count()

    def logic_connections(self, cud_mode=False):
        """Establish PV and slot connections for the logic model and
        logic tab."""
        for i, fault in enumerate(self.model.faults):
            state_pv = PV(fault.name,
                          callback=partial(self.send_new_val, row=i),
                          auto_monitor=DBE_VALUE)
            self.pvs.append(state_pv)
            byp_pv = PV(f"{fault.name}_SCBYPS",
                        callback=partial(self.send_new_val, row=i),
                        auto_monitor=DBE_VALUE)
            self.pvs.append(byp_pv)
            ign_pv = PV(f"{fault.name}_IGNORED",
                        callback=partial(self.send_new_val, row=i),
                        auto_monitor=DBE_VALUE)
            self.pvs.append(ign_pv)
            act_pv = PV(f"{fault.name}_ACTIVE",
                        callback=partial(self.send_new_val, row=i),
                        auto_monitor=DBE_VALUE)
            self.pvs.append(act_pv)

        if not cud_mode:

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
        if pvname[-4:] == "_FLT":
            self.tbl_model.state_signal.emit(value, row)
        elif pvname[-7:] == "_SCBYPS":
            self.tbl_model.byp_signal.emit(pvname[:-7], value, row)
        elif pvname[-8:] == "_IGNORED":
            self.tbl_model.ign_signal.emit(value, row)
        elif pvname[-7:] == "_ACTIVE":
            self.tbl_model.act_signal.emit(value, row)

    @Slot(int)
    def show_inactive(self, state):
        """Slot called when Inactive Checkbox is toggled. Determines if
        the inactive faults are shown. Only show faults that are active,
        this not including faults that could not establish a connection."""
        if not state:
            self.ui.logic_tbl.hideColumn(self.tbl_model.aind)
            self.logic_model.setFilterByColumn(self.tbl_model.aind, "Y")
        else:
            self.ui.logic_tbl.showColumn(self.tbl_model.aind)
            self.logic_model.removeFilterByColumn(self.tbl_model.aind)

    @Slot()
    def show_row_count(self):
        """When the number of displayed rows changes, update the row
        count at the bottom of the tab."""
        rows = self.logic_model.rowCount()
        self.ui.num_flts_lbl.setText(f"Displaying {rows} / {len(self.model.faults)} Faults")
