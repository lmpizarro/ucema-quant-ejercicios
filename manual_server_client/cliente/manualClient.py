import threading
from enum import Enum
import logging
import random
from pyfix.connection import ConnectionState, MessageDirection
from pyfix.client_connection import FIXClient
from pyfix.engine import FIXEngine
from pyfix.message import FIXMessage
from pyfix.event import TimerEventRegistration


class Side(Enum):
    buy = 1
    sell = 2


class Client(FIXEngine):
    def __init__(self):
        self.clOrdID = 0
        self.msgGenerator = None
        self._listening_thread = threading.Thread(target=self._startListening)
        self._listening = False

    def _startListening(self):
        FIXEngine.__init__(self, "client_example.store")
        # create a FIX Client using the FIX 4.4 standard
        self.client = FIXClient(self, "pyfix.FIX44", "TARGET", "SENDER")
        # we register some listeners since we want to know when the connection goes up or down
        self.client.addConnectionListener(self.onConnect, ConnectionState.CONNECTED)
        self.client.addConnectionListener(self.onDisconnect, ConnectionState.DISCONNECTED)
        try:
            # start our event listener indefinitely
            self.client.start('localhost', int("9898"))
            self._listening = True
            while True:
                self.eventManager.waitForEventWithTimeout(10.0)
                if not self._listening:
                    break
        finally:
            # some clean up before we shut down
            self.client.removeConnectionListener(self.onConnect, ConnectionState.CONNECTED)
            self.client.removeConnectionListener(self.onConnect, ConnectionState.DISCONNECTED)

    def start(self):
        command_thread = threading.Thread(target=self._startReadingCommands)
        self._listening_thread.start()
        command_thread.start()
        self._listening_thread.join()
        command_thread.join()

    def _printHelp(self):
        print("Los comandos son: ")
        print("\tsend                       ## Envia una orden al mercado")
        print("\texit                       ## Cierra el servidor")

    def _startReadingCommands(self):
        while True:
            command = input("--> ")
            if not command:
                self._printHelp()
            elif command.lower() == "help":
                self._printHelp()
            elif command.lower() == "send":
                pass
            elif command.lower() == 'exit':
                self._listening = False
                exit(0)
            else:
                print(f"Comando '{command}' invalido")
                self._printHelp()

    def onConnect(self, session):
        logging.info("Established connection to %s" % (session.address(),))
        # register to receive message notifications on the session which has just been created
        session.addMessageHandler(self.onLogin, MessageDirection.INBOUND, self.client.protocol.msgtype.LOGON)
        session.addMessageHandler(self.onExecutionReport, MessageDirection.INBOUND,
                                  self.client.protocol.msgtype.EXECUTIONREPORT)

    def onDisconnect(self, session):
        logging.info("%s has disconnected" % (session.address(),))
        # we need to clean up our handlers, since this session is disconnected now
        session.removeMessageHandler(self.onLogin, MessageDirection.INBOUND, self.client.protocol.msgtype.LOGON)

        if self.msgGenerator:
            self.eventManager.unregisterHandler(self.msgGenerator)

    def onLogin(self, connectionHandler, msg):
        logging.info("Logged in")

    def onExecutionReport(self, connectionHandler, msg):
        codec = connectionHandler.codec
        if codec.protocol.fixtags.ExecType in msg:
            if msg.getField(codec.protocol.fixtags.ExecType) == "0":
                side = Side(int(msg.getField(codec.protocol.fixtags.Side)))
                logging.debug("<--- [%s] %s: %s %s %s@%s" % (
                codec.protocol.msgtype.msgTypeToName(msg.getField(codec.protocol.fixtags.MsgType)),
                msg.getField(codec.protocol.fixtags.ClOrdID), msg.getField(codec.protocol.fixtags.Symbol), side.name,
                msg.getField(codec.protocol.fixtags.OrderQty), msg.getField(codec.protocol.fixtags.Price)))
            elif msg.getField(codec.protocol.fixtags.ExecType) == "4":
                reason = "Unknown" if codec.protocol.fixtags.Text not in msg else msg.getField(
                    codec.protocol.fixtags.Text)
                logging.info("Order Rejected '%s'" % (reason,))
        else:
            logging.error("Received execution report without ExecType")


def main():
    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)
    client = Client()
    client.start()
    logging.info("All done... shutting down")


if __name__ == '__main__':
    main()
