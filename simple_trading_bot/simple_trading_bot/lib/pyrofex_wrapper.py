import pyRofex

import simple_trading_bot.conf.remarkets_api_creds as rac
from simple_trading_bot.lib.singleton_metaclass import SingletonMetaClass


class PyRofexWrapper:
    """
    Class to ensure one and only one instance of pyRofex is initialized.
    """
    __metaclass__ = SingletonMetaClass

    def __init__(
            self,
            user=rac.USER,
            password=rac.PASS,
            account=rac.ACCOUNT,
            environment=pyRofex.Environment.REMARKET):
        self._environment = environment
        pyRofex.initialize(
            user=user,
            password=password,
            account=account,
            environment=self._environment)

    def __del__(self):
        self.close_websocket_connection_safely()

    def __getattr__(self, attribute):
        return getattr(pyRofex, attribute)

    def close_websocket_connection_safely(self):
        try:
            pyRofex.close_websocket_connection(self._environment)
        except AttributeError:
            pass
