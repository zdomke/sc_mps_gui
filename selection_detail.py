import json
from qtpy.QtGui import QFont
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QScrollArea, QWidget, QVBoxLayout, QHBoxLayout,
                            QLabel, QTableWidget, QTableWidgetItem,
                            QSizePolicy, QHeaderView, QSpacerItem,
                            QAbstractItemView)
from pydm.widgets.label import PyDMLabel
from pydm.widgets.related_display_button import PyDMRelatedDisplayButton


class SelectionDetail(QScrollArea):
    def __init__(self, parent=None, mps_model=None, fault=None):
        super(SelectionDetail, self).__init__()

        self.model = mps_model
        self.init_wid()
        
        # Destination.id -> truth_table column index conversion
        self.dest_order = [-1, -1, 3, 2, 4, 5, 1, 6]

        if fault:
            self.set_fault(fault)
        else:
            self.hide()
            
    # ~~~~ Section Management ~~~~ #
     # ~~ Set Fault ~~ #
    def set_fault(self, fault_obj):
        """Populate all labels & tables to represent the given fault.
        """
        self.fault_obj = fault_obj
        self.fault = self.model.desc_to_fault(fault_obj.description)
        self.dev = self.model.fault_to_dev(self.fault)
        self.inp = self.model.fault_to_inp(self.fault)

        self.byp_btn.macros = json.dumps({"DEVICE_BYP": self.fault_obj.name})
        self.name_lbl.setText(self.fault_obj.description)
        self.state_lbl.channel = self.fault_obj.state

        self.ignored_conditions()
        self.pop_truth_table()
        self.pop_pv_table()

     # ~~ Ignored Conditions ~~ #
    def ignored_conditions(self):
        """Set the selection's ignored conditions consisting of a comma
        separated list of condition descriptions.
        """
        cond_list = [ign.condition.description
                     for ign in self.dev.ignore_conditions]
        ign_str = ','.join(cond_list)

        if not ign_str:
            ign_str = "--"
            
        self.ignored_lbl.setText(ign_str)

     # ~~ Truth Table ~~ #
    def clear_truth_table(self, truth_row_count):
        """Clear contents of truth_table, then set the table size."""
        self.truth_tbl.clearContents()
        self.truth_tbl.setRowCount(truth_row_count)
        for i in range(truth_row_count):
            self.default_row(self.truth_tbl, i, 8)
        self.truth_tbl.setFixedHeight((truth_row_count * self.truth_row_h)
                                      + self.truth_hdr_h + 2)

    def pop_truth_table(self):
        """Populate the truth_table. Value is a binary number
        represented as F's and T's. Allowed classes fill destinations.
        """
        if "X Orbit" in self.fault_obj.description:
            shift_val = 8
        elif "Y Orbit" in self.fault_obj.description:
            shift_val = 16
        else:
            shift_val = 0

        shifted_val = self.fault.states[-1].device_state.value >> shift_val
        max_len = len(format(shifted_val, 'b'))
    
        self.clear_truth_table(len(self.fault.states))
        for i, state in enumerate(self.fault.states):
            item0 = CellItem(state.device_state.description)

            shifted_val = state.device_state.value >> shift_val
            value_str = format(shifted_val, 'b').zfill(max_len)
            value_str = value_str.replace('0', 'F').replace('1', 'T')
            item1 = CellItem(value_str)

            self.truth_tbl.setItem(i, 0, item0)
            self.truth_tbl.setItem(i, 1, item1)

            for cl in state.allowed_classes:
                if cl.beam_class.name == "Full":
                    continue

                col = self.dest_order.index(cl.beam_destination.id)
                item = CellItem(cl.beam_class.name)
                self.truth_tbl.setItem(i, col, item)

     # ~~ PV Table ~~ #
    def clear_pv_table(self, pv_row_count):
        """Clear contents of pv_table, then set the table size."""
        self.pv_tbl.clearContents()
        self.pv_tbl.setRowCount(pv_row_count)

        for i in range(pv_row_count):
            self.default_row(self.pv_tbl, i, 4)
        self.pv_tbl.setFixedHeight((pv_row_count * self.pv_row_h)
                                     + self.pv_hdr_h + 2)

    def pop_pv_table(self):
        """Display all PVs used by digital devices or all inputs of
        analog devices. Rightmost column is a button to open the link
        node associated with the faulted device.
        """
        if len(self.inp) == 0:
            self.where.hide()
            self.pv_tbl.hide()
            return

        analog = self.dev.is_analog()
        dev_macros = self.node_macros()
        inputs_file = "$PYDM/mps/mps_cn_inputs.ui"

        if analog:
            row_count = len(self.fault.states)
        else:
            row_count = len(self.inp)

        self.clear_pv_table(row_count)
        for i in range(row_count):
            if analog:
                pv = "{}_T{}_SCMPS".format(self.inp[0], i)
            else:
                pv = "{}_SCMPS".format(self.inp[i])

            item0 = CellItem(str(i))
            item1 = CellItem(pv + "C")
            item2 = CellItem(pv)
            self.pv_tbl.setItem(i, 0, item0)
            self.pv_tbl.setItem(i, 1, item1)
            self.pv_tbl.setItem(i, 2, item2)

            ln = self.dev.card.link_node.lcls1_id
            card = self.dev.card.number
            if self.dev.card.number == 1:
                card = "RTM"
            if analog:
                ch = self.dev.channel.number
            else:
                ch = self.dev.inputs[i].channel.number
            btn_text = "LN {}, Card {}, Ch {}...".format(ln, card, ch)

            node_btn = PyDMRelatedDisplayButton(filename=inputs_file)
            node_btn.setText(btn_text)
            node_btn.showIcon = False
            node_btn.openInNewWindow = True
            node_btn.macros = json.dumps(dev_macros)
            self.pv_tbl.setCellWidget(i, 3, node_btn)

     # ~~ Helper Functions ~~ #
    def node_macros(self):
        """Populate the macros dict used by pv_table"""
        ret_macros = {}
        ret_macros['ID'] = self.dev.card.link_node.lcls1_id
        ret_macros['LN'] = self.dev.card.link_node.lcls1_id
        ret_macros['AREA'] = self.dev.area.lower()
        ret_macros['AREAU'] = self.dev.area

        return ret_macros

    def default_row(self, table, row, column_count):
        """Set all cells of a given row of a given table to --."""
        for i in range(column_count):
            table.setItem(row, i, CellItem("--"))

    # ~~~~ Widget Builder & Initialization ~~~~ #
    def init_wid(self):
        """Initialize the Selection Detail widget to be filled later."""
        self.main_wid = QWidget(self)
        self.main_lyt = QVBoxLayout()

        # First row: Selection Details label and Bypass button
        lyt = QHBoxLayout()
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        lbl = QLabel("Selection Details")
        lbl.setFont(font)
        spcr = QSpacerItem(40, 20, QSizePolicy.Expanding)
        byp_file = "$PYDM/mps/mps_bypass.ui"
        self.byp_btn = PyDMRelatedDisplayButton(filename=byp_file)
        self.byp_btn.setText("Bypass...")
        self.byp_btn.showIcon = False
        self.byp_btn.openInNewWindow = True
        lyt.addWidget(lbl)
        lyt.addSpacerItem(spcr)
        lyt.addWidget(self.byp_btn)
        self.main_lyt.addLayout(lyt)

        # Second row: Fault name
        lyt = QHBoxLayout()
        lbl = QLabel("Name:")
        lbl.setSizePolicy(QSizePolicy())
        self.name_lbl = QLabel("<Display Name>", self.main_wid)
        lyt.addWidget(lbl)
        lyt.addWidget(self.name_lbl)
        self.main_lyt.addLayout(lyt)

        # Third row: Fault state
        lyt = QHBoxLayout()
        lbl = QLabel("Current State:")
        lbl.setSizePolicy(QSizePolicy())
        self.state_lbl = PyDMLabel(self.main_wid)
        lyt.addWidget(lbl)
        lyt.addWidget(self.state_lbl)
        self.main_lyt.addLayout(lyt)

        # Fourth row: Ignored conditions of the given fault
        lyt = QHBoxLayout()
        lbl = QLabel("Ignored When:")
        lbl.setSizePolicy(QSizePolicy())
        self.ignored_lbl = QLabel("<Ignored Conditions>", self.main_wid)
        lyt.addWidget(lbl)
        lyt.addWidget(self.ignored_lbl)
        self.main_lyt.addLayout(lyt)

        # Fifth row: Truth table that displays all possible states of
        # the faulted device as well as the conditions for each state.
        hdr_lbls = ["State", "Value", "SC_BSYD", "SC_DIAG0", "SC_HXR",
                    "SC_SXR", "LASER", "SC_LESA"]
        self.truth_tbl = QTableWidget(1, 8, self.main_wid)
        self.truth_tbl.setHorizontalHeaderLabels(hdr_lbls)
        self.truth_tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.truth_tbl.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        hdr = self.truth_tbl.verticalHeader()
        hdr.hide()
        self.truth_row_h = hdr.sectionSize(0)
        hdr = self.truth_tbl.horizontalHeader()
        hdr.setDefaultSectionSize(120)
        hdr.setResizeMode(QHeaderView.Interactive)
        hdr.setStretchLastSection(True)
        self.truth_hdr_h = hdr.height()
        self.main_lyt.addWidget(self.truth_tbl)

        # Sixth row: Label that says "Where:"
        font = QFont()
        font.setPointSize(8)
        self.where = QLabel("Where:")
        self.where.setFont(font)
        self.main_lyt.addWidget(self.where)

        # Seventh row: PV Table that shows all associated PVs with the
        # faulted device. The last column is a related display button.
        hdr_lbls = ["Bit Position", "Current PV",
                    "Latched PV", "Related Information"]
        self.pv_tbl = QTableWidget(1, 4, self.main_wid)
        self.pv_tbl.setHorizontalHeaderLabels(hdr_lbls)
        hdr = self.pv_tbl.verticalHeader()
        hdr.hide()
        self.pv_row_h = hdr.sectionSize(0)
        self.pv_tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        hdr = self.pv_tbl.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.pv_hdr_h = hdr.height()
        self.main_lyt.addWidget(self.pv_tbl)

        self.main_wid.setLayout(self.main_lyt)
        self.setWidget(self.main_wid)
        self.setWidgetResizable(True)


# ~~~~ Table Cell Object ~~~~ #
class CellItem(QTableWidgetItem):
    """Personalized QTableWidgetItem that sets preferred settings."""
    def __init__(self, text: str, parent=None, *args, **kwargs):
        super(CellItem, self).__init__(text, *args, **kwargs)
        flags = self.flags()
        flags = flags ^ Qt.ItemIsEditable
        self.setFlags(flags)
        self.setTextAlignment(Qt.AlignCenter)
