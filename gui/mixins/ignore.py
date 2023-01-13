from functools import partial
from qtpy.QtCore import (Qt, Slot)
from qtpy.QtWidgets import (QHeaderView, QLabel, QComboBox)
from epics import PV
from epics.dbr import DBE_VALUE
from mps_database.models import Condition
from gui.models_pkg.ignore_model import IgnoreTableModel
from models_pkg.logic_model import (LogicSortFilterModel, LogicItemDelegate)


class IgnoreMixin:
    def ignore_init(self):
        conditions = self.model.config.session.query(Condition).all()

        self.box_group = []
        self.box_states = []
        self.descriptions = []

        for c in conditions:
            c_pv = self.model.name.getConditionPV(c)
            c_state = 0
            if c_pv:
                get_ret = PV(c_pv, connection_timeout=2).get()
                c_state = get_ret + 1 if get_ret is not None else 0

            if c.description not in self.descriptions:
                self.descriptions.append(c.description)
                self.box_states.append(c_state)
            else:
                ind = self.descriptions.index(c.description)
                curr_state = self.box_states[ind]

                self.box_states[ind] = curr_state if curr_state else c_state

        for i, d in enumerate(self.descriptions):
            lbl = QLabel(d)
            cbox = QComboBox()
            cbox.addItems(["Does Not Matter", "Not Active", "Active"])
            cbox.setCurrentIndex(self.box_states[i])
            self.box_group.append(cbox)

            self.ui.ignore_filter_lyt.insertWidget(i * 2, lbl)
            self.ui.ignore_filter_lyt.insertWidget((i * 2) + 1, cbox)

        self.ign_tbl_model = IgnoreTableModel(self, self.model,
                                              self.model.config.Session)
        self.ign_delegate = LogicItemDelegate(self)

        self.ign_model = LogicSortFilterModel(self)
        self.ign_model.setSourceModel(self.ign_tbl_model)
        self.ign_model.setFilterByColumn(1, "True")
        self.ign_model.setFilterByColumn(9, "Y")
        self.ui.ignore_tbl.setModel(self.ign_model)
        self.ui.ignore_tbl.setSortingEnabled(True)
        self.ui.ignore_tbl.sortByColumn(0, Qt.AscendingOrder)
        self.ui.ignore_tbl.hideColumn(8)
        self.ui.ignore_tbl.hideColumn(9)
        self.ui.ignore_tbl.setItemDelegate(self.ign_delegate)

        self.hdr = self.ui.ignore_tbl.horizontalHeader()
        self.hdr.setSectionResizeMode(QHeaderView.Interactive)
        self.hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        self.hdr.resizeSection(1, 125)

        self.ign_pvs = []
        self.show_ignore_row_count()
        self.set_new_filter(-1, -1)

    def ignore_connections(self):
        """Establish PV and slot connections for the context menus and
        their action."""
        for i, fault in enumerate(self.faults):
            ign_pv = PV(f"{fault.name}_TEST",
                        callback=partial(self.new_ignore, row=i),
                        auto_monitor=DBE_VALUE)
            self.ign_pvs.append(ign_pv)

        for i, box in enumerate(self.box_group):
            box.currentIndexChanged.connect(
                partial(self.set_new_filter, ind=i))

        self.ui.ignore_filter_edt.textChanged.connect(
            partial(self.ign_model.setFilterByColumn, 0))
        self.ui.ignore_tbl.customContextMenuRequested.connect(
            self.custom_context_menu)

        # Establish connections for showing the row count
        self.ign_model.rowsRemoved.connect(self.show_ignore_row_count)
        self.ign_model.rowsInserted.connect(self.show_ignore_row_count)
        self.ign_model.layoutChanged.connect(self.show_ignore_row_count)

    def new_ignore(self, value: int, row: int, **kw):
        """Function to emit the appropriate signal based on the pvname."""
        self.ign_tbl_model.state_signal.emit(value, row)

    @Slot(int, int)
    def set_new_filter(self, state, ind):
        """When a QComboBox value changes, change the table's filters."""
        if ind != -1 and "YAG screen" in self.descriptions[ind]:
            if state == 2:
                self.box_states = [0] * len(self.box_states)
                for box in self.box_group:
                    if self.box_group.index(box) == ind:
                        continue
                    box.setEnabled(False)
                    box.blockSignals(True)
                    box.setCurrentIndex(0)
                    box.blockSignals(False)
            else:
                for box in self.box_group:
                    box.setEnabled(True)

        if ind != -1:
            self.box_states[ind] = state

        exclusion_str = ", ".join([d for i, d in enumerate(self.descriptions)
                                   if self.box_states[i] == 1])
        filter_str = ", ".join([d for i, d in enumerate(self.descriptions)
                                if self.box_states[i] == 2])

        if exclusion_str:
            self.ign_model.setExclusionByColumn(8, exclusion_str)
        else:
            self.ign_model.removeExclusionByColumn(8)
        if filter_str:
            self.ign_model.setFilterByColumn(8, filter_str)
        else:
            self.ign_model.removeFilterByColumn(8)

    @Slot()
    def show_ignore_row_count(self):
        """When the number of displayed rows changes, update the row
        count at the bottom of the tab."""
        rows = self.ign_model.rowCount()
        self.ui.ignore_num_flts_lbl.setText("Displaying {} / {} Faults"
                                            .format(rows, len(self.faults)))
