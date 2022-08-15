import glob
import logging
import sqlalchemy
from os import path
from mps_database.mps_config import MPSConfig, models
from mps_database.tools.mps_names import MpsName


class MPSModel:
    def __init__(self, filename=None):
        """Establish logger and establish connection to mps_database."""
        logger = logging.getLogger(__name__)

        if filename and path.exists(filename):
            self.filename = filename
        else:
            if filename:
                logger.error("File does not exist. Using default .db file.")
            self.filename = self.set_filename()
        
        try:
            self.config = MPSConfig(self.filename)
            self.name = MpsName(self.config.session)
        except sqlalchemy.exc.DatabaseError:
            logger.error("File is not a database. Using default .db file.")
            self.filename = self.set_filename()
            self.config = MPSConfig(self.filename)
            self.name = MpsName(self.config.session)

        self.faults = []
        self.fault_objects = {}
        self.set_faults()

    def set_filename(self):
        """Finds default database filename."""
        phys_top = path.expandvars("$PHYSICS_TOP")
        phys_top += "/mps_configuration/injector/"
        filename = glob.glob(phys_top + "mps_config*.db")[0]
        return filename

    def set_faults(self):
        """Populate fault_objects with FaultObjects from self.name."""
        self.faults = self.config.session.query(models.Fault).all()
        for fault in self.faults:
            desc = fault.description
            self.fault_objects[desc] = self.name.getFaultObject(fault)
        self.fault_objects = dict(sorted(self.fault_objects.items()))

    def get_faults(self):
        """Fault getter function."""
        return self.fault_objects

    def fault_to_dev(self, fault):
        """Get a models.Device object from a models.Fault object."""
        return self.name.getDeviceFromFault(fault)

    def fault_to_inp(self, fault):
        """Get a list of Inputs from a models.Device object."""
        dev = self.name.getDeviceFromFault(fault)
        return self.name.getInputsFromDevice(dev, fault)
