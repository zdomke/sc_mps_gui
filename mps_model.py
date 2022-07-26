import glob
from os import path
from mps_database.mps_config import MPSConfig, models
from mps_database.tools.mps_names import MpsName


class MPSModel:
    def __init__(self, filename=None):
        if filename:
            self.filename = filename
        else:
            self.filename = self.set_filename()
        self.config = MPSConfig(self.filename)
        self.session = self.config.session
        self.name = MpsName(self.session)

        self.faults = []
        self.fault_objects = []
        self.set_faults()

    def print_faults(self):
        for fault in self.fault_objects:
            print("{0:55} {1}".format(fault.description + ':', fault.name))

    def set_filename(self):
        phys_top = path.expandvars("$PHYSICS_TOP") + "/mps_configuration/injector/"
        filename = glob.glob(phys_top + "mps_config*.db")[0]
        return filename

    def set_faults(self):
        self.faults = self.session.query(models.Fault).all()
        self.fault_objects = sorted([self.name.getFaultObject(fault) for fault in self.faults])

    def get_faults(self):
        return self.fault_objects


def main():
    helper = MPSModel()
    helper.print_faults()

if __name__ == "__main__":
    main()