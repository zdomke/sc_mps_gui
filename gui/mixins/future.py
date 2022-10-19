from functools import partial
from qtpy.QtCore import (Qt, Slot)
from qtpy.QtWidgets import (QHeaderView, QLabel, QComboBox)
from epics import PV
from epics.dbr import DBE_VALUE
from mps_database.models import Condition
from models_pkg.future_model import FutureTableModel
from models_pkg.logic_model import (LogicSortFilterModel, LogicItemDelegate)


class FutureMixin:
    def future_init(self):
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

            self.ui.future_filter_lyt.insertWidget(i * 2, lbl)
            self.ui.future_filter_lyt.insertWidget((i * 2) + 1, cbox)

        self.ftr_tbl_model = FutureTableModel(self, self.model,
                                              self.model.config.Session)
        self.ftr_delegate = LogicItemDelegate(self)

        self.ftr_model = LogicSortFilterModel(self)
        self.ftr_model.setSourceModel(self.ftr_tbl_model)
        self.ftr_model.setFilterByColumn(1, "True")
        self.ftr_model.setFilterByColumn(9, "Y")
        self.ui.future_tbl.setModel(self.ftr_model)
        self.ui.future_tbl.setSortingEnabled(True)
        self.ui.future_tbl.sortByColumn(0, Qt.AscendingOrder)
        self.ui.future_tbl.hideColumn(8)
        self.ui.future_tbl.hideColumn(9)
        self.ui.future_tbl.setItemDelegate(self.ftr_delegate)

        self.hdr = self.ui.future_tbl.horizontalHeader()
        self.hdr.setSectionResizeMode(QHeaderView.Interactive)
        self.hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        self.hdr.resizeSection(1, 125)

        self.ftr_pvs = []
        self.show_future_row_count()
        self.set_new_filter(-1, -1)

    def ftr_connections(self):
        """Establish PV and slot connections for the context menus and
        their action."""
        for i, fault in enumerate(self.faults):
            ftr_pv = PV(f"{fault.name}_TEST",
                        callback=partial(self.new_ftr, row=i),
                        auto_monitor=DBE_VALUE)
            self.ftr_pvs.append(ftr_pv)

        for i, box in enumerate(self.box_group):
            box.currentIndexChanged.connect(
                partial(self.set_new_filter, ind=i))

        self.ui.future_filter_edt.textChanged.connect(
            partial(self.ftr_model.setFilterByColumn, 0))
        self.ui.future_tbl.customContextMenuRequested.connect(
            self.custom_context_menu)

        # Establish connections for showing the row count
        self.ftr_model.rowsRemoved.connect(self.show_future_row_count)
        self.ftr_model.rowsInserted.connect(self.show_future_row_count)
        self.ftr_model.layoutChanged.connect(self.show_future_row_count)

    def new_ftr(self, value: int, row: int, **kw):
        """Function to emit the appropriate signal based on the pvname."""
        self.ftr_tbl_model.state_signal.emit(value, row)

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
            self.ftr_model.setExclusionByColumn(8, exclusion_str)
        else:
            self.ftr_model.removeExclusionByColumn(8)
        if filter_str:
            self.ftr_model.setFilterByColumn(8, filter_str)
        else:
            self.ftr_model.removeFilterByColumn(8)

    @Slot()
    def show_future_row_count(self):
        """When the number of displayed rows changes, update the row
        count at the bottom of the tab."""
        rows = self.ftr_model.rowCount()
        self.ui.future_num_flts_lbl.setText("Displaying {} / {} Faults"
                                            .format(rows, len(self.faults)))
