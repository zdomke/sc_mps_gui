from qtpy.QtCore import Property
from pydm.widgets import (PyDMChannel, PyDMCheckbox, PyDMLineEdit)


class PyDMMultiCheckbox(PyDMCheckbox):
    def __init__(self, parent=None, init_channels=None):
        super(PyDMMultiCheckbox, self).__init__(parent, init_channel=init_channels)

    @Property(str)
    def channel(self):
        if self._channel:
            return self._channel
        return None

    @channel.setter
    def channel(self, value):
        if self._channel == value:
            return

        for address in self._channels:
            address.disconnect()
            self._channels.remove(address)

        self._channel = value
        if not self._channel:
            return

        for address in self._channel.split(", "):
            channel = PyDMChannel(address=address,
                                  connection_slot=self.connectionStateChanged,
                                  value_slot=None,
                                  severity_slot=self.alarmSeverityChanged,
                                  enum_strings_slot=self.enumStringsChanged,
                                  unit_slot=None,
                                  prec_slot=None,
                                  upper_ctrl_limit_slot=self.upperCtrlLimitChanged,
                                  lower_ctrl_limit_slot=self.lowerCtrlLimitChanged,
                                  upper_alarm_limit_slot=self.upper_alarm_limit_changed,
                                  lower_alarm_limit_slot=self.lower_alarm_limit_changed,
                                  upper_warning_limit_slot=self.upper_warning_limit_changed,
                                  lower_warning_limit_slot=self.lower_warning_limit_changed,
                                  value_signal=None,
                                  write_access_slot=None,
                                  timestamp_slot=self.timestamp_changed)

            if hasattr(self, 'unitChanged'):
                channel.unit_slot = self.unitChanged
            if hasattr(self, 'precisionChanged'):
                channel.prec_slot = self.precisionChanged
            if hasattr(self, 'send_value_signal'):
                channel.value_signal = self.send_value_signal
            if hasattr(self, 'writeAccessChanged'):
                channel.write_access_slot = self.writeAccessChanged
            channel.connect()
            self._channels.append(channel)


class PyDMMultiLineEdit(PyDMLineEdit):
    def __init__(self, parent=None, init_channels=None):
        super(PyDMMultiLineEdit, self).__init__(parent, init_channel=init_channels)

    @Property(str)
    def channel(self):
        if self._channel:
            return self._channel
        return None

    @channel.setter
    def channel(self, value):
        if self._channel == value:
            return

        for address in self._channels:
            address.disconnect()
            self._channels.remove(address)

        self._channel = value
        if not self._channel:
            return

        for address in self._channel.split(", "):
            channel = PyDMChannel(address=address,
                                  connection_slot=self.connectionStateChanged,
                                  value_slot=self.channelValueChanged,
                                  severity_slot=self.alarmSeverityChanged,
                                  enum_strings_slot=self.enumStringsChanged,
                                  unit_slot=None,
                                  prec_slot=None,
                                  upper_ctrl_limit_slot=self.upperCtrlLimitChanged,
                                  lower_ctrl_limit_slot=self.lowerCtrlLimitChanged,
                                  upper_alarm_limit_slot=self.upper_alarm_limit_changed,
                                  lower_alarm_limit_slot=self.lower_alarm_limit_changed,
                                  upper_warning_limit_slot=self.upper_warning_limit_changed,
                                  lower_warning_limit_slot=self.lower_warning_limit_changed,
                                  value_signal=None,
                                  write_access_slot=None,
                                  timestamp_slot=self.timestamp_changed)

            if hasattr(self, 'unitChanged'):
                channel.unit_slot = self.unitChanged
            if hasattr(self, 'precisionChanged'):
                channel.prec_slot = self.precisionChanged
            if hasattr(self, 'send_value_signal'):
                channel.value_signal = self.send_value_signal
            if hasattr(self, 'writeAccessChanged'):
                channel.write_access_slot = self.writeAccessChanged
            channel.connect()
            self._channels.append(channel)
