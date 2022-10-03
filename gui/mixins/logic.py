from functools import partial
from qtpy.QtCore import (Qt, Slot, QModelIndex, QItemSelection)
from qtpy.QtWidgets import (QHeaderView, QApplication)
from widgets.selection_detail import SelectionDetail
from models_pkg.logic_model import (LogicTableModel, LogicSortFilterModel,
                                    LogicItemDelegate)


class LogicMixin:
    def logic_init(self):
        """Initializer for everything in Logic tab: Logic Table Model,
        Logic Item Delegatw, and Selection Details."""
        self.tbl_model = LogicTableModel(self, self.faults,
                                         self.model.config.Session)
        self.delegate = LogicItemDelegate(self)

        self.logic_model = LogicSortFilterModel(self)
        self.logic_model.setSourceModel(self.tbl_model)
        self.logic_model.setFilterByColumn(0, "")
        self.ui.logic_tbl.setModel(self.logic_model)
        self.ui.logic_tbl.setSortingEnabled(True)
        self.ui.logic_tbl.sortByColumn(0, Qt.AscendingOrder)
        self.ui.logic_tbl.hideColumn(9)
        self.ui.logic_tbl.hideColumn(10)
        self.ui.logic_tbl.setItemDelegate(self.delegate)

        self.hdr = self.ui.logic_tbl.horizontalHeader()
        self.hdr.setSectionResizeMode(QHeaderView.Interactive)
        self.hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        self.hdr.resizeSection(1, 125)

        self.show_row_count()
        self.show_inactive(0)

        self.details = SelectionDetail(parent=self, mps_model=self.model)
        self.ui.logic_lyt.insertWidget(2, self.details)

    def logic_slot_connections(self):
        """Establish slot connections for the logic model and logic tab."""
        # Establish connections for inactive checkbox and filter lineedit
        self.ui.inactive_chck.stateChanged.connect(self.show_inactive)
        self.ui.logic_filter_edt.textChanged.connect(
            partial(self.logic_model.setFilterByColumn, 0))

        # Establish connections for the SelectionDetails widget
        self.ui.logic_tbl.selectionModel().selectionChanged.connect(
            self.selected)
        self.details.deselect.connect(self.details_closed)

        # Establish connections for showing the row count
        self.logic_model.rowsRemoved.connect(self.show_row_count)
        self.logic_model.rowsInserted.connect(self.show_row_count)
        self.logic_model.layoutChanged.connect(self.show_row_count)

        # Establish connection to remove channels on application close
        app = QApplication.instance()
        app.aboutToQuit.connect(self.tbl_model.remove_session)

    @Slot(int)
    def show_inactive(self, state):
        """Slot called when Inactive Checkbox is toggled. Determines if
        the inactive faults are shown. Only show faults that are active,
        this not including faults that could not establish a connection."""
        if not state:
            self.ui.logic_tbl.hideColumn(11)
            self.logic_model.setFilterByColumn(11, "Y")
        else:
            self.ui.logic_tbl.showColumn(11)
            self.logic_model.removeFilterByColumn(11)

    @Slot()
    def show_row_count(self):
        """When the number of displayed rows changes, update the row
        count at the bottom of the tab."""
        rows = self.logic_model.rowCount(QModelIndex())
        self.ui.num_flts_lbl.setText("Displaying {} / {} Faults"
                                     .format(rows, self.total_faults))

    @Slot(QItemSelection, QItemSelection)
    def selected(self, current, previous):
        """Slot called when a row is selected. This will change the
        SelectionDetails widget and open it if it's hidden."""
        indices = current.indexes()
        if not indices:
            indices = previous.indexes()
        row_ind = self.logic_model.mapToSource(indices[0])
        self.details.set_fault(self.faults[row_ind.row()])
        if self.details.isHidden():
            self.details.show()

    @Slot()
    def details_closed(self):
        """Slot to close the SelectionDetails widget."""
        self.ui.logic_tbl.clearSelection()
        self.details.hide()
