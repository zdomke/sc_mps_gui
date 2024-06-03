from logging import getLogger
from platform import system
from qtpy.QtCore import (Qt, Slot, Signal, QModelIndex, QAbstractTableModel,
                         QEvent, QSortFilterProxyModel)
from qtpy.QtWidgets import (QStyledItemDelegate, QApplication, QToolTip)
from qtpy.QtGui import QPalette
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import (sessionmaker, scoped_session)
from epics import caget
from mps_database.models import (Condition, FaultState)
from enums import Statuses
from models_pkg.mps_model import MPSModel


class LogicTableModel(QAbstractTableModel):
    logger = getLogger(__name__)

    state_signal = Signal(int, int)
    byp_signal = Signal(int, int)
    byp_exp_signal = Signal(str, int)
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
        self.channels = []

        # Get max permit value for determining fault status
        self.speed_limit = caget("SIOC:SYS0:MP00:MAX_PERMIT.RVAL") - 1

        self.set_data()
        self.state_signal.connect(self.set_state)
        self.byp_signal.connect(self.set_byp)
        self.byp_exp_signal.connect(self.set_byp_exp)
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
            return Statuses.BGD.brush()
        elif role == Qt.ForegroundRole:
            row = index.row()
            col = index.column()
            txt = index.data()

            if col == 1 and self.status[row].error():
                return self.status[row].brush()

            elif 2 <= col < self.conind[0] and txt != '-':
                return self.status[row].brush()

            elif col in self.conind and txt == "Is In":
                return Statuses.YEL.brush()

            elif col == self.iind and txt == "Ignored":
                return Statuses.YEL.brush()

            elif self.bind <= col <= self.aind and txt == '?':
                return Statuses.WHT.brush()

            elif col != 0:
                return Statuses.GRN.brush()

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
            lst[self.iind] = "?"
            lst[self.aind] = "?"

            for i in self.conind:
                lst[i] = '-'
            dev = self.model.fault_to_dev(fault.fault)
            for con in dev.ignore_conditions:
                col = self.conind[0] + max(0, con.condition.id - 3)
                lst[col] = "Is In"

            self._data.append(lst)
            self.status.append(Statuses.WHT)
            self.channels.append(fault.name)

    @Slot(int, int)
    def set_state(self, value: int, row: int):
        """Called when a Fault's state changes. Set the Fault's
        description and beam destinations based on the current state."""
        self._data[row][1:self.conind[0]] = ["-"] * (self.conind[0] - 1)
        self.status[row] = Statuses.GRN

        if value == 0:
            # Analog 'OK' State: all cells should be represented as '-'
            self.dataChanged.emit(self.index(row, 1),
                                  self.index(row, self.conind[0] - 1))
            return
        elif value == -1:
            # Timeout State: all cells should be represented as 'TIMEOUT'
            self._data[row][1:self.conind[0]] = ["TIMEOUT"] * (self.conind[0] - 1)
            self.status[row] = Statuses.MAG
            self.dataChanged.emit(self.index(row, 1),
                                  self.index(row, self.conind[0] - 1))
            return

        try:
            curr_state = (self.session.query(FaultState)
                          .filter(FaultState.id == value).one())
        except NoResultFound:
            # Database Error State: all cells should be "DB_ERROR"
            self._data[row][1:self.conind[0]] = ["DB_ERROR"] * (self.conind[0] - 1)
            self.status[row] = Statuses.MAG
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

            # Find Beam Class values in MPS Beam Class Definitions display
            if self.status[row] == Statuses.RED:
                # Status already accounted for
                continue
            if cl.beam_class.number < 2:
                self.status[row] = Statuses.RED
            elif cl.beam_class.number < self.speed_limit:
                self.status[row] = Statuses.YEL

        self.dataChanged.emit(self.index(row, 1),
                              self.index(row, self.conind[0] - 1))

    @Slot(int, int)
    def set_byp(self, value: int, row: int):
        """Sets the 'Bypassed' cell for the given row."""
        self._data[row][self.bind] = "Y" if value else "N"
        self.dataChanged.emit(self.index(row, self.bind),
                              self.index(row, self.bind))

    @Slot(str, int)
    def set_byp_exp(self, value: str, row: int):
        """Sets the 'Bypass Exp Date' cells for the given row."""
        self._data[row][self.beind] = value
        self.dataChanged.emit(self.index(row, self.beind),
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

    def less_than(self, left: QModelIndex, right: QModelIndex):
        """Called by MPSSortFilterProxyModel to sort rows based on the
        app's status."""
        left_state = left.data()
        right_state = right.data()

        if 0 < left.column() < self.conind[0]:
            left_state = self.status[left.row()].num()
            right_state = self.status[right.row()].num()

            # Reduce priority of Ignored faults
            if self._data[left.row()][self.iind] == "Ignored":
                left_state -= .5
            if self._data[right.row()][self.iind] == "Ignored":
                right_state -= .5

            # Reduce priority of fault if the sort destination is Full
            # Increase priority of fault if the cell is not a '-'
            if left.column() != 1:
                if left.data() == '-' and left_state > 0:
                    left_state /= 10
                elif left.data() != '-':
                    left_state += .35

                if right.data() == '-' and right_state > 0:
                    right_state /= 10
                elif right.data() != '-':
                    right_state += .35

        if (0 < left.column() < self.conind[-1]
                or left.column() == self.bind
                or left.column() == self.aind):
            return right_state < left_state

        return left_state < right_state

    def filter_accepts_row(self, row: int, parent: QModelIndex, filters: dict):
        """Called by MPSSortFilterProxyModel to filter out rows based on
        the table's needs."""
        for col, text in filters.items():
            if col == 1:
                if not self.status[row].faulted():
                    return False
            else:
                if text not in str(self._data[row][col]).lower():
                    return False
        return True

    def middle_click_data(self, index: QModelIndex):
        """Method called by the ItemDelegate. Returns the data to be
        sent to the clipboard."""
        if index.column() == 0:
            return index.data()
        return self.channels[index.row()]


class MPSSortFilterModel(QSortFilterProxyModel):
    """Customized QSortFilterProxyModel to allow the user to sort and
    filter the customized QAbstractTableModel. Allows for functionality
    for the summary table, bypass table, and logic table."""
    def __init__(self, parent):
        super(MPSSortFilterModel, self).__init__(parent)
        self.filters = {}

    def setFilterByColumn(self, column: int, text: str):
        """Sets the filters to be used on individual columns."""
        self.filters[column] = text.lower()
        self.invalidateFilter()

    def removeFilterByColumn(self, column: int):
        """Removes the filters from a given column."""
        if column in self.filters:
            del self.filters[column]
            self.invalidateFilter()

    def lessThan(self, left: QModelIndex, right: QModelIndex):
        """Override QSortFilterProxyModel's lessThan method to sort
        columns to meet more personalized needs."""
        return self.sourceModel().less_than(left, right)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex):
        """Override QSortFilterProxyModel's filterAcceptsRow method to
        filter out rows based on the table's needs."""
        return self.sourceModel().filter_accepts_row(source_row, source_parent, self.filters)


