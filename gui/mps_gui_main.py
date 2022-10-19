from logging import getLogger
from subprocess import run
from pydm import Display
from models_pkg.mps_model import MPSModel
from mixins.summary import SummaryMixin
from mixins.logic import LogicMixin
from mixins.selection_detail import SelectionDetailsMixin
from mixins.configure import ConfigureMixin
from mixins.ignore import IgnoreMixin
from mixins.app_status import AppStatusMixin
from mixins.recent_faults import RecentFaultsMixin


class MpsGuiDisplay(Display, SummaryMixin, LogicMixin, SelectionDetailsMixin,
                    ConfigureMixin, IgnoreMixin, AppStatusMixin, RecentFaultsMixin):
    def git_version(self):
        git_cmd = run("git describe --tags",
                      text=True,
                      shell=True,
                      capture_output=True)
        return git_cmd.stdout.strip()

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

        if 'DB_FILE' in macros:
            self.model = MPSModel(macros['DB_FILE'])
        else:
            self.model = MPSModel()

        self.logic_init(cud_mode=cud_mode)
        self.summary_init(cud_mode=cud_mode)
        if not cud_mode:
            self.ui.ftr_ver_lbl.setText(self.git_version())
            self.configure_init()
            self.selection_init()
            self.ignore_init()
            self.app_status_init()
            self.recent_init()

        self.logic_connections(cud_mode=cud_mode)
        if not cud_mode:
            self.configure_connections()
            self.selection_connections()
            self.recent_connections()
            self.summ_connections()
            self.ignore_connections()
            self.app_status_connections()
