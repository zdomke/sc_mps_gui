from epics import caget_many
from qtpy.QtCore import (Qt, Slot)
from qtpy.QtWidgets import (QWidget, QTableWidgetItem, QHBoxLayout, QVBoxLayout,
                            QMessageBox, QHeaderView, QLabel, QTableWidget)
from pydm import Display
from pydm.widgets import (PyDMLabel, PyDMByteIndicator)
from resources.widgets import (PyDMMultiLineEdit, PyDMMultiCheckbox)


class ConfBPM(Display):
    cell_fill_dict = {0: "LN",
                      1: "CL",
                      2: "AC",
                      3: "CH",
                      4: "X_T0",
                      5: "Y_T0",
                      6: "TMIT_T0",
                      7: "TMIT_T1",
                      8: "TMIT_T2",
                      9: "TMIT_T3",
                      10: "TMIT_T4",
                      11: "TMIT_T5"}

    def __init__(self, parent=None, args=[], macros=None, ui_filename=None):
        super(ConfBPM, self).__init__(parent=parent, args=args, macros=macros,
                                      ui_filename=__file__.replace(".py", ".ui"))
        self.mac = macros

        if not self.mac.get('MULTI', False):
            self.ui.multi_dev_tbl.hide()
            return

        self.ui.single_dev_scroll.hide()

        self.devs = [self.mac[k] for k in self.mac.keys() if "DEVICE" in k]
        self.ui.multi_dev_tbl.setColumnCount((len(self.devs)) + 1)
        self.ui.multi_dev_tbl.setEditTriggers(QTableWidget.NoEditTriggers)

        for row in range(self.ui.multi_dev_tbl.rowCount()):
            for col in range(self.ui.multi_dev_tbl.columnCount()):
                self.populate_cell(row, col)

        hdr = self.ui.multi_dev_tbl.verticalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr = self.ui.multi_dev_tbl.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        self.ui.multi_dev_tbl.setHorizontalHeaderLabels(["Set Value To"] + self.devs)

    def populate_cell(self, row, col):
        """Populate the given cell. Rows 0-3 are static text, while
        other rows are dynamic Read/Write widgets."""
        if row < 4:
            if col == 0:
                item = QTableWidgetItem("-")
            else:
                key = self.cell_fill_dict[row] + str(col)
                item = QTableWidgetItem(str(self.mac[key]))
            item.setTextAlignment(Qt.AlignCenter)
            self.ui.multi_dev_tbl.setItem(row, col, item)
            return

        if col == 0:
            row_devs = [f"{d}:{self.cell_fill_dict[row]}" for d in self.devs]
            wid = ConfWriteBPM(self.ui.multi_dev_tbl, row_devs)
        else:
            row_dev = f"{self.mac['DEVICE' + str(col)]}:{self.cell_fill_dict[row]}"
            wid = ConfReadBPM(self.ui.multi_dev_tbl, row_dev)

        self.ui.multi_dev_tbl.setCellWidget(row, col, wid)


class ConfReadBPM(QWidget):
    def __init__(self, parent, dev):
        super(ConfReadBPM, self).__init__(parent=parent)
        self.dev = dev
        self.main_lyt = QVBoxLayout()
        self.setLayout(self.main_lyt)

        self.make_row("L")
        self.make_row("H")

    def make_row(self, hilo):
        """Makes the Min/Max row of the Read-only widget."""
        lyt = QHBoxLayout()

        lbl = QLabel("Max" if hilo == "H" else "Min")
        lbl.setFixedSize(25, 12)
        lbl.setStyleSheet("background-color: transparent")
        lyt.addWidget(lbl)

        wid = PyDMLabel(init_channel=f"ca://{self.dev}_{hilo}_RBV")
        wid.setMinimumWidth(64)
        lyt.addWidget(wid)

        wid = PyDMByteIndicator(init_channel=f"ca://{self.dev}_{hilo}_EN_RBV")
        wid.setFixedSize(14, 14)
        wid.showLabels = False
        wid.offColor = Qt.red
        lyt.addWidget(wid)

        self.main_lyt.addLayout(lyt)


class ConfWriteBPM(QWidget):
    def __init__(self, parent, devs):
        super(ConfWriteBPM, self).__init__(parent=parent)
        self.devs = devs
        self.main_lyt = QVBoxLayout()
        self.setLayout(self.main_lyt)

        self.make_row("L")
        self.make_row("H")

    def make_row(self, hilo):
        """Makes the Min/Max row of the Write-only widget. Establishes
        slot connections between the row's widgets."""
        lyt = QHBoxLayout()
        self.main_lyt.addLayout(lyt)

        lbl = QLabel("Max" if hilo == "H" else "Min")
        lbl.setFixedSize(25, 12)
        lbl.setStyleSheet("background-color: transparent")
        lyt.addWidget(lbl)

        edt = PyDMMultiLineEdit(init_channels=", ".join(f"{d}_{hilo}" for d in self.devs))
        edt.alarmSensitiveContent = True
        lyt.addWidget(edt)

        edt.returnPressed.disconnect()
        edt.returnPressed.connect(self.edt_returned)

        chk = PyDMMultiCheckbox(init_channels=", ".join([f"{d}_{hilo}_EN" for d in self.devs]))
        lyt.addWidget(chk)

        chk.clicked.disconnect()
        chk.clicked.connect(self.chk_clicked)

    @Slot()
    def edt_returned(self):
        """Slot for the PyDMMultiLineEdit. Checks that values match and
        requests user confirmation if they do not."""
        sndr = self.sender()
        txt = sndr.text()
        print(txt)

        vals = caget_many([f"{d[:-5]}_RBV" for d in sndr.channel.split(", ")],
                          connection_timeout=(len(self.devs) * .1))
        equiv = True
        first = vals[0]

        for v in vals:
            if v != first:
                equiv = False
                break

        if not equiv:
            ret = QMessageBox.warning(self, "Differing Threshold Values",
                                      "Threshold values are different across multiple devices."
                                      "\n\nContinue writing to all devices?",
                                      QMessageBox.Yes | QMessageBox.No)
            if ret == QMessageBox.No:
                return
        sndr.setText(txt)
        sndr.send_value()

    @Slot(bool)
    def chk_clicked(self, chk):
        """Slot for the PyDMMultiCheckboxes. If enabling the thresholds,
        confirm with the user first."""
        sndr = self.sender()
        if chk:
            ret = QMessageBox.warning(self, "Confirm Enabling Threshold",
                                      f"Enabling Thresholds:\n{sndr.channel.replace('_EN', '')}"
                                      "\n\nContinue to enable thresholds?",
                                      QMessageBox.Yes | QMessageBox.No)
            if ret == QMessageBox.No:
                sndr.setChecked(False)
                return

        sndr.send_value(chk)
