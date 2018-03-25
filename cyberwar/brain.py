import time
import os
import translations


class BrainCore:
    def __init__(self):
        self.game_size = 100
        self.heartbeat = 0.5
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
        self.moveable = False
        self.map = {}
        self.loop = 0
        self.id = None
        self.last_direction = None
        self.location = None, None
        self.perdiction_location = None, None
        self.objAttributes = None
        self.step = 0
        self.higher_move = ["aaaa"]

    def getNextMessage(self, translator, buffer):
        complete, mData = translator.HasMessage(buffer)
        if not complete:
            return None, buffer
        mt, m, headers, hOff, bLen = mData
        body, buffer = buffer[hOff:hOff + bLen], buffer[hOff + bLen:]
        msg = translator.unmarshallFromNetwork(mt, m, headers, body)
        return msg, buffer

    def sendMove(self, direction):
        # self.last_direction = direction
        if direction in self.DIRECTIONS_SHORT:
            direction = self.DIRECTIONS_SHORT[direction]
        cmdObj = translations.MoveCommand(direction)
        sendData = self.translator.marshallToNetwork(cmdObj)
        os.write(self.gameSocket.fileno(), sendData)

    def getDirection(self):
        if len(self.higher_move) > 1:
            direction = self.higher_move[1]
            del self.higher_move[1]
            return direction
        if "s" in self.last_direction:
            if self.location[1] == 0:
                self.moveable = False
        elif "n" in self.last_direction:
            if self.location[1] == self.game_size - 1:
                self.moveable = False
        elif "w" in self.last_direction:
            if self.location[0] == 0:
                self.moveable = False
        elif "e" in self.last_direction:
            if self.location[0] == self.game_size - 1:
                self.moveable = False
        return self.last_direction

    def autoExplore(self):
        direction = self.getDirection()
        self.step += 1
        self.sendMove(direction)

    def autoScan(self):
        os.write(self.gameSocket.fileno(), self.translator.marshallToNetwork(translations.ScanCommand()))

    def stateCheck(self):
        if self.moveable:
            if self.step == 5:
                self.step += 1
                self.autoScan()
            if self.step < 5:
                self.autoExplore()

    def detectEnemy(self, coord, d):
        if coord[0] == self.location[0]:
            self.higher_move.append("w")

    def handleGameMsg(self, msg):
        if isinstance(msg, translations.ScanResponse):
            for coord, objDataList in msg.scanResults:
                self.map[coord] = objDataList
                for objData in objDataList:
                    d = dict(objData)
                    if d["type"] == "object":
                        if d["identifier"] == self.id:
                            self.location = coord
                        else:
                            self.detectEnemy(coord, d)
            self.step = 0

        try:
            os.write(self.ccSocket.fileno(), self.translator.marshallToNetwork(msg))
        except Exception as e:
            self.ccSocket = None
            print("lost connection", e)

    def handleCCMsg(self, ccmsg):
        if isinstance(ccmsg, translations.AutoExploreCommand):
            self.last_direction = ccmsg.direction
            self.moveable = True
            respond = self.translator.marshallToNetwork(translations.AutoExploreReceivedResponse("success"))
            os.write(self.ccSocket.fileno(), respond)
        elif isinstance(ccmsg, translations.StayCommand):
            self.moveable = False
            respond = self.translator.marshallToNetwork(translations.StayReceivedResponse("success"))
            os.write(self.ccSocket.fileno(), respond)
        elif isinstance(ccmsg, translations.GetMapCommand):
            respond = self.translator.marshallToNetwork(translations.MapInfoResponse(self.map))
            os.write(self.ccSocket.fileno(), respond)
        else:
            os.write(self.gameSocket.fileno(), self.translator.marshallToNetwork(ccmsg))

    def brainLoop(self):
        hb = None
        gameDataStream = b""
        ccDataStream = b""
        # os.write(self.ccSocket.fileno(), self.translator.marshallToNetwork(translations.StatusCommand()))
        while True:
            self.loop += 1
            gameData = os.read(self.gameSocket.fileno(), 1024)  # max of 1024
            gameDataStream += gameData
            msg = None
            if gameDataStream:
                msg, gameDataStream = self.getNextMessage(self.translator, gameDataStream)
                if isinstance(msg, translations.BrainConnectResponse):
                    self.translator = translations.NetworkTranslator(*msg.attributes)
                    self.id = msg.identifier
                    self.objAttributes = msg.attributes
                    hb = msg
            if (not gameData) and hb and (self.loop % 30 == 0) and self.ccSocket:
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

            if msg and self.ccSocket:
                self.handleGameMsg(msg)
            ccDataStream += ccData
            ccmsg = None
            if ccDataStream:
                ccmsg, ccDataStream = self.getNextMessage(self.translator, ccDataStream)
            if ccmsg:
                self.handleCCMsg(ccmsg)

            self.stateCheck()
            time.sleep(self.heartbeat)

            if not gameData and not gameDataStream and not ccData:
                time.sleep(self.heartbeat)  # sleep half a second every time there's no data

            if not self.ccSocket and self.loop % 60 == 0:
                # if the gamesock didn't open or is dead, try to reconnect
                # once per minute
                try:
                    self.ccSocket = open(ccSocketName, "rb+")
                except:
                    self.ccSocket = None
            self.loop %= 60


if __name__ == "__main__":
    try:
        b = BrainCore()
        b.brainLoop()
    except Exception as e:
        print("Brain failed because {}".format(e))

        f = open("/tmp/error.txt", "wb+")
        f.write(str(e).encode())
        f.close()

