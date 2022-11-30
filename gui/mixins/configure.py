from json import dumps
from qtpy.QtCore import (Qt, Slot, QModelIndex, QItemSelection,
                         QSortFilterProxyModel)
from qtpy.QtWidgets import (QHeaderView, QApplication)
from mps_database.models import Device
from enums import ConfFiles
from models_pkg.configure_model import (ConfigureTableModel)


class ConfigureMixin:
    def configure_init(self):
        """Initializer for everything in Configure tab: ListViews and
        PyDMEmbeddedDisplay."""
        self.ui.configure_spltr.setSizes([50, 50])
        self.ui.devs_spltr.setStretchFactor(0, 2)
        self.ui.devs_spltr.setStretchFactor(1, 1)

        devs = self.model.config.session.query(Device).all()

        # Set model, filter, and header for the All Devices table
        self.all_devs_model = ConfigureTableModel(self, devs)
        self.all_devs_filter = QSortFilterProxyModel(self)
        self.all_devs_filter.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.all_devs_filter.setSourceModel(self.all_devs_model)
        self.ui.all_devs_tbl.setModel(self.all_devs_filter)
        self.ui.all_devs_tbl.sortByColumn(1, Qt.AscendingOrder)
        hdr = self.ui.all_devs_tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)

        # Set model, filter, and header for the Selected Devices table
        self.sel_devs_model = ConfigureTableModel(self, [])
        self.sel_devs_filter = QSortFilterProxyModel(self)
        self.sel_devs_filter.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.sel_devs_filter.setSourceModel(self.sel_devs_model)
        self.ui.sel_devs_tbl.setModel(self.sel_devs_filter)
        self.ui.sel_devs_tbl.sortByColumn(1, Qt.AscendingOrder)
        hdr = self.ui.sel_devs_tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)

    def configure_connections(self):
        """Establish PV and slot connections for the devices model and
        configure tab."""
        # All Devices table and LineEdit
        self.ui.all_devs_edt.textChanged.connect(self.all_devs_filter.setFilterFixedString)
        self.ui.all_devs_tbl.selectionModel().selectionChanged.connect(self.dev_selected)

        # Selected Devices table and LineEdit
        self.ui.sel_devs_edt.textChanged.connect(self.sel_devs_filter.setFilterFixedString)
        self.ui.sel_clear_btn.clicked.connect(self.sel_devs_model.clear_data)
        self.ui.sel_devs_tbl.clicked.connect(self.dev_deselect)
        self.sel_devs_model.table_changed.connect(self.reload_embed)

    def bpm_macros(self):
        """Construct the macros dictionary for the selected device(s) if
        the device(s) are BPM's."""
        multi = not self.sel_devs_model.rowCount() == 1

        mac = {'MULTI': multi}
        for i in range(self.sel_devs_model.rowCount()):
            suf = str(i + 1) if multi else ""
            dev = self.sel_devs_model.get_device(i)

            mac['LN' + suf] = dev.card.link_node.lcls1_id
            mac['CL' + suf] = dev.card.crate.location
            mac['AC' + suf] = f"Slot {dev.card.number}" if dev.card.number != 1 else "RTM"
            if dev.is_analog():
                mac['CH' + suf] = dev.channel.number
            else:
                mac['CH' + suf] = ", ".join([i.channel.number for i in dev.inputs])
            mac['DEVICE' + suf] = self.model.name.getDeviceName(dev)
        
        return mac

    @Slot(QItemSelection, QItemSelection)
    def dev_selected(self, selected: QItemSelection, **kw):
        """When a device is selected in all_devs_tbl, add it to the
        sel_devs_tbl."""
        indexes = [i for i in selected.indexes() if i.column() == 0]

        for ind in indexes:
            dev_id = self.all_devs_filter.mapToSource(ind).row()
            dev = self.all_devs_model.get_device(dev_id)
            self.sel_devs_model.add_datum(dev)

    @Slot(QModelIndex)
    def dev_deselect(self, index: QModelIndex):
        """When a device is selected in sel_devs_tbl, remove it."""
        if not index.isValid():
            return

        dev_id = self.sel_devs_filter.mapToSource(index).row()
        self.sel_devs_model.remove_datum(dev_id)

    @Slot(ConfFiles)
    def reload_embed(self, dev_type: ConfFiles):
        """Reload the embedded display when the Selected Devices table
        content changes. Load the associated Configure Display."""
        if dev_type == ConfFiles.BPMS:
            mac = self.bpm_macros()
        else:
            mac = {}

        self.ui.configure_embed.macros = dumps(mac)
        self.ui.configure_embed.filename = dev_type.value
        QApplication.instance().processEvents()
