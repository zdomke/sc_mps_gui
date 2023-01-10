from logging import getLogger
from pydm import Display
from models_pkg.mps_model import MPSModel
from mixins.summary import SummaryMixin
from mixins.logic import LogicMixin
from mixins.selection_detail import SelectionDetailsMixin
from mixins.configure import ConfigureMixin


class MpsGuiDisplay(Display, SummaryMixin, LogicMixin, SelectionDetailsMixin,
                    ConfigureMixin):
    def __init__(self, parent=None, args=[], macros=None, ui_filename=None):

        cud_mode = False
        if 'CUD' in macros:
            cud_mode = (macros['CUD'] == "True")

        if cud_mode:
            ui_filename = 'mps_cud_main.ui'
        else:
            ui_filename = __file__.replace(".py", ".ui")

        super(MpsGuiDisplay, self).__init__(parent=parent, args=args,
                                            macros=macros, ui_filename=ui_filename)
        self.logger = getLogger(__name__)

        if 'DBFILE' in macros:
            self.model = MPSModel(macros['DBFILE'])
        else:
            self.model = MPSModel()

        self.logic_init(cud_mode=cud_mode)
        self.summary_init(cud_mode=cud_mode)
        if not cud_mode:
            self.configure_init()
            self.selection_init()

        self.logic_connections(cud_mode=cud_mode)
        if not cud_mode:
            self.configure_connections()
            self.selection_connections()
            self.summ_connections()
