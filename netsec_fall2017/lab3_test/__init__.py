from ..lab3_protocol.lab2_protocol.src.lab2_protocol.PEEPClientProtocol import PEEPClientProtocol
from ..lab3_protocol.lab2_protocol.src.lab2_protocol.PEEPServerProtocol import PEEPServerProtocol

from ..lab3_protocol.src.lab3_protocol.PLSClientProtocol import PLSClientProtocol
from ..lab3_protocol.src.lab3_protocol.PLSServerProtocol import PLSServerProtocol

from . import VerificationCodeClientProtocol
from . import VerificationCodeServerProtocol

from playground.network.common import StackingProtocolFactory
import playground

# you can turn off the logging of PEEP layer here for a clean logging
# cf = StackingProtocolFactory(lambda: PLSClientProtocol(), lambda: PEEPClientProtocol(logging = False))
# sf = StackingProtocolFactory(lambda: PLSServerProtocol(), lambda: PEEPServerProtocol(logging = False))
'''
cf = StackingProtocolFactory(lambda: PLSClientProtocol(), lambda: PEEPClientProtocol())
sf = StackingProtocolFactory(lambda: PLSServerProtocol(), lambda: PEEPServerProtocol())

lab3_connector = playground.Connector(protocolStack=(cf, sf))
playground.setConnector('lab3_protocol', lab3_connector)
'''
