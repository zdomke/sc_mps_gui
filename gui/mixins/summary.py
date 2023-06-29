from qtpy.QtCore import (Qt, Slot, QPoint)
from qtpy.QtWidgets import (QHeaderView, QAction, QMenu, QTableView, QGraphicsOpacityEffect)
from models_pkg.logic_model import MPSSortFilterModel
from epics import caget
from epics import PV


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
            font.setPointSize(22)
            font.setBold(True)
            hdr.setFont(font)
            hdr.setFixedHeight(50)
            vhdr = self.ui.summ_tbl.verticalHeader()
            vhdr.setDefaultSectionSize(53)
            hdr.setDefaultSectionSize(200)
            hdr.resizeSection(0, 1100)
            hdr.setSectionResizeMode(1, QHeaderView.Stretch)
            for i in range(2, 10):
                self.ui.summ_tbl.hideColumn(i)

            self.TPG_mode_destination_preference = {
                'SC10': 6,  # LASER
                'SC11': 2,  # BSYD
                'SC12': 2,  # BSYD
                'SC13': 3,  # DIAG0
                'SC14': 2,  # BSYD
                'SC15': 4,  # HXR
                'SC16': 5,  # SXR
                'SC17': 5,  # SXR
                'SC18': 5}  # SXR
            self.dest_permit_map = {
                'SC_DIAG0': self.ui.permit_DIAG0,
                'SC_BSYD':  self.ui.permit_BSYD,
                'SC_HXR':   self.ui.permit_HXR,
                'SC_SXR':   self.ui.permit_SXR,
                'SC_LESA':  self.ui.permit_LESA}

            # need this initial call with direct caget, otherwise the initial
            # run of the callback will not connect to the 'DSTxx_NAME' PVs
            self.arrange_cud(value=caget('TPG:SYS0:1:MODE'))
            self.tpg_mode = PV('TPG:SYS0:1:MODE', callback=self.arrange_cud)

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

    def arrange_cud(self, value, **kw):
        """
        callback for changes to the "TPG mode" -- updates the sorting priority
        of the summary table and shades permit widgets accordingly
        """
        # sort by "priority" destination
        priority_destination = self.TPG_mode_destination_preference[value]
        self.ui.summ_tbl.sortByColumn(priority_destination, Qt.AscendingOrder)
        for i in range(2, 10):
            self.ui.summ_tbl.hideColumn(i)
        self.ui.summ_tbl.showColumn(priority_destination)
        # always show DIAG0 column for modes that allow it
        if value not in ['SC10', 'SC11', 'SC12']:
            self.ui.summ_tbl.showColumn(3)

        # shade permit boxes for unsupported destinations
        allowed_destinations = []
        for i in range(6):
            dest_name = caget(f'TPG:SYS0:1:{value}:DST0{i}_NAME')
            if dest_name != 'NULL':
                allowed_destinations.append(dest_name)

        for dest_name, dest_permit_obj in self.dest_permit_map.items():
            permit_effect = None
            if dest_name not in allowed_destinations:
                permit_effect = QGraphicsOpacityEffect(opacity=0.2)
            dest_permit_obj.setGraphicsEffect(permit_effect)
