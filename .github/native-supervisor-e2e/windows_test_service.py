"""Ephemeral pywin32 service used only by the native SCM validation."""

import servicemanager
import win32event
import win32service
import win32serviceutil


class HermesCodexSupervisorE2E(win32serviceutil.ServiceFramework):
    _svc_name_ = "HermesCodexSupervisorE2E"
    _svc_display_name_ = "Hermes Codex Supervisor E2E"

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        servicemanager.LogInfoMsg("Hermes native SCM validation service started")
        win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(HermesCodexSupervisorE2E)
