from logging import getLogger
from platform import system
from qtpy.QtGui import (QBrush, QColor)
from qtpy.QtCore import (Qt, Slot, Signal, QModelIndex, QAbstractTableModel,
                         QEvent, QSortFilterProxyModel)
from qtpy.QtWidgets import (QStyledItemDelegate, QApplication, QToolTip)
from epics import PV
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import sessionmaker, scoped_session
from models_pkg.mps_model import MPSModel
from mps_database.models.condition import Condition
from mps_database.models.fault_state import FaultState


class LogicTableModel(QAbstractTableModel):
    # Set class variables for the model. These are standard and static.
    brushes = {3: QBrush(QColor(255, 0, 0)),       # Red
               2: QBrush(QColor(235, 235, 0)),     # Yellow
               1: QBrush(QColor(235, 0, 235)),     # Magenta
               0: QBrush(QColor(0, 235, 0)),       # Green
               -1: QBrush(QColor(255, 255, 255)),  # White
               -2: QBrush(QColor(0, 0, 0, 165))}   # Background
    logger = getLogger(__name__)

    state_signal = Signal(int, int)
    byp_signal = Signal(str, int, int)
    ign_signal = Signal(int, int)
    act_signal = Signal(int, int)

    def __init__(self, parent, model: MPSModel, sessionmaker: sessionmaker):
        super(LogicTableModel, self).__init__(parent)
        self.model = model
        self.session = scoped_session(sessionmaker)

        self.conind = []

        self.hdr_lst = (["Fault", "State"] + self.model.dest_lst)
        for con in self.model.config.session.query(Condition).all():
            name = con.name.split('_')[0] if "IGNORE" in con.name else con.name
            if name in self.hdr_lst:
                continue
            self.hdr_lst.append(name)
            self.conind.append(len(self.hdr_lst) - 1)
        self.hdr_lst += ["Bypassed", "Bypass Exp Date", "Ignored", "Active"]

        self.bind = self.hdr_lst.index("Bypassed")
        self.beind = self.hdr_lst.index("Bypass Exp Date")
        self.iind = self.hdr_lst.index("Ignored")
        self.aind = self.hdr_lst.index("Active")

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
        """Return the index's text, alignment, background color,
        and foreground color."""
        if not index.isValid():
            return
        elif role == Qt.DisplayRole:
            return str(self._data[index.row()][index.column()])
        elif role == Qt.TextAlignmentRole and 0 < index.column():
            return Qt.AlignCenter
        elif role == Qt.BackgroundRole and 0 < index.column():
            return self.brushes[-2]
        elif role == Qt.ForegroundRole:
            col = index.column()
            if col == 1:
                status = self.status[index.row()]
                color = status if status in [-1, 1] else 0
            elif 2 <= col < self.conind[0]:
                color = 0 if index.data() == '-' else self.status[index.row()]
            elif col in self.conind:
                color = 2 if index.data() == "Is In" else 0
                # color = 0
            elif col == self.iind:
                color = 2 if index.data() == "Ignored" else 0
            elif self.bind <= col <= self.aind:
                color = -1 if index.data() == '?' else 0
            if col != 0:
                return self.brushes[color]

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: Qt.ItemDataRole):
        """Set the horizontal header's text."""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.hdr_lst[section]

    def set_data(self):
        """Set initial data for each fault. Populate each fault with the
        description, the PV name, and default values for bypass, ignore,
        and active cells. Set the color to white (for disconnected)."""
        for fault in self.model.faults:
            lst = [fault.name] * len(self.hdr_lst)
            lst[0] = fault.description
            lst[1] = fault.name
            lst[self.bind] = "?"
            lst[self.beind] = "None"
            lst[self.iind] = "Not Ignored"
            lst[self.aind] = "?"

            for i in self.conind:
                lst[i] = '-'
            dev = self.model.fault_to_dev(fault.fault)
            for con in dev.ignore_conditions:
                col = self.conind[0] + max(0, con.condition.id - 3)
                lst[col] = "Is In"

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
        self._data[row][1:self.conind[0]] = ["-"] * (self.conind[0] - 1)
        self.status[row] = 0

        if value == 0:
            # Analog 'OK' State: all cells should be represented as '-'
            self.dataChanged.emit(self.index(row, 1),
                                  self.index(row, self.conind[0] - 1))
            return
        elif value == -1:
            # Timeout State: all cells should be represented as 'TIMEOUT'
            self._data[row][1:self.conind[0]] = ["TIMEOUT"] * (self.conind[0] - 1)
            self.status[row] = 1
            self.dataChanged.emit(self.index(row, 1),
                                  self.index(row, self.conind[0] - 1))
            return

        try:
            curr_state = (self.session.query(FaultState)
                          .filter(FaultState.id == value).one())
        except NoResultFound:
            # Database Error State: all cells should be "DB_ERROR"
            self._data[row][1:self.conind[0]] = ["DB_ERROR"] * (self.conind[0] - 1)
            self.status[row] = 1
            self.dataChanged.emit(self.index(row, 1),
                                  self.index(row, self.conind[0] - 1))
            return
        else:
            self._data[row][1] = curr_state.device_state.description

        for cl in curr_state.allowed_classes:
            if cl.beam_class.name == "Full":
                continue

            col = self.hdr_lst.index(cl.beam_destination.name)
            self._data[row][col] = cl.beam_class.name

            is_yellow = "Hz" in cl.beam_class.name
            is_yellow |= cl.beam_class.name in ["Diagnostic", "Tuning"]
            self.status[row] = 2 if self.status[row] != 3 and is_yellow else 3
        self.dataChanged.emit(self.index(row, 1),
                              self.index(row, self.conind[0] - 1))

    @Slot(str, int, int)
    def set_byp(self, pvname: str, value: int, row: int):
        """Sets the 'Bypassed' and 'Bypass Exp Date' cells for the given
        row."""
        self._data[row][self.bind] = "Y" if value else "N"
        self._data[row][self.beind] = (self.byp_ends[pvname].value
                                       if value else "None")
        self.dataChanged.emit(self.index(row, self.bind),
                              self.index(row, self.beind))

    @Slot(int, int)
    def set_ign(self, value: int, row: int):
        """Sets the 'Ignored' cell for the given row."""
        self._data[row][self.iind] = "Ignored" if bool(value) else "Not Ignored"
        self.dataChanged.emit(self.index(row, self.iind),
                              self.index(row, self.iind))

    @Slot(int, int)
    def set_act(self, value: int, row: int):
        """Sets the 'Active' cell for the given row."""
        self._data[row][self.aind] = "Y" if value else "N"
        self.dataChanged.emit(self.index(row, self.aind),
                              self.index(row, self.aind))


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
        if 0 < left.column() < self.sourceModel().conind[0]:
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
        elif (left.column() in self.sourceModel().conind
              or left.column() == self.sourceModel().bind
              or left.column() == self.sourceModel().aind):
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
