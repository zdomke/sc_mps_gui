from datetime import datetime
from qtpy.QtGui import QFont
from qtpy.QtCore import (Qt, QAbstractTableModel, QModelIndex, Slot)
from sqlalchemy.orm import Session
from history.models.fault_history import FaultHistory


# ~~~~ Recent Faults Table ~~~~ #
class RecentFaultsTableModel(QAbstractTableModel):
    """Subclass of QAbstractTableModel for accessing and showing
    information from the FaultHistory table in the mps_history database.
    """
    font = QFont()
    font.setBold(True)
    hdr_lst = ["Date", "Fault", "State", "SC_BSYD", "SC_DIAG0",
               "SC_HXR", "SC_SXR", "LASER", "SC_LESA"]
    dest_lst = ["", "", "", "BSYD", "DIAG0",
                "HXR", "SXR", "LASER", "LESA"]

    def __init__(self, parent, session: Session):
        super(RecentFaultsTableModel, self).__init__(parent)
        """Takes in a SQLAlchemy session used to populate and refresh
        the model's data when needed. The variables created in the
        initialization are re-used often.
        """
        self.session = session
        self.last_datetime = datetime.min
        self._data = []

        self.get_data()
        parent.rcnt_refresh.connect(self.get_data)

    def rowCount(self, index: QModelIndex = QModelIndex()):
        """Return number of rows in the model. (dynamic)"""
        return len(self._data)

    def columnCount(self, index: QModelIndex = QModelIndex()):
        """Return number of columns in the model. (static)"""
        return len(self.hdr_lst)

    def data(self, index: QModelIndex, role: Qt.ItemDataRole):
        """Return data from the model for the given index."""
        if role == Qt.DisplayRole:
            return str(self._data[index.row()][index.column()])
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: Qt.ItemDataRole):
        """Return the model's header data & header font. (static)"""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.hdr_lst[section]
        if orientation == Qt.Horizontal and role == Qt.FontRole:
            return self.font

    def datum_to_row(self, datum: FaultHistory):
        """Helper function to convert data to the model's format."""
        row = ["--" for _ in range(9)]
        row[0] = datum.timestamp.strftime("%m/%d/%y  %H:%M:%S")
        row[1] = datum.fault_desc
        row[2] = datum.new_state

        new_dest = datum.beam_destination.replace("SC_", "")
        if new_dest == "DUMPBSY":
            new_dest = "BSYD"
        if datum.beam_class != "FULL" and new_dest in self.dest_lst:
            col = self.dest_lst.index(new_dest)
            row[col] = datum.beam_class

        return row

    @Slot()
    def get_data(self):
        """Query the FaultHistory table for faults newer than the most
        recent in the model (all if model is empty). Add all newest
        faults if there are any. Limit the model to 1000 faults by
        removing the oldest faults.
        """
        data = (self.session
                    .query(FaultHistory)
                    .filter(FaultHistory.timestamp > self.last_datetime)
                    .filter(FaultHistory.active)
                    .order_by(FaultHistory.timestamp.desc())
                    .limit(1000).all())

        if not data:
            return

        self.beginInsertRows(QModelIndex(), 0, len(data) - 1)
        for i, datum in enumerate(data):
            row = self.datum_to_row(datum)
            self._data.insert(i, row)
        self.endInsertRows()

        if len(self._data) >= 1000:
            self.beginRemoveRows(QModelIndex(), 1000, len(self._data))
            del self._data[1000:]
            self.endRemoveRows()

        self.layoutChanged.emit()
        self.last_datetime = data[0].timestamp
