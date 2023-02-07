from models_pkg.app_status_model import AppStatusTable


class AppStatusMixin:
    def app_status_init(self):
        """Initializer for the App Status tab."""
        self.app_model = AppStatusTable(self, self.model.config.Session)
