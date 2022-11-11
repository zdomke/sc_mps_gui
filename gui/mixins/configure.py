from qtpy.QtCore import (Qt, Slot, QModelIndex, QItemSelection,
                         QSortFilterProxyModel)
from mps_database.models import Device
from models_pkg.configure_model import (ConfigureListModel)


class ConfigureMixin:
    def configure_init(self):
        """Initializer for everything in Configure tab: ListViews and
        PyDMEmbeddedDisplay."""
        self.ui.configure_spltr.setStretchFactor(0, 2)
        self.ui.configure_spltr.setStretchFactor(1, 1)
        self.ui.devs_spltr.setStretchFactor(0, 2)
        self.ui.devs_spltr.setStretchFactor(1, 1)

        devs = self.model.config.session.query(Device).all()

        self.all_devs_model = ConfigureListModel(self, devs)
        self.all_devs_filter = QSortFilterProxyModel(self)
        self.all_devs_filter.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.all_devs_filter.setSourceModel(self.all_devs_model)

        self.sel_devs_model = ConfigureListModel(self, [])
        self.sel_devs_filter = QSortFilterProxyModel(self)
        self.sel_devs_filter.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.sel_devs_filter.setSourceModel(self.sel_devs_model)

        self.ui.all_devs_list.setModel(self.all_devs_filter)
        self.ui.sel_devs_list.setModel(self.sel_devs_filter)

        (self.ui.all_devs_edt.textChanged
            .connect(self.all_devs_filter.setFilterFixedString))
        (self.ui.sel_devs_edt.textChanged
            .connect(self.sel_devs_filter.setFilterFixedString))

        (self.ui.all_devs_list.selectionModel().selectionChanged
            .connect(self.dev_selected))
        self.ui.sel_devs_list.clicked.connect(self.dev_deselect)

    @Slot(QItemSelection, QItemSelection)
    def dev_selected(self, selected: QItemSelection, deselected):
        indices = selected.indexes()
        for ind in indices:
            dev_id = self.all_devs_filter.mapToSource(ind).row()
            dev = self.all_devs_model.get_device(dev_id)
            self.sel_devs_model.add_datum(dev)

    @Slot(QModelIndex)
    def dev_deselect(self, index: QModelIndex):
        if not index.isValid():
            return

        dev_id = self.sel_devs_filter.mapToSource(index).row()
        self.sel_devs_model.remove_datum(dev_id)
