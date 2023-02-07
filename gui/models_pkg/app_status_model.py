from qtpy.QtCore import (Qt, QModelIndex, QAbstractTableModel)
from sqlalchemy.orm import (sessionmaker, scoped_session)
from enums import Statuses


class AppStatusTable(QAbstractTableModel):
    hdr_lst = ["LN", "Loc", "Slot", "AID", "Type", "Status"]

    def __init__(self, parent, sessionmaker: sessionmaker):
        super(AppStatusTable, self).__init__(parent)
        self.session = scoped_session(sessionmaker)

        self._data = []
        self.set_data()

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
        # elif role == Qt.ForegroundRole:
        #     row = index.row()
        #     col = index.column()
        #     txt = index.data()

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: Qt.ItemDataRole):
        """Set the horizontal header's text."""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.hdr_lst[section]

    def set_data(self):
        """Set initial data for every app."""
