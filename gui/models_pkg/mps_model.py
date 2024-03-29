from os import path
from glob import glob
from logging import getLogger
from sqlalchemy.exc import DatabaseError
from mps_database.models import (Fault, BeamDestination)
from mps_database.mps_config import MPSConfig
from mps_database.tools.mps_names import MpsName


class MPSModel:
    def __init__(self, filename=None):
        """Establish logger and establish connection to mps_database."""
        logger = getLogger(__name__)

        if filename and path.exists(filename):
            self.filename = filename
        else:
            if filename:
                logger.error("File does not exist. Using default .db file.")
            self.filename = self.set_filename()

        try:
            self.config = MPSConfig(self.filename)
            self.name = MpsName(self.config.session)
        except DatabaseError:
            logger.error("File is not a database. Using default .db file.")
            self.filename = self.set_filename()
            self.config = MPSConfig(self.filename)
            self.name = MpsName(self.config.session)

        self.get_faults()
        self.get_dests()

    def set_filename(self):
        """Finds default database filename."""
        phys_top = path.expandvars("$PHYSICS_TOP")
        phys_top += "/mps_configuration/current/"
        filename = glob(phys_top + "mps_config*.db")[0]
        return filename

    def get_faults(self):
        """Populate faults with FaultObjects from self.name."""
        self.faults = [self.name.getFaultObject(fault) for fault in
                       self.config.session.query(Fault).all()]

    def get_dests(self):
        """Populate list of Destination names. Move 2 columns for GUI."""
        self.dest_lst = [d.name for d in
                         self.config.session.query(BeamDestination).all()]
        self.dest_lst.insert(4, self.dest_lst.pop(0))
        self.dest_lst.insert(1, self.dest_lst.pop(0))

    def fault_to_dev(self, fault):
        """Get a models.Device object from a models.Fault object."""
        return self.name.getDeviceFromFault(fault)

    def fault_to_inp(self, fault):
        """Get a list of Inputs from a models.Device object."""
        dev = self.name.getDeviceFromFault(fault)
        return self.name.getInputsFromDevice(dev, fault)
