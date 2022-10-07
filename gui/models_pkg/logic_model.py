from logging import getLogger
from platform import system
from qtpy.QtGui import (QBrush, QColor, QFont)
from qtpy.QtCore import (Qt, Slot, QModelIndex, QAbstractTableModel,
                         QEvent, QSortFilterProxyModel)
from qtpy.QtWidgets import (QStyledItemDelegate, QApplication, QToolTip)
from epics import caget
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import sessionmaker, scoped_session
from mps_database.models.fault_state import FaultState


class LogicTableModel(QAbstractTableModel):
    # Set class variables for the model. These are standard and static.
    font = QFont()
    font.setBold(True)
    brushes = {"bg": QBrush(QColor(0, 0, 0, 165)),
               "green": QBrush(QColor(0, 235, 0)),
               "yellow": QBrush(QColor(235, 235, 0)),
               "red": QBrush(QColor(255, 0, 0)),
               "magenta": QBrush(QColor(235, 0, 235)),
               "white": QBrush(QColor(255, 255, 255))}
    hdr_lst = ["Fault", "State", "SC_BSYD", "SC_DIAG0", "SC_HXR", "SC_SXR",
               "LASER", "SC_LESA", "Bypassed", "Bypass Exp Date", "Ignored",
               "Active"]
    dest_order = [-1, -1, 3, 2, 4, 5, 1, 6]
    logger = getLogger(__name__)

    def __init__(self, parent, faults: list, sessionmaker: sessionmaker):
        super(LogicTableModel, self).__init__(parent)
        self.faults = faults
        self.session = scoped_session(sessionmaker)

        self._data = []
        self._colors = []
        self.pv_addresses = []

        self.set_data()

    def rowCount(self, index: QModelIndex = QModelIndex()):
        """Return the number of rows in the model."""
        return len(self._data)

    def columnCount(self, index: QModelIndex = QModelIndex()):
        """Return the number of columns in the model."""
        if not self._data:
            return 0
        return len(self._data[0])

    def data(self, index: QModelIndex, role: Qt.ItemDataRole):
        """Return the index's text, font, alignment, background color,
        and foreground color."""
        if role == Qt.DisplayRole:
            return str(self._data[index.row()][index.column()])
        elif role == Qt.FontRole:
            return self.font
        elif 0 < index.column() and role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        elif (0 < index.column() and role == Qt.BackgroundRole):
            return self.brushes["bg"]
        elif index.column() == 1 and role == Qt.ForegroundRole:
            row_color = self._colors[index.row()]
            if row_color in [self.brushes["white"], self.brushes["magenta"]]:
                return row_color
            return self.brushes["green"]
        elif 1 < index.column() < 8 and role == Qt.ForegroundRole:
            if index.data() == '-':
                return self.brushes["green"]
            return self._colors[index.row()]
        elif 8 <= index.column() and role == Qt.ForegroundRole:
            if index.data() == "?":
                return self.brushes["white"]
            return self.brushes["green"]

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: Qt.ItemDataRole):
        """Set the horizontal header's text and font."""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.hdr_lst[section]
        elif orientation == Qt.Horizontal and role == Qt.FontRole:
            return self.font

    def set_data(self):
        """Set initial data for each fault. Populate each fault with the
        description, the PV name, and default values for bypass, ignore,
        and active cells. Set the color to white (for disconnected)."""
        for fault in self.faults:
            lst = []
            lst.append(fault.description)
            lst.append(fault.name)
            for _ in range(6):
                lst.append(fault.name)
            lst.append("?")
            lst.append("None")
            lst.append(False)
            lst.append("?")
            self._data.append(lst)
            self._colors.append(self.brushes["white"])
            self.pv_addresses.append(fault.name)

    def is_row_faulted(self, row: int):
        """Check if row is faulted based on the color (red, yellow, and
        magenta are faulted) then confirm that fault is not ignored and
        is active."""
        ret = not (self._colors[row] == self.brushes["green"]
                   or self._colors[row] == self.brushes["white"])
        return ret

    @Slot(int, int)
    def set_row(self, value: int, row: int):
        """Called when a Fault's state changes. Set the Fault's
        description and beam destinations based on the current state."""
        if value == -1:
            # 'BROKEN' State: all cells should be "BROKEN" in magenta
            self._data[row][1:8] = ["BROKEN"] * 7
            self._colors[row] = self.brushes["magenta"]
            self.dataChanged.emit(self.index(row, 1), self.index(row, 7))
            return
        elif value == 0:
            # Analog 'OK' State: all cells should be represented as '-'
            self._data[row][1:8] = ["-"] * 7
            self._colors[row] = self.brushes["green"]
            self.dataChanged.emit(self.index(row, 1), self.index(row, 7))
            return
        try:
            curr_state = (self.session.query(FaultState)
                          .filter(FaultState.id == value).one())
        except NoResultFound:
            self.logger.error(f"No Result: FaultState.id == '{value}' was not "
                              "found in the SQLite DB")

        self._data[row][1] = curr_state.device_state.description
        self._data[row][2:8] = ["-"] * 6
        self._colors[row] = self.brushes["green"]

        for cl in curr_state.allowed_classes:
            if cl.beam_class.name == "Full":
                continue

            col = self.dest_order.index(cl.beam_destination.id)
            self._data[row][col] = cl.beam_class.name
            if (self._colors[row] != self.brushes["red"]
                    and (cl.beam_class.name in ["Diagnostic", "Tuning"]
                         or "Hz" in cl.beam_class.name)):
                self._colors[row] = self.brushes["yellow"]
            else:
                self._colors[row] = self.brushes["red"]
        self.dataChanged.emit(self.index(row, 1), self.index(row, 7))

    @Slot(int, str, int)
    def set_byp(self, value: int, pvname: str, row: int):
        """Sets the 'Bypassed' and 'Bypass Exp Date' cells for the given
        row."""
        byp_exp = caget(pvname[:-1] + "_END", as_string=True)
        self._data[row][8] = "Y" if value else "N"
        self._data[row][9] = byp_exp if value else "None"
        self.dataChanged.emit(self.index(row, 8), self.index(row, 9))

    @Slot(int, int)
    def set_ign(self, value: int, row: int):
        """Sets the 'ignored_hidden' cell for the given row."""
        self._data[row][10] = bool(value)
        self.dataChanged.emit(self.index(row, 10), self.index(row, 10))

    @Slot(int, int)
    def set_act(self, value: int, row: int):
        """Sets the 'Active' cell for the given row."""
        self._data[row][11] = "Y" if value else "N"
        self.dataChanged.emit(self.index(row, 11), self.index(row, 11))


