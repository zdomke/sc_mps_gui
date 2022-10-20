from qtpy.QtCore import (Qt, Slot, Signal, QPoint, QTimer, QModelIndex,
                         QSortFilterProxyModel)
from qtpy.QtWidgets import (QHeaderView, QMenu)
from models_pkg.recent_faults_model import RecentFaultsTableModel
from history.tools.HistoryAPI import HistoryAPI


# ~~~~ Recent Faults Tab ~~~~ #
class RecentFaultsMixin:
    rcnt_refresh = Signal()

    def recent_init(self):
        """Connect to mps_history database, initialize the faults table
        model and sort/filter proxy model, create a custom context menu,
        initialize the refresh timer, and connect all necessary signals.
        """
        self.hist = HistoryAPI(True)
        self.recent_mdl = RecentFaultsTableModel(
            self, self.hist.history_conn.session)
        self.recent_prxmdl = QSortFilterProxyModel(self)
        self.recent_prxmdl.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.recent_prxmdl.setFilterKeyColumn(1)

        self.recent_prxmdl.setSourceModel(self.recent_mdl)
        self.ui.recent_tbl.setModel(self.recent_prxmdl)
        self.ui.recent_tbl.setItemDelegate(self.delegate)

        recent_header = self.ui.recent_tbl.horizontalHeader()
        recent_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        recent_header.setSectionResizeMode(1, QHeaderView.Stretch)
        recent_header.resizeSection(2, 125)

        self.recent_menu = QMenu(self)
        self.recent_menu.addAction(self.action)

        self.show_recent_count()
        self.timer = QTimer()
        self.timer.setInterval(1000)

    def recent_connections(self):
        # Row count connections
        self.recent_prxmdl.rowsRemoved.connect(self.show_recent_count)
        self.recent_prxmdl.rowsInserted.connect(self.show_recent_count)
        self.recent_prxmdl.layoutChanged.connect(self.show_recent_count)

        # Connections for Timer, filter change and context menu
        self.timer.timeout.connect(self.rcnt_refresh.emit)
        self.ui.recent_filter_edt.textChanged.connect(
            self.recent_prxmdl.setFilterFixedString)
        self.ui.recent_tbl.customContextMenuRequested.connect(
            self.recent_context_menu)

    @Slot()
    def show_recent_count(self):
        """Updates the table's current row count in the bottom right."""
        rows = self.recent_prxmdl.rowCount(QModelIndex())
        self.ui.recent_num_lbl.setText(f"Displaying {rows} / 1000 Faults")

    @Slot(QPoint)
    def recent_context_menu(self, pos: QPoint):
        """Open the customized context menu when a fault is
        right-clicked.
        """
        index = self.ui.recent_tbl.indexAt(pos)
        is_valid = index.isValid()
        if is_valid:
            start = self.tbl_model.index(0, 0)
            desc = self.recent_prxmdl.index(index.row(), 1).data()
            ind = self.tbl_model.match(start, Qt.DisplayRole,
                                       desc, flags=Qt.MatchExactly)
            is_valid = ind != []
            if is_valid:
                self.selected_fault = ind[0]
        self.action.setEnabled(is_valid)
        self.recent_menu.popup(self.ui.recent_tbl.viewport().mapToGlobal(pos))
