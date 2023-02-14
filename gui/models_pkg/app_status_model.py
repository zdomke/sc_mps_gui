from qtpy.QtCore import (Qt, Slot, Signal, QModelIndex, QAbstractTableModel)
from sqlalchemy.orm import (sessionmaker, scoped_session)
from enums import Statuses


class AppStatusTable(QAbstractTableModel):
    hdr_lst = ["LN", "Loc", "Slot", "AID", "Type", "Status"]

    status_signal = Signal(int, int)

    def __init__(self, parent, sessionmaker: sessionmaker, apps):
        super(AppStatusTable, self).__init__(parent)
        self.session = scoped_session(sessionmaker)
        self.apps = apps

        self._data = []
        self.set_data()

        self.status_signal.connect(self.set_status)

    def rowCount(self, index: QModelIndex = QModelIndex()):
        """Return the number of rows in the model."""
        return len(self._data)

    def columnCount(self, index: QModelIndex = QModelIndex()):
        """Return the number of columns in the model."""
        return len(self.hdr_lst)

    def data(self, index: QModelIndex, role: Qt.ItemDataRole):
        """Return the index's data associated with the role."""
        if not index.isValid():
            return
        elif role == Qt.DisplayRole:
            return str(self._data[index.row()][index.column()])
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        elif role == Qt.BackgroundRole:
            return Statuses.BGD.brush()
        elif role == Qt.ForegroundRole:
            col = index.column()
            txt = index.data()
            if col == 5:
                if txt == "ONLINE":
                    return Statuses.GRN.brush()
                elif txt == "OFFLINE":
                    return Statuses.RED.brush()
                else:
                    return Statuses.WHT.brush()
            else:
                return Statuses.GRN.brush()

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: Qt.ItemDataRole):
        """Set the horizontal header's text."""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.hdr_lst[section]

    def set_data(self):
        """Set initial data for every app."""
        for app in self.apps:
            lst = [app.name] * len(self.hdr_lst)
            lst[0] = app.link_node.lcls1_id
            lst[1] = app.crate.location
            lst[2] = app.slot_number if app.slot_number != 1 else "RTM"
            lst[3] = app.number
            lst[4] = app.type.name

            self._data.append(lst)

    @Slot(int, int)
    def set_status(self, value: int, row: int):
        """Set the App's Status based on the value passed."""
        self._data[row][5] = "ONLINE" if value else "OFFLINE"
        self.dataChanged.emit(self.index(row, 5), self.index(row, 5))