class LogicSortFilterModel(QSortFilterProxyModel):
    """Customized QSortFilterProxyModel to allow the user to sort and
    filter the customized QAbstractTableModel. Allows for functionality
    for the summary table, bypass table, and logic table."""
    def __init__(self, parent):
        super(LogicSortFilterModel, self).__init__(parent)
        self.filters = {}

    def setFilterByColumn(self, column: int, text: str):
        """Sets the filters to be used on individual columns."""
        self.filters[column] = text.lower()
        self.invalidateFilter()

    def removeFilterByColumn(self, column: int):
        """Removes the filters from a given column."""
        del self.filters[column]
        self.invalidateFilter()

    def lessThan(self, left: QModelIndex, right: QModelIndex):
        """Override QSortFilterProxyModel's lessThan method to sort
        columns to meet more personalized needs."""
        if 0 < left.column() < 8:
            left_fltd = self.sourceModel().is_row_faulted(left.row())
            right_fltd = self.sourceModel().is_row_faulted(right.row())

            # Sort by which row is faulted. If both rows have the same
            # fault status, then sort alphabetically. Set a lower
            # priority for "BROKEN" faults
            if left_fltd ^ right_fltd:
                return left_fltd
            if left.column() == 1:
                return (self.sourceModel().index(left.row(), 0).data()
                        < self.sourceModel().index(right.row(), 0).data())
            return (left.data().replace('-', '~').replace("BROKEN", '}')
                    < right.data().replace('-', '~').replace("BROKEN", '}'))
        elif left.column() == 8 or left.column() == 11:
            return right.data() < left.data()
        else:
            return left.data() < right.data()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex):
        """Override QSortFilterProxyModel's filterAcceptsRow method to
        filter out rows based on the table's needs."""
        for col, text in self.filters.items():
            if col == 1:
                if not self.sourceModel().is_row_faulted(source_row):
                    return False
            else:
                ind = self.sourceModel().index(source_row, col, source_parent)
                if ind.isValid() and text not in str(ind.data()).lower():
                    return False
        return True


class LogicItemDelegate(QStyledItemDelegate):
    """Customized QStyledItemDelegate to allow the user to copy
    some fault information from the table. Mimics functionality from
    PyDMWidgets."""
    def __init__(self, parent):
        super(LogicItemDelegate, self).__init__(parent)

    def editorEvent(self, event, model, option, index) -> bool:
        """Allow the user to copy a PV address by middle-clicking."""
        if (event.type() == QEvent.MouseButtonPress
                and event.button() == Qt.MiddleButton):
            clipboard = QApplication.clipboard()
            mode = clipboard.Clipboard
            if system() == 'Linux':
                mode = clipboard.Selection
            if index.column() != 0:
                source_ind = model.mapToSource(index)
                text = model.sourceModel().pv_addresses[source_ind.row()]
            else:
                text = index.data()
            clipboard.setText(text, mode=mode)
            new_event = QEvent(QEvent.Clipboard)
            QApplication.instance().sendEvent(clipboard, new_event)
            QToolTip.showText(event.globalPos(), text)
        return super().editorEvent(event, model, option, index)
