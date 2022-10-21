from os import path
from logging import getLogger
from pydm import Display
from models_pkg.mps_model import MPSModel
from mixins.summary import SummaryMixin
from mixins.logic import LogicMixin
from mixins.selection_detail import SelectionDetailsMixin


class MpsGuiDisplay(Display, SummaryMixin, LogicMixin, SelectionDetailsMixin):
    def __init__(self, parent=None, args=[], macros=None):
        super(MpsGuiDisplay, self).__init__(parent=parent, args=args,
                                            macros=macros)
        self.logger = getLogger(__name__)

        if 'DBFILE' in macros:
            self.model = MPSModel(macros['DBFILE'])
        else:
            self.model = MPSModel()

        self.faults = self.model.faults

        self.logic_init()
        self.selection_init()
        self.summary_init()

        self.logic_connections()
        self.selection_connections()
        self.summ_connections()

    # ~~~~ PyDM UI File Management ~~~~ #
    @staticmethod
    def ui_filename():
        return 'mps_gui_main.ui'

    def ui_filepath(self):
        return path.join(path.dirname(path.realpath(__file__)),
                         self.ui_filename())
