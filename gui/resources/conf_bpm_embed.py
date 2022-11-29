from functools import partial
from epics import caget_many
from qtpy.QtCore import (Qt, Slot, QTimer)
from qtpy.QtWidgets import (QWidget, QTableWidgetItem, QHBoxLayout, QVBoxLayout, QMessageBox, QHeaderView, QLabel, QTableWidget)
from pydm import Display
from pydm.widgets import PyDMLabel, PyDMByteIndicator
from widgets import (PyDMMultiLineEdit, PyDMMultiCheckbox)


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
        if not macros.get('MULTI', False):
            self.ui.multi_dev_tbl.hide()
            return

        self.ui.single_dev_scroll.hide()

        devs = [macros[k] for k in macros.keys() if "DEV" in k]
        self.ui.multi_dev_tbl.setColumnCount((len(devs)) + 1)
        self.ui.multi_dev_tbl.setEditTriggers(QTableWidget.NoEditTriggers)

        for row in range(self.ui.multi_dev_tbl.rowCount()):
            for col in range(self.ui.multi_dev_tbl.columnCount()):
                if row < 4:
                    if col == 0:
                        item = QTableWidgetItem("-")
                    else:
                        key = self.cell_fill_dict[row] + str(col)
                        item = QTableWidgetItem(str(macros[key]))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.ui.multi_dev_tbl.setItem(row, col, item)
                elif col == 0:
                    row_devs = [f"{d}:{self.cell_fill_dict[row]}" for d in devs]
                    # row_devs = ["MKB:SYS0:10", "MKB:SYS0:11", "MKB:SYS0:12"]
                    wid = ConfWriteBPM(self.ui.multi_dev_tbl, row_devs)
                    self.ui.multi_dev_tbl.setCellWidget(row, col, wid)
                else:
                    row_dev = f"{macros['DEV' + str(col)]}:{self.cell_fill_dict[row]}"
                    # row_dev = "MKB:SYS0:1" + str(col - 1)
                    wid = ConfReadBPM(self.ui.multi_dev_tbl, row_dev)
                    self.ui.multi_dev_tbl.setCellWidget(row, col, wid)

        hdr = self.ui.multi_dev_tbl.verticalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr = self.ui.multi_dev_tbl.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        self.ui.multi_dev_tbl.setHorizontalHeaderLabels(["Set Value To"] + devs)


class ConfReadBPM(QWidget):
    def __init__(self, parent, dev):
        super(ConfReadBPM, self).__init__(parent=parent)
        
        self.dev = dev
        
        self.main_lyt = QVBoxLayout()
        self.setLayout(self.main_lyt)

        self.make_row("L")
        self.make_row("H")

    def make_row(self, hilo):
        lyt = QHBoxLayout()
        
        lbl = QLabel("Max" if hilo == "H" else "Min")
        lbl.setFixedSize(25, 12)
        lbl.setStyleSheet("background-color: transparent")
        lyt.addWidget(lbl)

        wid = PyDMLabel(init_channel=f"ca://{self.dev}_{hilo}_RBV")
        # wid = PyDMLabel(init_channel=f"ca://{self.dev}:LABEL")
        wid.setMinimumWidth(64)
        lyt.addWidget(wid)

        wid = PyDMByteIndicator(init_channel=f"ca://{self.dev}_{hilo}_EN_RBV")
        # wid = PyDMByteIndicator(init_channel=f"ca://{self.dev}:VAL")
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
        lyt = QHBoxLayout()
        self.main_lyt.addLayout(lyt)
        
        lbl = QLabel("Max" if hilo == "H" else "Min")
        lbl.setFixedSize(25, 12)
        lbl.setStyleSheet("background-color: transparent")
        lyt.addWidget(lbl)

        chk = PyDMMultiCheckbox(init_channels=", ".join([f"{d}_{hilo}_EN" for d in self.devs]))
        # chk = PyDMMultiCheckbox(init_channels=", ".join([f"{d}:VAL" for d in self.devs]))
        lyt.addWidget(chk)

        edt = PyDMMultiLineEdit(init_channels=", ".join(f"{d}_{hilo}" for d in self.devs))
        # edt = PyDMMultiLineEdit(init_channels=", ".join(f"{d}:LABEL" for d in self.devs))
        edt.alarmSensitiveContent = True
        lyt.addWidget(edt)

        chk_val = all(caget_many([f"{d}_{hilo}_EN_RBV" for d in self.devs],
        # chk_val = all(caget_many([f"{d}:VAL" for d in self.devs],
                                 connection_timeout=(len(self.devs) * .1)))
        chk.setCheckState(chk_val)
        QTimer.singleShot(1, partial(edt.setEnabled, chk_val))

        try:
            chk.clicked.disconnect()
        except TypeError:
            pass
        chk.clicked.connect(self.chk_clicked)
        chk.toggled.connect(edt.setEnabled)

    @Slot(bool)
    def chk_clicked(self, chk):
        sndr = self.sender()
        if chk:
            vals = caget_many([f"{d[:-5]}_RBV" for d in sndr.channel.split(", ")],
            # print(sndr.channel.split(", "))
            # vals = caget_many([d.replace("VAL", "LABEL") for d in sndr.channel.split(", ")],
                              connection_timeout=(len(self.devs) * .1))
            # print(vals)
            equiv = True
            first = vals[0]

            for v in vals:
                if v != first:
                    equiv = False
                    break

            if not equiv:
                ret = QMessageBox.warning(self,"Differing Threshold Values",
                                          "Threshold values are different across multiple devices."
                                              "\n\nContinue writing to all devices?",
                                          QMessageBox.Yes | QMessageBox.No)
                if ret == QMessageBox.No:
                    sndr.setCheckState(False)
                    return

        sndr.send_value(chk)
