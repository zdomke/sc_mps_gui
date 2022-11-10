from typing import List
from qtpy.QtCore import (Qt, QModelIndex, QAbstractListModel)
from mps_database.models import Device


class ConfigureListModel(QAbstractListModel):
    def __init__(self, parent, _data: List[Device]):
        super(ConfigureListModel, self).__init__(parent)
        self._data = _data

    def rowCount(self, index: QModelIndex = QModelIndex()):
        """Return the number of rows in the model."""
        return len(self._data)

    def data(self, index: QModelIndex, role: Qt.ItemDataRole):
        """Return the index's text if requested."""
        if role == Qt.DisplayRole:
            return self._data[index.row()].description

    def add_datum(self, datum: Device):
        ind = len(self._data)
        self.beginInsertRows(self.parent(), ind, ind)
        self._data.append(datum)
        self.endInsertRows(self.parent(), ind, ind)

    def remove_datum(self, datum: Device):
        ind = self._data.index(datum)
        self.beginRemoveRows(self.parent(), ind, ind)
        self._data.remove(datum)
        self.beginRemoveRows(self.parent(), ind, ind)
