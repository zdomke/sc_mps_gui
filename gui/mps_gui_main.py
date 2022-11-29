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
        super(MpsGuiDisplay, self).__init__(parent=parent, args=args, macros=macros,
                                            ui_filename=__file__.replace(".py", ".ui"))
        self.logger = getLogger(__name__)

        if 'DBFILE' in macros:
            self.model = MPSModel(macros['DBFILE'])
        else:
            self.model = MPSModel()

        self.logic_init()
        self.selection_init()
        self.summary_init()
        self.configure_init()

        self.logic_connections()
        self.selection_connections()
        self.summ_connections()
        self.configure_connections()
