from qtpy.QtCore import (Qt, Slot)
from qtpy.QtWidgets import (QHeaderView, QTableWidgetItem)
from widgets.widget_constructors import *
from widgets.selection_detail import SelectionDetail


# ~~~~ Logic Tab ~~~~ #
class LogicMixin:
    # ~~~~ Sort Buttons ~~~~ #
    @Slot()
    def set_sort_order(self):
        """Slot to change order to sort logic_tbl by."""
        if self.sort_order == Qt.AscendingOrder:
            self.sort_order = Qt.DescendingOrder
            self.ui.order_btn.setText("Descending")
        else:
            self.sort_order = Qt.AscendingOrder
            self.ui.order_btn.setText("Ascending")
        self.sort_logic_table()
    
    @Slot()
    def sort_logic_table(self):
        """Slot called to change the sorting on logic_tbl."""
        if self.ui.a_sort_btn.isChecked():
            self.ui.logic_tbl.sortItems(0, self.sort_order)
        elif self.ui.flt_sort_btn.isChecked():
            self.ui.logic_tbl.sortItems(9, self.sort_order)
        elif self.ui.byp_sort_btn.isChecked():
            self.ui.logic_tbl.sortItems(10, self.sort_order)
        self.ui.logic_tbl.horizontalHeader().setSortIndicatorShown(False)

    def set_flt_byp(self, fault_desc: str, col: int, val):
        row = self.ui.logic_tbl.findItems(fault_desc, Qt.MatchExactly)[0].row()
        item = self.ui.logic_tbl.item(row, col)
        if not self.ui.logic_tbl.item(row, col):
            self.ui.logic_tbl.setItem(row, col, QTableWidgetItem(str(val)))
        else:
            item.setText(str(val))
    
    # ~~~~ Search Bar ~~~~ #
    @Slot(str)
    def search_logic_table(self, text: str):
        """When text is entered in the search bar, only show rows where
        the fault's description contains the given text.
        """
        for i in range(len(self.faults)):
            if text.lower() in self.ui.logic_tbl.item(i, 0).text().lower():
                self.ui.logic_tbl.showRow(i)
            else:
                self.ui.logic_tbl.hideRow(i)

    # ~~~~ Logic Table ~~~~ #
    def pop_desc(self):
        """Populate column 0 of logic_tbl with fault.description."""
        self.ui.logic_tbl.setRowCount(len(self.faults))
        for i, fault in enumerate(self.faults.values()):
            item = QTableWidgetItem(fault.description)
            flags = item.flags()
            flags = flags ^ Qt.ItemIsEditable
            item.setFlags(flags)
            self.ui.logic_tbl.setItem(i, 0, item.clone())

    def logic_init(self):
        """For every fault, construct a row in the logic table
        containing information on that fault.
        """
        for i, fault in enumerate(self.faults.values()):
            construct_table_row(self.ui.logic_tbl, fault, i, True)

        self.ui.logic_tbl.hideColumn(9)
        self.ui.logic_tbl.hideColumn(10)
        self.ui.logic_tbl.setSortingEnabled(True)

        faults_header = self.ui.logic_tbl.horizontalHeader()

        faults_header.setSectionResizeMode(QHeaderView.Interactive)
        faults_header.setSectionResizeMode(0, QHeaderView.Stretch)
        faults_header.resizeSection(1, 125)

        self.details = SelectionDetail(parent=self, mps_model=self.model)
        self.details.deselect.connect(self.details_closed)
        self.ui.logic_lyt.addWidget(self.details, 2)

    # ~~~~ Selection Details ~~~~ #
    @Slot()
    def fault_selected(self):
        """Slot to be called when the logic_tbl selections change"""
        row = self.ui.logic_tbl.currentRow()
        desc = self.ui.logic_tbl.item(row, 0).text()
        self.details.set_fault(self.faults[desc])
        if self.details.isHidden:
            self.details.show()

    @Slot()
    def details_closed(self):
        """Called when the Selection Details section is closed"""
        self.ui.logic_tbl.clearSelection()
        self.details.hide()