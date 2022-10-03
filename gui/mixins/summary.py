from qtpy.QtCore import (Slot, QPoint)
from qtpy.QtWidgets import (QHeaderView, QAction, QMenu, QTableView)
from models_pkg.logic_model import LogicSortFilterModel


class SummaryMixin:
    def summary_init(self):
        """Initializer for the Summary tab."""
        # Initialize the Summary Table and Headers
        self.summ_model = LogicSortFilterModel(self)
        self.summ_model.setSourceModel(self.tbl_model)
        self.summ_model.setFilterByColumn(1, "True")
        self.summ_model.setFilterByColumn(10, "False")
        self.summ_model.setFilterByColumn(11, "Y")
        self.ui.summ_tbl.setModel(self.summ_model)
        for i in range(8, 12):
            self.ui.summ_tbl.hideColumn(i)
        self.ui.summ_tbl.setItemDelegate(self.delegate)

        self.hdr = self.ui.summ_tbl.horizontalHeader()
        self.hdr.setSectionResizeMode(QHeaderView.Interactive)
        self.hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        self.hdr.resizeSection(1, 125)

        # Initialize the Bypass Table and Headers
        self.byp_model = LogicSortFilterModel(self)
        self.byp_model.setSourceModel(self.tbl_model)
        self.byp_model.setFilterByColumn(8, "Y")
        self.ui.byp_tbl.setModel(self.byp_model)
        for i in range(2, 12):
            self.ui.byp_tbl.hideColumn(i)
        self.ui.byp_tbl.showColumn(9)
        self.ui.byp_tbl.setItemDelegate(self.delegate)

        self.hdr = self.ui.byp_tbl.horizontalHeader()
        self.hdr.setSectionResizeMode(QHeaderView.Stretch)

        # Initialize the QAction used by the conext menus
        self.selected_fault = None
        self.action = QAction("Open fault in Logic tab", self)
        self.menu = QMenu(self)
        self.menu.addAction(self.action)

    def summ_slot_connections(self):
        """Establish connections for the context menus and their action."""
        self.ui.summ_tbl.customContextMenuRequested.connect(
            self.custom_context_menu)
        self.ui.byp_tbl.customContextMenuRequested.connect(
            self.custom_context_menu)
        self.action.triggered.connect(self.logic_select)

    def logic_select(self):
        """Set the selected fault in the Logic Tab to open the
        SelectionDetails widget. Then change tabs to the Logic Tab."""
        self.ui.logic_filter_edt.setText("")
        index = self.logic_model.mapFromSource(self.selected_fault)
        self.ui.logic_tbl.setCurrentIndex(index)
        self.ui.logic_tbl.scrollTo(index)
        self.ui.tabWidget.setCurrentIndex(1)

    @Slot(QPoint)
    def custom_context_menu(self, pos: QPoint):
        """Create a custom context menu to open the Fault's Details."""
        table = self.sender()
        if not table or not isinstance(table, QTableView):
            print("error", type(table))
            return
        index = table.indexAt(pos)
        if index.isValid():
            self.selected_fault = table.model().mapToSource(index)
            self.menu.popup(table.viewport().mapToGlobal(pos))
