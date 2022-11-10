from qtpy.QtCore import (Qt, QSortFilterProxyModel)
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

    # @Slot(QItemSelection, QItemSelection)
    # def item_selected(self, selected, deselected):
    #     sel_ind = self.ui.all_devs_list.selectionModel().selectedIndexes()
    #     self.conf_index.set_filter([i.row() for i in sel_ind])
