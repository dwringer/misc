from datetime import datetime as dt
from shutil import copy
from json import dumps as json_dumps
from os import environ, mkdir, listdir
from os.path import join as path_join, exists as path_exists
from selenium.webdriver import Firefox, FirefoxProfile
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


FIREFOX_BINARY = "C:\\Program Files\\Firefox Developer Edition\\firefox.exe"
GECKODRIVER_PATH = "C:\\Users\\Darren\\Downloads\\geckodriver\\"

CERTFILE_DB = "C:\\Users\\Darren\\AppData\\Roaming\\" +  \
              "Mozilla\\Firefox\\Profiles\\" +  \
              "9pml1p5t.dev-edition-default\\cert8.db"

BASE_DATA_PATH = "C:/DWR/Data/"

AUTO_DOWNLOAD_MIME_TYPES = [
    "application/octet-stream",
    "application/vnd.ms-excel",
    "application/msexcel",
    "application/x-msexcel",
    "application/x-ms-excel",
    "application/x-excel",
    "application/x-dos_ms_excel",
    "application/xls",
    "application/x-xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
]


class FirefoxBrowser(object):
    "A Firefox browser using geckodriver.exe with auto-download & saved certs"
    def __init__(self, download_path=None):
        "Prepare and launch Firefox browser"
        self.prepare_geckodriver(GECKODRIVER_PATH)
        self.downloadPath = self.make_download_path(download_path)
        self.profile = self.make_profile()
        self.capabilities = self.make_capabilities()
        self.browser = self.launch_browser()

    def launch_browser(self):
        "Import saved certificates to profile and launch Firefox"
        copy(CERTFILE_DB, self.profile.profile_dir)
        return Firefox(self.profile, capabilities=self.capabilities)

    def make_download_path(self, download_path):
        "Prepare download path, or BASE_DATA_PATH/<datestamp> if None"
        if download_path is None:
            _datestamp = dt.now().strftime("%Y%m%d")
            download_path = path_join(BASE_DATA_PATH, _datestamp)
        if not path_exists(download_path):
            mkdir(download_path)
        return download_path.replace('/', '\\')

    def prepare_geckodriver(self, geckodriver_path):
        "Ensure geckodriver.exe is accessible through the PATH env variable"
        if "geckodriver.exe" not in listdir(geckodriver_path):
            raise Exception("geckodriver.exe not found in " + geckodriver_path)
        _path = environ['PATH']
        _path = _path + ";" + geckodriver_path
        environ['PATH'] = _path

    def make_capabilities(self):
        "Create a direct-proxy browser capabilities object for Firefox"
        _capabilities = DesiredCapabilities.FIREFOX
        _capabilities["marionette"] = True
        _capabilities["binary"] = FIREFOX_BINARY
        _capabilities["proxy"] = json_dumps({'proxyType': 'direct'})
        _capabilities["firefox_profile"] = self.profile.encoded
        return _capabilities

    def make_profile(self):
        "Set up a profile to auto-download specific MIME types"
        _profile = FirefoxProfile()
        _profile.set_preference("browser.download.manager.showWhenStarting",
                                False)
        _profile.set_preference("browser.helperApps.alwaysAsk.force", False)
        _profile.set_preference("browser.helperApps.neverAsk.saveToDisk",
                                ', '.join(AUTO_DOWNLOAD_MIME_TYPES))
        _profile.set_preference("browser.download.dir", self.downloadPath)
        _profile.set_preference("browser.download.downloadDir",
                                self.downloadPath)
        _profile.set_preference("browser.download.defaultFolder",
                                self.downloadPath)
        _profile.set_preference("browser.download.folderList", 2)
        _profile.update_preferences()
        return _profile
