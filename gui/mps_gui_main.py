from os import path
from qtpy.QtCore import Qt
from pydm import Display
from models_pkg.mps_model import MPSModel
from mixins.summary import SummaryMixin
from mixins.logic import LogicMixin


class MpsGuiDisplay(Display, SummaryMixin, LogicMixin):
    def __init__(self, parent=None, args=[], macros=None):
        super(MpsGuiDisplay, self).__init__(parent=parent, args=args,
                                            macros=macros)
        if 'DBFILE' in macros:
            self.model = MPSModel(macros['DBFILE'])
        else:
            self.model = MPSModel()
        self.faults = self.model.get_faults()
        
        self.faulted_channels = []
        self.bypassed_channels = []
        self.ignored_channels = []
        self.faulted_pvs = {}
        self.bypassed_pvs = {}
        self.ignored_pvs = {}

        self.sort_order = Qt.AscendingOrder
        self.pop_desc()
        
        self.summary_init()
        self.bypass_init()
        self.ignored_init()
        self.logic_init()

        self.ui.a_sort_btn.clicked.connect(self.sort_logic_table)
        self.ui.flt_sort_btn.clicked.connect(self.sort_logic_table)
        self.ui.byp_sort_btn.clicked.connect(self.sort_logic_table)
        self.ui.order_btn.clicked.connect(self.set_sort_order)
        self.ui.logic_filter_edt.textChanged.connect(self.search_logic_table)
        self.ui.logic_tbl.itemSelectionChanged.connect(self.fault_selected)

    # ~~~~ PyDM UI File Management ~~~~ #
    @staticmethod
    def ui_filename():
        return 'mps_gui_main.ui'

    def ui_filepath(self):
        return path.join(path.dirname(path.realpath(__file__)),
                         self.ui_filename())
