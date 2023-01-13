from logging import getLogger
from qtpy.QtGui import (QBrush, QColor, QFont)
from qtpy.QtCore import (Qt, Slot, Signal, QModelIndex, QAbstractTableModel)
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import sessionmaker, scoped_session
from mps_database.models.fault_state import FaultState
from models_pkg.mps_model import MPSModel


class IgnoreTableModel(QAbstractTableModel):
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
               "LASER", "SC_LESA", "Ignore Conditions", "Active"]
    dest_order = [-1, -1, 3, 2, 4, 5, 1, 6]
    logger = getLogger(__name__)

    state_signal = Signal(int, int)
    act_signal = Signal(int, int)

    def __init__(self, parent, model: MPSModel, sessionmaker: sessionmaker):
        super(IgnoreTableModel, self).__init__(parent)
        self.model = model
        self.faults = model.faults
        self.session = scoped_session(sessionmaker)

        self._data = []
        self.status = []
        self.pv_addresses = []

        self.set_data()
        self.state_signal.connect(self.set_row)
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
            elif 1 < col:
                color = 0 if index.data() == '-' else self.status[index.row()]
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
            lst = [fault.name] * 10
            lst[0] = fault.description

            # Get ignore condition string
            dev = self.model.fault_to_dev(fault.fault)
            ign_str = ", ".join([ign.condition.description
                                for ign in dev.ignore_conditions])
            lst[8] = ign_str
            lst[9] = '?'

            self._data.append(lst)
            self.status.append(-1)
            self.pv_addresses.append(fault.name)

    def is_row_faulted(self, row: int):
        """Check if row is faulted based on the color (red, yellow, and
        magenta are faulted) then confirm that fault is not ignored and
        is active."""
        return 0 < self.status[row]

    @Slot(int, int)
    def set_row(self, value: int, row: int, **kw):
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

            col = self.dest_order.index(cl.beam_destination.id)
            self._data[row][col] = cl.beam_class.name
            if (self.status[row] != 3
                    and (cl.beam_class.name in ["Diagnostic", "Tuning"]
                         or "Hz" in cl.beam_class.name)):
                self.status[row] = 2
            else:
                self.status[row] = 3
        self.dataChanged.emit(self.index(row, 1), self.index(row, 7))

    @Slot(int, int)
    def set_act(self, value: int, row: int):
        """Sets the 'Active' cell for the given row."""
        self._data[row][9] = "Y" if value else "N"
        self.dataChanged.emit(self.index(row, 9), self.index(row, 9))
