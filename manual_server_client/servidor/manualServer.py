import threading
from enum import Enum
import logging
from pyfix.connection import ConnectionState, MessageDirection
from pyfix.engine import FIXEngine
from pyfix.message import FIXMessage
from pyfix.server_connection import FIXServer


class Side(Enum):
    buy = 1
    sell = 2


class Server(FIXEngine):
    def __init__(self):
        self.server = None
        self._listening_thread = threading.Thread(target=self._startListening)
        self._listening = False

    def start(self):
        command_thread = threading.Thread(target=self._startReadingCommands)
        self._listening_thread.start()
        command_thread.start()
        self._listening_thread.join()
        command_thread.join()

    def _printHelp(self):
        print("Los comandos son: ")
        print("\tbook                       ## Muestra el libro de ordenes actual")
        print("\tack [orderID]              ## Manda ack de un orden con orderID [orderID]")
        print("\tcancel [orderID]           ## Manda ack de cancelacion de orden con [orderID]")
        print("\tfill [orderID] [quantity]  ## Manda Fill de orderID con cantidad [quantity]")
        print("\torder [orderID]            ## Detalles de la orden [orderID]")
        print("\tremove [orderID]           ## Saca la orden [orderID] del libro")
        print("\treplace [orderID]          ## Manda un ReplaceAck para la orden [orderID]")
        print("\treplacepending [orderID]   ## Manda mensaje ReplacePending para la orden [orderID]")
        print("\texit                       ## Cierra el servidor")

    def _startReadingCommands(self):
        while True:
            command = input("--> ")
            if not command:
                self._printHelp()
            elif command.lower() == "help":
                self._printHelp()
            elif command.lower() == "book":
                pass
            elif command.lower()[:6] == "order ":
                pass
            elif command.lower()[:7] == "remove ":
                pass
            elif command.lower()[:4] == "ack ":
                pass
            elif command.lower()[:7] == "cancel ":
                pass
            elif command.lower()[:8] == "replace ":
                pass
            elif command.lower()[:15] == "replacepending ":
                pass
            elif command.lower()[:5] == "fill ":
                pass
            elif command.lower() == 'exit':
                self._listening = False
                exit(0)
            else:
                print(f"Comando '{command}' invalido")
                self._printHelp()

    def _startListening(self):
        FIXEngine.__init__(self, "server_example.store")
        # create a FIX Server using the FIX 4.4 standard
        self.server = FIXServer(self, "pyfix.FIX44")
        # we register some listeners since we want to know when the connection goes up or down
        self.server.addConnectionListener(self.onConnect, ConnectionState.CONNECTED)
        self.server.addConnectionListener(self.onDisconnect, ConnectionState.DISCONNECTED)
        # start our event listener indefinitely
        try:
            self.server.start('', int("9898"))
            self._listening = True
            while True:
                self.eventManager.waitForEventWithTimeout(10.0)
                if not self._listening:
                    break
        finally:
            # some clean up before we shut down
            self.server.removeConnectionListener(self.onConnect, ConnectionState.CONNECTED)
            self.server.removeConnectionListener(self.onConnect, ConnectionState.DISCONNECTED)

    def validateSession(self, targetCompId, senderCompId):
        logging.info("Received login request for %s / %s" % (senderCompId, targetCompId))
        return True

    def onConnect(self, session):
        logging.info("Accepted new connection from %s" % (session.address(),))
        # register to receive message notifications on the session which has just been created
        session.addMessageHandler(self.onLogin, MessageDirection.OUTBOUND, self.server.protocol.msgtype.LOGON)

    def onDisconnect(self, session):
        logging.info("%s has disconnected" % (session.address(),))
        # we need to clean up our handlers, since this session is disconnected now
        session.removeMessageHandler(self.onLogin, MessageDirection.OUTBOUND, self.server.protocol.msgtype.LOGON)

    def onLogin(self, connectionHandler, msg):
        codec = connectionHandler.codec
        logging.info("[" + msg[codec.protocol.fixtags.SenderCompID] + "] <---- " + codec.protocol.msgtype.msgTypeToName(
            msg[codec.protocol.fixtags.MsgType]))


def main():
    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)
    server = Server()
    try:
        server.start()
    except Exception as e:
        logging.error("Server failed with msg", e)
    finally:
        logging.info("All done... shutting down")


if __name__ == '__main__':
    main()
