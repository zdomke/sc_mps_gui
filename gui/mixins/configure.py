from json import dumps
from itertools import groupby
from qtpy.QtCore import (Qt, Slot, QModelIndex, QSortFilterProxyModel)
from qtpy.QtWidgets import (QHeaderView, QApplication)
from mps_database.models import Device
from enums import ConfFiles
from models_pkg.configure_model import (ConfigureTableModel)


class ConfigureMixin:
    def configure_init(self):
        """Initializer for everything in Configure tab: ListViews and
        PyDMEmbeddedDisplay."""
        self.ui.configure_spltr.setSizes([50, 50])
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
        self.sel_devs_model = ConfigureTableModel(self, [], save_type=True)
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
        self.ui.all_devs_tbl.clicked.connect(self.dev_selected)

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

            mac[f'LN{suf}'] = dev.card.link_node.lcls1_id
            mac[f'CL{suf}'] = dev.card.crate.location
            mac[f'DEVICE{suf}'] = self.model.name.getDeviceName(dev)

            if multi:
                if dev.is_analog():
                    chans = dev.channel.number
                else:
                    chans = self.channel_range([i.channel for i in dev.inputs])
                mac[f'AC{suf}'] = dev.card.number
                mac[f'CH{suf}'] = chans

        if not multi:
            mac['AS'] = dev.card.slot_number
            mac['CPU'] = dev.card.link_node.cpu

            for i in range(1, 8):
                mac[f'AC{i}'] = "Slot Empty"
                mac[f'CH{i}'] = ""

            for c in dev.card.crate.cards:
                chans = self.channel_range(c.analog_channels
                                           + c.digital_channels
                                           + c.digital_out_channels)
                mac[f'AC{c.slot_number}'] = c.number
                mac[f'CH{c.slot_number}'] = chans

        return mac

    def channel_range(self, channels):
        """Takes a list of channels (AnalogChannel, DigitalChannel, or
        DigitalOutChannel) and returns ranges of numbers covered."""
        nums = sorted([ch.number for ch in channels])
        ranges = []
        for _, r in groupby(enumerate(nums), lambda e: e[1] - e[0]):
            r = list(r)
            if len(r) == 1:
                ranges.append((r[0][1], None))
            elif len(r) == 2:
                ranges.append((r[0][1], None))
                ranges.append((r[-1][1], None))
            else:
                ranges.append((r[0][1], r[-1][1]))

        return ", ".join([str(x) if not y else f"{x}-{y}" for x, y in ranges])

    @Slot(QModelIndex)
    def dev_selected(self, index: QModelIndex):
        """When a device is clicked in all_devs_tbl, add it to the
        sel_devs_tbl."""
        if not index.isValid():
            return

        dev_id = self.all_devs_filter.mapToSource(index).row()
        dev = self.all_devs_model.get_device(dev_id)
        self.sel_devs_model.add_datum(dev)

    @Slot(QModelIndex)
    def dev_deselect(self, index: QModelIndex):
        """When a device is clicked in sel_devs_tbl, remove it."""
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
