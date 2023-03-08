from qtpy.QtCore import (Qt, Slot, Signal, QModelIndex, QAbstractTableModel)
from qtpy.QtWidgets import QStyledItemDelegate
from sqlalchemy.orm import (sessionmaker, scoped_session)
from pydm.widgets import PyDMRelatedDisplayButton
from enums import Statuses


class AppStatusTable(QAbstractTableModel):
    hdr_lst = ["LN", "Loc", "Slot", "AID", "Type", "Status", "Group"]

    status_signal = Signal(int, int)

    def __init__(self, parent, sessionmaker: sessionmaker, apps):
        super(AppStatusTable, self).__init__(parent)
        self.session = scoped_session(sessionmaker)
        self.apps = apps

        self._data = []
        self.status = []
        self.channels = []
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
            row = index.row()
            col = index.column()
            if col == 5:
                return self.status[row].brush()
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
            ch = f"{app.link_node.get_cn_prefix()}:APP{app.number}_STATUS"

            lst = [ch] * len(self.hdr_lst)
            lst[0] = app.link_node.lcls1_id
            lst[1] = app.crate.location
            lst[2] = app.slot_number if app.slot_number != 1 else "RTM"
            lst[3] = app.number
            lst[4] = app.type.name
            lst[6] = app.link_node.group

            self._data.append(lst)
            self.status.append(Statuses.WHT)
            self.channels.append(ch)

    @Slot(int, int)
    def set_status(self, value: int, row: int):
        """Set the App's Status based on the value passed."""
        self._data[row][5] = "ONLINE" if value else "OFFLINE"
        self.status[row] = Statuses.GRN if value else Statuses.RED
        self.dataChanged.emit(self.index(row, 5), self.index(row, 5))

    def less_than(self, left: QModelIndex, right: QModelIndex):
        """Called by MPSSortFilterProxyModel to sort rows based on the
        app's status."""
        if left.column() in [0, 2, 3]:
            left_state = int(left.data().replace("RTM", "1"))
            right_state = int(right.data().replace("RTM", "1"))
        elif left.column() == 5:
            left_state = self.status[left.row()].num()
            if self.status[left.row()] == Statuses.WHT:
                left_state = Statuses.max() + 1
            right_state = self.status[right.row()].num()
            if self.status[right.row()] == Statuses.WHT:
                right_state = Statuses.max() + 1
        else:
            left_state = left.data()
            right_state = right.data()
        return left_state < right_state

    def filter_accepts_row(self, row: int, parent: QModelIndex, filters: dict):
        """Called by MPSSortFilterProxyModel to filter out rows based on
        the table's needs."""
        for col, text in filters.items():
            if col == 5:
                if not self.status[row].faulted():
                    return False
            else:
                ind = self.index(row, col, parent)
                if ind.isValid() and (text not in str(ind.data()).lower()):
                    return False
        return True

    def middle_click_data(self, index: QModelIndex):
        """Returns the text to be copied to the clipboard."""
        return self.channels[index.row()]


# TODO: Generalize this
class RelatedDisplayDelegate(QStyledItemDelegate):
    """Customized QStyledItemDelegate to allow the user to open an
    associated display."""
    def __init__(self, parent):
        super(RelatedDisplayDelegate, self).__init__(parent)

    def createEditor(self, parent, option, index):
        """Create the RelatedDisplayButton to show for the index."""
        file = f"$PHYSICS_TOP/mps_configuration/current/display/groups/LinkNodeGroup{index.data()}.ui"
        editor = PyDMRelatedDisplayButton(parent=parent, filename=file)
        editor.setText(f"Group {index.data()}...")
        editor.showIcon = False
        editor.openInNewWindow = True
        return editor
