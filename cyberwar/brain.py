import time
import os
import translations


class BrainCore:
    def __init__(self):
        self.gameSocket = open("game://", "rb+")
        ccSocketName = "default://20181.1.1.1:10013"
        try:
            self.ccSocket = open(ccSocketName, "rb+")
        except:
            self.ccSocket = None
        self.translator = translations.NetworkTranslator()
        self.map = None
        self.DIRECTIONS_SHORT = {
            "n": "north",
            "ne": "north-east",
            "e": "east",
            "se": "south-east",
            "s": "south",
            "sw": "south-west",
            "w": "west",
            "nw": "north-west"
        }
        self.moveable = True
        self.map = {}

    def getNextMessage(self, translator, buffer):
        complete, mData = translator.HasMessage(buffer)
        if not complete:
            return None, buffer
        mt, m, headers, hOff, bLen = mData
        body, buffer = buffer[hOff:hOff + bLen], buffer[hOff + bLen:]
        msg = translator.unmarshallFromNetwork(mt, m, headers, body)
        return msg, buffer

    def autoExplore(self):
        while self.moveable:
            direction = "e"
            if direction in self.DIRECTIONS_SHORT:
                direction = self.DIRECTIONS_SHORT[direction]
            cmdObj = translations.MoveCommand(direction)
            sendData = self.translator.marshallToNetwork(cmdObj)
            os.write(self.gameSocket.fileno(), sendData)
            time.sleep(0.8)

    def brainLoop(self):

        loop = 0
        hb = None
        gameDataStream = b""

        while True:
            loop += 1
            gameData = os.read(self.gameSocket.fileno(), 1024)  # max of 1024
            gameDataStream += gameData
            if gameDataStream:
                msg, gameDataStream = self.getNextMessage(self.translator, gameDataStream)
                if isinstance(msg, translations.BrainConnectResponse):
                    self.translator = translations.NetworkTranslator(*msg.attributes)
                    hb = msg
            if (not gameData) and hb and (loop % 30 == 0) and self.ccSocket:
                # every thirty seconds, send heartbeat to cc
                try:
                    os.write(self.ccSocket.fileno(), self.translator.marshallToNetwork(hb))
                except:
                    self.ccSocket = None

            try:
                if self.ccSocket:
                    ccData = os.read(self.ccSocket.fileno(), 1024)
                else:
                    ccData = b""
            except:
                ccData = b""
                self.ccSocket = None

            if gameData and self.ccSocket:
                try:
                    f = open("/tmp/received.txt", "ab+")
                    f.write(str(gameData).encode())
                    f.close()
                    os.write(self.ccSocket.fileno(), gameData)
                except:
                    self.ccSocket = None
            if ccData:
                if ccData == b"CMD auto_explore braininterface/1.0\nContent_length: 0\n\n":
                    self.moveable = False
                    time.sleep(1)
                    self.moveable = True
                    respond = self.translator.marshallToNetwork(translations.AutoExploreReceivedEvent())
                    os.write(self.ccSocket.fileno(), respond)
                    self.autoExplore()
                elif ccData == b"CMD stay braininterface/1.0\nContent_length: 0\n\n":
                    self.moveable = False
                    respond = self.translator.marshallToNetwork(translations.StayReceivedEvent())
                    os.write(self.ccSocket.fileno(), respond)
                elif ccData == b"CMD getmap braininterface/1.0\nContent_length: 0\n\n":
                    respond = self.translator.marshallToNetwork(translations.MapInfoResponse(self.map))
                    os.write(self.ccSocket.fileno(), respond)
                else:
                    os.write(self.gameSocket.fileno(), ccData)

            if not gameData and not gameDataStream and not ccData:
                time.sleep(.5)  # sleep half a second every time there's no data

            if not self.ccSocket and loop % 60 == 0:
                # if the gamesock didn't open or is dead, try to reconnect
                # once per minute
                try:
                    self.ccSocket = open(ccSocketName, "rb+")
                except:
                    self.ccSocket = None


if __name__ == "__main__":
    try:
        b = BrainCore()
        b.brainLoop()
    except Exception as e:
        print("Brain failed because {}".format(e))

        f = open("/tmp/error.txt", "wb+")
        f.write(str(e).encode())
        f.close()
