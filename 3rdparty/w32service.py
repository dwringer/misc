from os.path import splitext, abspath
from sys import modules

from win32serviceutil import ServiceFramework, StartService, InstallService
from win32service import (SERVICE_START_PENDING,
                          SERVICE_RUNNING,
                          SERVICE_STOP_PENDING,
                          SERVICE_STOPPED,
                          SERVICE_AUTO_START)
from win32event import (CreateEvent,
                        WaitForSingleObject,
                        SetEvent,
                        INFINITE)
from win32api import (Sleep,
                      SetConsoleCtrlHandler)


class Service(ServiceFramework):
    """Win32 Service template class.  Subclass and override start()/stop()."""
    _svc_name_ = ""
    _svc_display_name_ = ""
    _svc_reg_class_ = ""
    _svc_description_ = ""

    def __init__(o, *args):
        ServiceFramework.__init__(o, *args)
        o.log('init')
        o.stop_event = CreateEvent(None, 0, 0, None)

    def log(o, msg):
        with open("C:/python27/logs/pysvclog.txt", "a") as outf:
            outf.write(str(msg) + '\r\n')

    def sleep(self, secs):
        Sleep(1000 * secs, True)

    def SvcDoRun(o):
        o.ReportServiceStatus(SERVICE_START_PENDING)
        try:
            o.ReportServiceStatus(SERVICE_RUNNING)
            o.log('start')
            o.start()
            o.log('wait')
            WaitForSingleObject(o.stop_event, INFINITE)
            o.log('done')
        except Exception as e:
            o.log("Exception: %s" % e)
            o.SvcStop()

    def SvcStop(o):
        o.ReportServiceStatus(SERVICE_STOP_PENDING)
        o.log('stopping')
        o.stop()
        o.log('stopped')
        SetEvent(o.stop_event)
        o.ReportServiceStatus(SERVICE_STOPPED)

    def start(o):
        pass

    def stop(o):
        pass


def install_and_start(cls, name,
                      display_name=None,
                      description=None,
                      stay_alive=True):
    """Install and automatically start a service.
        cls          : the service class (derived from Service)
        name         : the service name
        display_name : name shown in service manager
        description  : detailed description of service
        stay_alive   : keep running on system logout"""
    cls._svc_name_ = name
    cls._svc_display_name_ = display_name or name
    cls._svc_description_ = description or (display_name or name)
    try:
        module_path = modules[cls.__module__].__file__
    except AttributeError:
        from sys import executable
        module_path = executable
    module_file = splitext(abspath(module_path))[0]
    cls._svc_reg_class_ = "%s.%s" % (module_file, cls.__name__)
    if stay_alive:
        SetConsoleCtrlHandler(lambda x: True, True)
    try:
        InstallService(cls._svc_reg_class_,
                       cls._svc_name_,
                       cls._svc_display_name_,
                       startType=SERVICE_AUTO_START,
                       description=cls._svc_description_)
        print 'Install ok'
        StartService(cls._svc_name_)
        print 'Start ok'
    except Exception as e:
        print str(e)
