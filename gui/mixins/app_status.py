from functools import partial
from epics import PV
from epics.dbr import DBE_VALUE
from qtpy.QtCore import (Qt, Slot)
from qtpy.QtWidgets import QHeaderView
from mps_database.models import ApplicationCard
from models_pkg.logic_model import MPSSortFilterModel
from models_pkg.app_status_model import (AppStatusTable, RelatedDisplayDelegate)


class AppStatusMixin:
    def app_status_init(self):
        """Initializer for the App Status tab."""
        self.apps = self.model.config.session.query(ApplicationCard).all()

        self.app_tbl_model = AppStatusTable(self, self.model.config.Session, self.apps)
        self.rd_button_delegate = RelatedDisplayDelegate(self.ui.app_status_tbl)

        self.app_model = MPSSortFilterModel(self)
        self.app_model.setSourceModel(self.app_tbl_model)

        self.ui.app_status_tbl.setModel(self.app_model)
        self.ui.app_status_tbl.sortByColumn(self.app_tbl_model.sind, Qt.AscendingOrder)

        self.ui.app_status_tbl.setItemDelegate(self.delegate)
        self.ui.app_status_tbl.setItemDelegateForColumn(self.app_tbl_model.gdind, self.rd_button_delegate)
        for row in range(len(self.apps)):
            self.ui.app_status_tbl.openPersistentEditor(self.app_model.index(row, self.app_tbl_model.gdind))

        hdr = self.ui.app_status_tbl.horizontalHeader()
        hdr.setSectionResizeMode(self.app_tbl_model.sind, QHeaderView.Stretch)
        hdr.resizeSection(self.app_tbl_model.gdind, 100)

        self.app_pvs = []

    def app_status_connections(self):
        """Establish App Status connections with PVs and Signals."""
        for i, app in enumerate(self.apps):
            app_pv = PV(f"{app.link_node.get_cn_prefix()}:APP{app.number}_STATUS",
                        callback=partial(self.send_app_status, row=i),
                        auto_monitor=DBE_VALUE)
            self.app_pvs.append(app_pv)

            self.ui.app_status_filter_edt.textChanged.connect(self.search_app_status)
            self.ui.app_status_filter_cmbx.currentIndexChanged.connect(self.search_app_status)

            # Establish connections for showing the row count
            self.app_model.rowsRemoved.connect(self.show_app_row_count)
            self.app_model.rowsInserted.connect(self.show_app_row_count)
            self.app_model.layoutChanged.connect(self.show_app_row_count)

    def send_app_status(self, value: int, row: int, **kw):
        """Function to emit the status signal in the model."""
        self.app_tbl_model.status_signal.emit(value, row)

    @Slot()
    def search_app_status(self):
        col = self.ui.app_status_filter_cmbx.currentIndex()
        if col == self.app_tbl_model.lnind:
            self.app_model.removeFilterByColumn(self.app_tbl_model.gind)
        elif col == self.app_tbl_model.gind:
            self.app_model.removeFilterByColumn(self.app_tbl_model.lnind)

        txt = self.ui.app_status_filter_edt.currentText()
        self.app_model.setFilterByColumn(col, txt)

    @Slot()
    def show_app_row_count(self):
        """When the number of displayed rows changes, update the row
        count at the bottom of the tab."""
        rows = self.app_model.rowCount()
        self.ui.num_apps_lbl.setText(f"Displaying {rows} / {len(self.apps)} Faults")
