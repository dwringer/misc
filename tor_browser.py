from selenium.webdriver import Firefox, FirefoxProfile, Chrome, ChromeOptions
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from stem.socket import ControlPort as TorControlPort
from stem.connection import authenticate as tor_authenticate

from json import dumps as json_dumps
from os import environ
from random import randint
from socket import socket, AF_INET, SOCK_STREAM
from subprocess import Popen
from tempfile import mkdtemp
from time import sleep


DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200

TOR_PATH = "C:/TOR/Browser/TorBrowser/Tor/"
TOR_HASH = "16:C9371DFEECC656226029B464635F25469FA4B0AB009F0518F5950DFE5E"
TOR_PWD = 'Wsdfg098'

CHROMEDRIVER_PATH = "C:/Users/Darren/Downloads/"
FIREFOX_BINARY = "C:\\Program Files\\Firefox Developer Edition\\firefox.exe"
GECKODRIVER_PATH = "C:\\Users\\Darren\\Downloads\\geckodriver\\"


class TorInstance(object):
    """A managed instance of a Tor connection"""
    def __init__(o, tor_path=TOR_PATH, pwd=TOR_PWD, pwd_hash=TOR_HASH):
        """Set up instance with specified Tor configuration parameters"""
        o.controlPort = None
        o.proxyPort = None
        o.dataPath = None
        o.torPath = tor_path
        o.pwd = pwd
        o.pwdHash = pwd_hash
        o.ctrlProcess = None

    def launch(o):
        """Launch Tor.exe instance"""
        o.controlPort, o.proxyPort = o._get_ports()
        o.dataPath = mkdtemp()
        params = ('"%stor.exe" ' % o.torPath +
                  '--nt-service ' +
                  '--HashedControlPassword "%s" ' % o.pwdHash +
                  '--ControlPort %d ' % o.controlPort +
                  '--SocksPort %d ' % o.proxyPort +
                  '--DataDirectory "%s"' % o.dataPath)
        print params
        o.ctrlProcess = Popen(params,
                              creationflags=(DETACHED_PROCESS &
                                             CREATE_NEW_PROCESS_GROUP))

    def start(o):
        """Authenticate with Tor controller and set up proxy connection"""
        o.controller = TorControlPort(port=o.controlPort)
        tor_authenticate(o.controller, password=o.pwd)
        while True:
            o.controller.send("GETINFO status/bootstrap-phase")
            info = o._rsp2dict(o.controller.recv().content())
            o.progressVar = info['PROGRESS'].strip()
            print o.progressVar
            try:
                if o.progressVar == '100':
                    break
                else:
                    raise Exception()
            except:
                sleep(0.2)

    def new_identity(o):
        o.controller.send("SIGNAL NEWNYM")
        if 'OK' not in o._rsp2dict(o.controller.recv().content()):
            raise Exception("SIGNAL NEWNYM not accepted by Tor")

    def kill(o):
        """Shut down the Tor.exe process"""
        o.ctrlProcess.kill()

    def _rsp2dict(o, rsp):
        return dict(map(lambda x: x if (len(x) == 2) else (x[0], ''),
                        map(lambda x: x.split('='),
                            rsp[0][2].split())))

    def _get_ports(o, n=2):
        portArray = []
        while len(portArray) < n:
            s = socket(AF_INET, SOCK_STREAM)
            while True:
                tryPort = randint(5001, 49151)
                if tryPort in portArray:
                    continue
                try:
                    s.bind(('localhost', tryPort))
                except:
                    continue
                break
            s.close()
            portArray.append(tryPort)
        return tuple(portArray)


class ProxyChrome(object):
    """Selenium Chrome webdriver through a specific proxy port"""
    def __init__(o, socks_port):
        o.options = ChromeOptions()
        o.options.add_argument("--proxy-server=socks5://127.0.0.1:%d" %
                               socks_port)
        o.options.add_argument("--incognito")
        o.browser = Chrome(CHROMEDRIVER_PATH + "chromedriver.exe",
                           chrome_options=o.options)


class ProxyFirefox(object):
    """Selenium Firefox webdriver through a specific proxy port"""
    def __init__(o, socks_port):
        o.profile = FirefoxProfile()
        prefs = [("webdriver.load.strategy", "unstable"),
                 ("places.history.enabled", False),
                 ("privacy.clearOnShutdown.offlineApps", True),
                 ("privacy.clearOnShutdown.passwords", True),
                 ("privacy.clearOnShutdown.siteSettings", True),
                 ("privacy.sanitize.sanitizeOnShutdown", True),
                 ("signon.rememberSignons", False),
                 ("network.cookie.lifetimePolicy", 2),
                 ("network.dns.disablePrefetch", True),
                 ("network.http.sendRefererHeader", 0),
                 ("network.proxy.type", 1),
                 ("network.proxy.socks_version", 5),
                 ("network.proxy.socks", '127.0.0.1'),
                 ("network.proxy.socks_port", socks_port),
                 ("network.proxy.socks_remote_dns", True),
                 ("permissions.default.image", 2),
                 ("network.http.proxy.keep-alive", False)]
        map(lambda x: o.profile.set_preference(x[0], x[1]), prefs)
        _path = environ['PATH']
        _path = _path + ";" + GECKODRIVER_PATH
        environ['PATH'] = _path
        _capabilities = DesiredCapabilities.FIREFOX
        _capabilities["marionette"] = True
        _capabilities["binary"] = FIREFOX_BINARY
        _capabilities["proxy"] = json_dumps(
            {'proxyType': 'manual',
             'socksProxy': '127.0.0.1:%d' % socks_port})
        o.browser = Firefox(o.profile, capabilities=_capabilities)


class TorBrowser(object):
    """Selenium Firefox webdriver using a Tor instance as a proxy"""
    def __init__(o, use_chrome=False):
        o.ti = TorInstance()
        o.ti.launch()
        o.ti.start()
        if not use_chrome:
            o.pf = ProxyFirefox(o.ti.proxyPort)
            o.pc = None
        else:
            o.pf = None
            o.pc = ProxyChrome(o.ti.proxyPort)

    def new_identity(o):
        o.ti.new_identity()

    def close(o):
        if o.pf is not None:
            o.pf.browser.quit()
        else:
            o.pc.browser.quit()
        o.ti.kill()
