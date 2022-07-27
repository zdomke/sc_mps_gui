import json
from operator import setitem
from qtpy.QtGui import QFont
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QScrollArea, QWidget, QVBoxLayout,
                            QHBoxLayout, QLabel, QTableWidget,
                            QTableWidgetItem, QSizePolicy, QHeaderView,
                            QSpacerItem, QAbstractItemView)
from pydm.widgets.label import PyDMLabel
from pydm.widgets.related_display_button import PyDMRelatedDisplayButton


class SelectionDetail(QScrollArea):
    def __init__(self, parent=None, mps_model=None, fault=None, *args, **kwargs):
        super(SelectionDetail, self).__init__(*args, **kwargs)

        self.details_init()

        self.truth_row_height = self.truth_table.verticalHeader().sectionSize(0)
        self.truth_header_height = self.truth_table.horizontalHeader().height()
        self.pv_row_height = self.pv_table.verticalHeader().sectionSize(0)
        self.pv_header_height = self.pv_table.horizontalHeader().height()
        
        # Used for converting the given destination.id to truth_table column index
        self.dest_order = [-1, -1, 3, 2, 4, 5, 1, 6]

        # self.default_tables(1, 1)
        
        if mps_model and fault:
            self.set_fault(mps_model, fault)
        else:
            self.hide()
            
    # ~~~~ Section Management ~~~~ #
     # ~~ Set Fault ~~ #
    def set_fault(self, mps_model, fault):
        self.bypass_btn.macros = "{{\"DEVICE_BYP\":\"{}\"}}".format(fault.name)
        self.name_lbl.setText(fault.description)
        self.state_lbl.channel = fault.state
        # self.ignored_lbl      Worry about this later

        self.pop_truth_table(mps_model, fault.description)
        self.pop_pv_table(mps_model, fault.description)

     # ~~ Truth Table ~~ #
    def default_truth_table(self, truth_row_count):
        self.truth_table.clearContents()
        self.truth_table.setRowCount(truth_row_count)
        for i in range(truth_row_count):
            self.default_row(self.truth_table, i, 8)
        self.truth_table.setFixedHeight((truth_row_count * self.truth_row_height)
                                        + self.truth_header_height + 2)

    def pop_truth_table(self, mps_model, fault_desc):
        fault_states = mps_model.get_fault_states(fault_desc)

        if "X Orbit" in fault_desc:
            shift_val = 8
        elif "Y Orbit" in fault_desc:
            shift_val = 16
        else:
            shift_val = 0

        shifted_val = fault_states[-1].device_state.value >> shift_val
        max_len = len(format(shifted_val, 'b'))
    
        self.default_truth_table(len(fault_states))
        for i, state in enumerate(fault_states):
            self.truth_table.setItem(i, 0, CellItem(state.device_state.description))

            shifted_val = state.device_state.value >> shift_val
            value_str = format(shifted_val, 'b').zfill(max_len)
            value_str = value_str.replace('0', 'F').replace('1', 'T')
            self.truth_table.setItem(i, 1, CellItem(value_str))

            for cl in state.allowed_classes:
                if cl.beam_class.name == "Full":
                    continue

                col = self.dest_order.index(cl.beam_destination.id)
                self.truth_table.setItem(i, col, CellItem(cl.beam_class.name))

     # ~~ PV Table ~~ #
    def default_pv_table(self, pv_row_count, pv_col_count):
        self.pv_table.clearContents()
        self.pv_table.setRowCount(pv_row_count)
        self.pv_table.setColumnCount(pv_col_count)

        if pv_col_count == 4:
            self.pv_table.setHorizontalHeaderLabels(["Bit Position", "Current PV",
                                                    "Latched PV", "Related Information"])
        elif pv_col_count == 5:
            self.pv_table.setHorizontalHeaderLabels(["Bit Position", "Current PV",
                                                    "Latched PV", "Channel",
                                                    "Related Information"])
            self.pv_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)

        for i in range(pv_row_count):
            self.default_row(self.pv_table, i, pv_col_count)
        self.pv_table.setFixedHeight((pv_row_count * self.pv_row_height)
                                     + self.pv_header_height + 2)

    def pop_pv_table(self, mps_model, fault_desc):
        dev = mps_model.get_device(fault_desc)
        inputs = mps_model.get_device_inputs(fault_desc)
        analog = int(dev.is_analog())
        dev_macros = self.node_macros(dev)

        if len(inputs) == 0:
            self.where.hide()
            self.pv_table.hide()
            return

        self.default_pv_table(len(inputs), 4 + analog)
        for i, inp in enumerate(inputs):
            self.pv_table.setItem(i, 0, CellItem(str(i)))

            # This PV should be different for analog devices
            self.pv_table.setItem(i, 1, CellItem(inp + "_SCMPSC"))

            # This PV should be different for analog devices
            self.pv_table.setItem(i, 2, CellItem(inp + "_SCMPS"))

            if analog:
                self.pv_table.setItem(i, 3, CellItem(str(dev.channel.number)))

            node_btn = PyDMRelatedDisplayButton(filename="$PYDM/mps/mps_cn_inputs.ui")
            node_btn.setText("Link Node {}...".format(dev_macros['ID']))
            node_btn.showIcon = False
            node_btn.openInNewWindow = True
            node_btn.macros = json.dumps(dev_macros)
            self.pv_table.setCellWidget(i, (3 + analog), node_btn)

     # ~~ Helper Functions ~~ #
    def node_macros(self, dev):
        ret_macros = {}
        ret_macros['ID'] = dev.card.link_node.lcls1_id
        ret_macros['LN'] = dev.card.link_node.lcls1_id
        ret_macros['AREA'] = dev.area.lower()
        ret_macros['AREAU'] = dev.area

        return ret_macros

    def default_row(self, table, row, column_count):
        for i in range(column_count):
            table.setItem(row, i, CellItem("--"))

    # ~~~~ Widget Builder & Initialization ~~~~ #
    def details_init(self):
        self.main_wid = QWidget(self)
        self.main_layout = QVBoxLayout()

        layout = QHBoxLayout()
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        lbl = QLabel("Selection Details")
        lbl.setFont(font)
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding)
        self.bypass_btn = PyDMRelatedDisplayButton(filename="$PYDM/mps/mps_bypass.ui")
        self.bypass_btn.setText("Bypass...")
        self.bypass_btn.showIcon = False
        self.bypass_btn.openInNewWindow = True
        layout.addWidget(lbl)
        layout.addSpacerItem(spacer)
        layout.addWidget(self.bypass_btn)
        self.main_layout.addLayout(layout)

        layout = QHBoxLayout()
        lbl = QLabel("Name:")
        lbl.setSizePolicy(QSizePolicy())
        self.name_lbl = QLabel("<Display Name>", self.main_wid)
        layout.addWidget(lbl)
        layout.addWidget(self.name_lbl)
        self.main_layout.addLayout(layout)

        layout = QHBoxLayout()
        lbl = QLabel("Current State:")
        lbl.setSizePolicy(QSizePolicy())
        self.state_lbl = PyDMLabel(self.main_wid)
        layout.addWidget(lbl)
        layout.addWidget(self.state_lbl)
        self.main_layout.addLayout(layout)

        layout = QHBoxLayout()
        lbl = QLabel("Ignored When:")
        lbl.setSizePolicy(QSizePolicy())
        self.ignored_lbl = QLabel("<Ignored Conditions>", self.main_wid)
        layout.addWidget(lbl)
        layout.addWidget(self.ignored_lbl)
        self.main_layout.addLayout(layout)

        self.truth_table = QTableWidget(1, 8, self.main_wid)
        self.truth_table.setHorizontalHeaderLabels(["State", "Value", "SC_BSYD",
                                                    "SC_DIAG0", "SC_HXR", "SC_SXR",
                                                    "LASER", "SC_LESA"])
        self.truth_table.verticalHeader().hide()
        self.truth_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.truth_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        truth_header = self.truth_table.horizontalHeader()
        truth_header.setDefaultSectionSize(120)
        truth_header.setResizeMode(QHeaderView.Interactive)
        truth_header.setStretchLastSection(True)
        self.main_layout.addWidget(self.truth_table)

        font = QFont()
        font.setPointSize(8)
        self.where = QLabel("Where:")
        self.where.setFont(font)
        self.main_layout.addWidget(self.where)

        self.pv_table = QTableWidget(1, 4, self.main_wid)
        self.pv_table.setHorizontalHeaderLabels(["Bit Position", "Current PV",
                                                 "Latched PV", "Related Information"])
        self.pv_table.verticalHeader().hide()
        self.pv_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        pv_header = self.pv_table.horizontalHeader()
        pv_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        pv_header.setSectionResizeMode(1, QHeaderView.Stretch)
        pv_header.setSectionResizeMode(2, QHeaderView.Stretch)
        pv_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.main_layout.addWidget(self.pv_table)

        self.main_wid.setLayout(self.main_layout)
        self.setWidget(self.main_wid)
        self.setWidgetResizable(True)


# ~~~~ Table Cell Object ~~~~ #
class CellItem(QTableWidgetItem):
    def __init__(self, text: str, parent=None, *args, **kwargs):
        super(CellItem, self).__init__(text, *args, **kwargs)
        flags = self.flags()
        flags = flags ^ Qt.ItemIsEditable
        self.setFlags(flags)
        self.setTextAlignment(Qt.AlignCenter)
