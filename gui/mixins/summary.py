from qtpy.QtCore import (Qt, Slot, QPoint)
from qtpy.QtWidgets import (QHeaderView, QAction, QMenu, QTableView)
from models_pkg.logic_model import MPSSortFilterModel


class SummaryMixin:
    def summary_init(self, cud_mode=False):
        """Initializer for everything in the Summary tab: Summary table,
        Bypass table, and Custom Context menus."""
        # Initialize the Summary Table and Headers
        self.summ_model = MPSSortFilterModel(self)
        self.summ_model.setSourceModel(self.tbl_model)
        self.summ_model.setFilterByColumn(1, "True")
        self.summ_model.setFilterByColumn(self.tbl_model.iind, "Not Ignored")
        self.summ_model.setFilterByColumn(self.tbl_model.aind, "Y")
        self.ui.summ_tbl.setModel(self.summ_model)
        for i in range(self.tbl_model.conind[0], self.tbl_model.aind + 1):
            self.ui.summ_tbl.hideColumn(i)
        self.ui.summ_tbl.sortByColumn(2, Qt.AscendingOrder)
        self.ui.summ_tbl.setItemDelegate(self.delegate)

        hdr = self.ui.summ_tbl.horizontalHeader()
        if not cud_mode:
            hdr.setSectionResizeMode(QHeaderView.Interactive)
            hdr.setSectionResizeMode(0, QHeaderView.Stretch)
            hdr.resizeSection(1, 125)
        else:
            font = hdr.font()
            font.setPointSize(16)
            hdr.setFont(font)
            hdr.setFixedHeight(40)
            hdr.resizeSection(0, 550)
            hdr.resizeSection(1, 300)
            hdr.setSectionResizeMode(8, QHeaderView.Stretch)

        # Initialize the Bypass Table and Headers
        self.byp_model = MPSSortFilterModel(self)
        self.byp_model.setSourceModel(self.tbl_model)
        self.byp_model.setFilterByColumn(self.tbl_model.bind, "Y")
        self.ui.byp_tbl.setModel(self.byp_model)
        for i in range(2, self.tbl_model.aind + 1):
            self.ui.byp_tbl.hideColumn(i)
        self.ui.byp_tbl.showColumn(self.tbl_model.beind)
        self.ui.byp_tbl.sortByColumn(self.tbl_model.beind, Qt.AscendingOrder)
        self.ui.byp_tbl.setItemDelegate(self.delegate)

        hdr = self.ui.byp_tbl.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        if cud_mode:
            font = hdr.font()
            font.setPointSize(14)
            hdr.setFont(font)
            hdr.setFixedHeight(40)

        # Initialize the QAction used by the conext menus
        if not cud_mode:
            self.selected_fault = None
            self.action = QAction("Open fault in Logic tab", self)
            self.menu = QMenu(self)
            self.menu.addAction(self.action)

    def summ_connections(self):
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
        self.ui.main_tabs.setCurrentIndex(1)

    @Slot(QPoint)
    def custom_context_menu(self, pos: QPoint):
        """Create a custom context menu to open the Fault's Details."""
        table = self.sender()
        if not table or not isinstance(table, QTableView):
            self.logger.error("Internal error: "
                              f"{type(table)} is not a QTableView")
            return
        index = table.indexAt(pos)
        if index.isValid():
            source_index = table.model().mapToSource(index)
            self.selected_fault = (self.logic_model.sourceModel()
                                   .index(source_index.row(), 0))
            self.menu.popup(table.viewport().mapToGlobal(pos))
