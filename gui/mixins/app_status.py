from functools import partial
from epics import PV
from epics.dbr import DBE_VALUE
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QHeaderView
from mps_database.models import ApplicationCard
from models_pkg.app_status_model import AppStatusTable


class AppStatusMixin:
    def app_status_init(self):
        """Initializer for the App Status tab."""
        self.apps = self.model.config.session.query(ApplicationCard).all()

        self.app_model = AppStatusTable(self, self.model.config.Session, self.apps)

        # TODO: Sorting does nothing yet. Implement SortFilterProxyModel
        self.ui.app_status_tbl.setModel(self.app_model)
        self.ui.app_status_tbl.sortByColumn(5, Qt.AscendingOrder)

        hdr = self.ui.app_status_tbl.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)

        self.app_pvs = []

    def app_status_connections(self):
        for i, app in enumerate(self.apps):
            app_pv = PV(f"{app.link_node.get_cn_prefix()}:APP{app.number}_STATUS",
                        callback=partial(self.send_app_status, row=i),
                        auto_monitor=DBE_VALUE)
            self.app_pvs.append(app_pv)

    def send_app_status(self, value: int, row: int, **kw):
        self.app_model.status_signal.emit(value, row)
