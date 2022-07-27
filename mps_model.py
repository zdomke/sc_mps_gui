import glob
import logging
import sqlalchemy
from os import path
from mps_database.mps_config import MPSConfig, models
from mps_database.tools.mps_names import MpsName


class MPSModel:
    def __init__(self, filename=None):
        logger = logging.getLogger(__name__)

        if filename and path.exists(filename):
            self.filename = filename
        else:
            if filename:
                logger.error("Given file does not exist. Using default .db file.")
            self.filename = self.set_filename()
        
        try:
            self.config = MPSConfig(self.filename)
            self.name = MpsName(self.config.session)
        except sqlalchemy.exc.DatabaseError:
            logger.error("Given file is not a database. Using default .db file.")
            self.filename = self.set_filename()
            self.config = MPSConfig(self.filename)
            self.name = MpsName(self.config.session)

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
        self.faults = self.config.session.query(models.Fault).all()
        self.fault_objects = sorted([self.name.getFaultObject(fault) for fault in self.faults])

    def get_faults(self):
        return self.fault_objects

    def get_fault_model(self, fault_description):
        return self.config.session.query(models.Fault).filter(models.Fault.description==fault_description).one()

    def get_fault_states(self, fault_description):
        return self.get_fault_model(fault_description).states

    def get_device(self, fault_description):
        fault = self.get_fault_model(fault_description)
        return self.name.getDeviceFromFault(fault)

    def get_device_inputs(self, fault_description):
        fault = self.get_fault_model(fault_description)
        dev = self.name.getDeviceFromFault(fault)

        return self.name.getInputsFromDevice(dev, fault)

def main():
    helper = MPSModel()
    helper.print_faults()

if __name__ == "__main__":
    main()