from functools import partial
from qtpy.QtCore import (Qt, Slot)
from qtpy.QtWidgets import QHeaderView
from pydm.widgets import PyDMByteIndicator
from mps_database.models import Condition
from models_pkg.logic_model import (MPSSortFilterModel, MPSItemDelegate)


class IgnoreMixin:
    def ignore_init(self):
        """Initializer for everything in Ignore Logic tab: Ignore Table
        and Ignore Status Bit Indicators."""

        # Create bit indicators for each Ignore status; exclude duplicates
        names = []
        conditions = self.model.config.session.query(Condition).all()
        for i, con in enumerate(conditions):
            con_pv = self.model.name.getConditionPV(con)
            name = con.name.split('_')[0] if "IGNORE" in con.name else con.name
            if name in names:
                continue
            names.append(name)

            wid = PyDMByteIndicator(init_channel=f"ca://{con_pv}")
            wid.circles = True
            wid.labels = [name]
            wid.onColor = Qt.yellow
            wid.offColor = Qt.transparent
            wid.setStyleSheet("font-weight: bold;")
            wid._indicators[0].setMinimumWidth(30)
            wid.layout().setAlignment(wid._labels[0], Qt.AlignLeft)
            self.ui.ignore_status_lyt.insertWidget(self.ui.ignore_status_lyt.count() - 1, wid)

        # Initialize Ignore Table models, delegate, and view
        self.ignore_delegate = MPSItemDelegate(self)
        self.ignore_model = MPSSortFilterModel(self)
        self.ignore_model.setSourceModel(self.tbl_model)

        self.ui.ignore_tbl.setModel(self.ignore_model)
        self.ui.ignore_tbl.sortByColumn(0, Qt.AscendingOrder)
        for i in range(2, self.tbl_model.iind):
            if i in self.tbl_model.conind:
                continue
            self.ui.ignore_tbl.hideColumn(i)
        self.ui.ignore_tbl.setItemDelegate(self.ignore_delegate)

        hdr = self.ui.ignore_tbl.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.resizeSection(1, 125)
        hdr.resizeSection(self.tbl_model.aind, 70)
        hdr.moveSection(self.tbl_model.iind, 3)

        self.show_inactive_ign(0)
        self.show_ignore_row_count()

    def ignore_connections(self):
        """Establish slot connections for the Context Menu, Filter Text
        Edit, Beampath Combobox, and the Row Count Label."""
        self.ui.ignore_filter_edt.textChanged.connect(
            partial(self.ignore_model.setFilterByColumn, 0))
        self.ui.ignore_tbl.customContextMenuRequested.connect(
            self.custom_context_menu)

        self.ui.ignore_beampath_cmbx.currentTextChanged.connect(self.show_beampath_ign)
        self.ui.ignore_inactive_chck.stateChanged.connect(self.show_inactive_ign)

        # Establish connections for showing the row count
        self.ignore_model.rowsRemoved.connect(self.show_ignore_row_count)
        self.ignore_model.rowsInserted.connect(self.show_ignore_row_count)
        self.ignore_model.layoutChanged.connect(self.show_ignore_row_count)

    @Slot(str)
    def show_beampath_ign(self, path):
        """Slot called by the Beampath Combobox to hide/show Ignore
        Table columns based on the Combobox option."""
        if path == "All" or path == "SC_SXR":
            for i in self.tbl_model.conind:
                self.ui.ignore_tbl.showColumn(i)
            if path == "SC_SXR":
                self.ui.ignore_tbl.hideColumn(self.tbl_model.conind[1])
        elif path == "SC_BSYD" or path == "SC_HXR":
            for i in self.tbl_model.conind:
                self.ui.ignore_tbl.hideColumn(i)
            self.ui.ignore_tbl.showColumn(self.tbl_model.conind[0])
            if path == "SC_HXR":
                self.ui.ignore_tbl.showColumn(self.tbl_model.conind[1])

    @Slot(int)
    def show_inactive_ign(self, state):
        """Slot called when Inactive Checkbox is toggled. Determines if
        the inactive faults are shown. Only show faults that are active,
        this not including faults that could not establish a connection."""
        if not state:
            self.ui.ignore_tbl.hideColumn(self.tbl_model.aind)
            self.ignore_model.setFilterByColumn(self.tbl_model.aind, "Y")
        else:
            self.ui.ignore_tbl.showColumn(self.tbl_model.aind)
            self.ignore_model.removeFilterByColumn(self.tbl_model.aind)

    @Slot()
    def show_ignore_row_count(self):
        """When the number of displayed rows changes, update the row
        count at the bottom of the tab."""
        rows = self.ignore_model.rowCount()
        self.ui.ignore_num_flts_lbl.setText(f"Displaying {rows} / {len(self.model.faults)} Faults")