class MPSItemDelegate(QStyledItemDelegate):
    """Customized QStyledItemDelegate to allow the user to copy
    some fault information from the table. Mimics functionality from
    PyDMWidgets."""
    def __init__(self, parent):
        super(MPSItemDelegate, self).__init__(parent)

    def editorEvent(self, event, model, option, index) -> bool:
        """Allow the user to copy a PV address by middle-clicking."""
        if (event.type() == QEvent.MouseButtonPress
                and event.button() == Qt.MiddleButton):
            clipboard = QApplication.clipboard()

            mode = clipboard.Clipboard
            if system() == 'Linux':
                mode = clipboard.Selection
            source_ind = model.mapToSource(index)
            text = model.sourceModel().middle_click_data(source_ind)
            clipboard.setText(text, mode=mode)

            new_event = QEvent(QEvent.Clipboard)
            QApplication.instance().sendEvent(clipboard, new_event)
            QToolTip.showText(event.globalPos(), text)
        return super().editorEvent(event, model, option, index)


class IgnoredColDelegate(MPSItemDelegate):
    """Customized QStyledItemDelegate to change the Ignored column
    display options.
    """
    def __init__(self, parent):
        super(IgnoredColDelegate, self).__init__(parent)

    def initStyleOption(self, option, index):
        super(IgnoredColDelegate, self).initStyleOption(option, index)
        if index.data() == '?':
            option.palette.setBrush(QPalette.Text, Statuses.WHT.brush())
        else:
            option.palette.setBrush(QPalette.Text, Statuses.GRN.brush())

    def displayText(self, value, locale):
        if value == "Ignored":
            value = 'Y'
        elif value == "Not Ignored":
            value = 'N'
        return value
