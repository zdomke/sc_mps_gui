from logging import getLogger
from platform import system
from qtpy.QtGui import (QBrush, QColor, QFont)
from qtpy.QtCore import (Qt, Slot, Signal, QModelIndex, QAbstractTableModel,
                         QEvent, QSortFilterProxyModel)
from qtpy.QtWidgets import (QStyledItemDelegate, QApplication, QToolTip)
from epics import PV
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import sessionmaker, scoped_session
from models_pkg.mps_model import MPSModel
from mps_database.models.fault_state import FaultState


class LogicTableModel(QAbstractTableModel):
    # Set class variables for the model. These are standard and static.
    font = QFont()
    font.setBold(True)
    brushes = {3: QBrush(QColor(255, 0, 0)),       # Red
               2: QBrush(QColor(235, 235, 0)),     # Yellow
               1: QBrush(QColor(235, 0, 235)),     # Magenta
               0: QBrush(QColor(0, 235, 0)),       # Green
               -1: QBrush(QColor(255, 255, 255)),  # White
               -2: QBrush(QColor(0, 0, 0, 165))}   # Background
    hdr_lst = ["Fault", "State", "SC_BSYD", "SC_DIAG0", "SC_HXR", "SC_SXR",
               "LASER", "SC_LESA", "Bypassed", "Bypass Exp Date", "Ignored",
               "Active"]
    dest_order = [-1, -1, 3, 2, 4, 5, 1, 6]
    logger = getLogger(__name__)

    state_signal = Signal(int, int)
    byp_signal = Signal(str, int, int)
    ign_signal = Signal(int, int)
    act_signal = Signal(int, int)

    def __init__(self, parent, model: MPSModel, sessionmaker: sessionmaker):
        super(LogicTableModel, self).__init__(parent)
        self.faults = model.faults
        self.model = model
        self.session = scoped_session(sessionmaker)

        self._data = []
        self.status = []
        self.byp_ends = {}

        self.set_data()
        self.state_signal.connect(self.set_state)
        self.byp_signal.connect(self.set_byp)
        self.ign_signal.connect(self.set_ign)
        self.act_signal.connect(self.set_act)

    def rowCount(self, index: QModelIndex = QModelIndex()):
        """Return the number of rows in the model."""
        return len(self._data)

    def columnCount(self, index: QModelIndex = QModelIndex()):
        """Return the number of columns in the model."""
        return len(self.hdr_lst)

    def data(self, index: QModelIndex, role: Qt.ItemDataRole):
        """Return the index's text, font, alignment, background color,
        and foreground color."""
        if role == Qt.DisplayRole:
            return str(self._data[index.row()][index.column()])
        elif role == Qt.FontRole:
            return self.font
        elif role == Qt.TextAlignmentRole and 0 < index.column():
            return Qt.AlignCenter
        elif role == Qt.BackgroundRole and 0 < index.column():
            return self.brushes[-2]
        elif role == Qt.ForegroundRole:
            col = index.column()
            if col == 1:
                status = self.status[index.row()]
                color = status if status in [-1, 1] else 0
            elif 2 <= col < 8:
                color = 0 if index.data() == '-' else self.status[index.row()]
            elif 8 <= col:
                color = -1 if index.data() == '?' else 0
            if col != 0:
                return self.brushes[color]

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
            lst = [fault.name] * len(self.hdr_lst)
            lst[0] = fault.description
            lst[1] = fault.name
            lst[8] = "?"
            lst[9] = "None"
            lst[10] = False
            lst[11] = "?"

            self._data.append(lst)
            self.status.append(-1)
            pv = PV(f"{fault.name}_SCBYP_END")
            self.byp_ends[fault.name] = pv

    def is_row_faulted(self, row: int):
        """Check if row is faulted based on the color (red, yellow, and
        magenta are faulted) then confirm that fault is not ignored and
        is active."""
        return 0 < self.status[row]

    @Slot(int, int)
    def set_state(self, value: int, row: int):
        """Called when a Fault's state changes. Set the Fault's
        description and beam destinations based on the current state."""
        if value == -1:
            # 'BROKEN' State: all cells should be "BROKEN" in magenta
            self._data[row][1:8] = ["BROKEN"] * 7
            self.status[row] = 1
            self.dataChanged.emit(self.index(row, 1), self.index(row, 7))
            return
        elif value == 0:
            # Analog 'OK' State: all cells should be represented as '-'
            self._data[row][1:8] = ["-"] * 7
            self.status[row] = 0
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
        self.status[row] = 0

        for cl in curr_state.allowed_classes:
            if cl.beam_class.name == "Full":
                continue

            try:
                col = self.dest_order.index(cl.beam_destination.id)
            except ValueError:
                self.logger.error("No Column for Destination "
                                  f"{cl.beam_destination.name}.")
                continue
            self._data[row][col] = cl.beam_class.name
            if (self.status[row] != 3
                    and (cl.beam_class.name in ["Diagnostic", "Tuning"]
                         or "Hz" in cl.beam_class.name)):
                self.status[row] = 2
            else:
                self.status[row] = 3
        self.dataChanged.emit(self.index(row, 1), self.index(row, 8))

    @Slot(str, int, int)
    def set_byp(self, pvname: str, value: int, row: int):
        """Sets the 'Bypassed' and 'Bypass Exp Date' cells for the given
        row."""
        self._data[row][8] = "Y" if value else "N"
        self._data[row][9] = self.byp_ends[pvname].value if value else "None"
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
        self.exclusions = {}

    def setFilterByColumn(self, column: int, text: str):
        """Sets the filters to be used on individual columns."""
        self.filters[column] = text.lower()
        self.invalidateFilter()

    def setExclusionByColumn(self, column: int, text: str):
        """Sets filter to exclude from given column."""
        self.exclusions[column] = text.lower()
        self.invalidateFilter()

    def removeFilterByColumn(self, column: int):
        """Removes the filters from a given column."""
        if column in self.filters:
            del self.filters[column]
            self.invalidateFilter()

    def removeExclusionByColumn(self, column: int):
        """Removes the filters from a given column."""
        if column in self.exclusions:
            del self.exclusions[column]
            self.invalidateFilter()

    def lessThan(self, left: QModelIndex, right: QModelIndex):
        """Override QSortFilterProxyModel's lessThan method to sort
        columns to meet more personalized needs."""
        if 0 < left.column() < 8:
            left_state = self.sourceModel().status[left.row()]
            right_state = self.sourceModel().status[right.row()]

            if left.column() != 1:
                left_txt = left.data()
                if left_state > 0 and left_txt == '-':
                    left_state /= 10

                right_txt = right.data()
                if right_state > 0 and right_txt == '-':
                    right_state /= 10

            return right_state < left_state
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
                if ind.isValid() and (text not in str(ind.data()).lower()):
                    return False
        for col, text in self.exclusions.items():
            ind = self.sourceModel().index(source_row, col, source_parent)
            if text in str(ind.data()).lower():
                return False
            for word in text.split(','):
                if word.strip() in str(ind.data()).lower():
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
                key_list = list(model.sourceModel().byp_ends.keys())
                text = key_list[source_ind.row()]
            else:
                text = index.data()
            clipboard.setText(text, mode=mode)
            new_event = QEvent(QEvent.Clipboard)
            QApplication.instance().sendEvent(clipboard, new_event)
            QToolTip.showText(event.globalPos(), text)
        return super().editorEvent(event, model, option, index)
