import asyncio
import websockets
import json
import time

from PySide6.QtCore import Qt, QThread, Signal, QSettings
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
import file_utils as fu
from enum import Enum, auto

from blendshapes import DESIRED_BLENDSHAPES

PLUGIN_NAME = "Real Facial Expressions (Hytale Expression Tracking Plugin)"
PLUGIN_AUTHOR = "Thomas Belk"
DEFAULT_WEBSOCKET_URI = "ws://localhost:8001"

class PluginStatus(Enum):
    STARTUP = auto()
    GET_AUTH_TOKEN = auto()
    AWAIT_PERMISSIONS = auto()
    SEND_AND_RECEIVE_DATA = auto()
    PERMISSIONS_ERROR = auto()
    ERROR = auto()


class VTubeStudioDataHandler(QThread):
    studio_tracking_ready = Signal(object)
    parameter_list_ready = Signal(list)

    def __init__(self, settings, uri=DEFAULT_WEBSOCKET_URI, parent=None):
        super().__init__(parent)
        self.running = True
        self.state = PluginStatus.STARTUP
        self.uri = uri
        self.rate = 30
        self.interval = 1 / self.rate
        self.vSettings = settings
        self.converter = VTubeStudioParameterConverter(self.vSettings)
        self.vParamList = []

    def run(self):
        asyncio.run(self.main())

    async def main(self):
        try:
            async with websockets.connect(self.uri) as wb:
                print("Connected to VTube Studio")

                while self.running:
                    match self.state:

                        case PluginStatus.STARTUP:
                            await self.initialConnection(wb)

                        case PluginStatus.GET_AUTH_TOKEN:
                            await self.getAuthToken(wb)

                        case PluginStatus.AWAIT_PERMISSIONS:
                            await self.authRequest(wb)

                        case PluginStatus.SEND_AND_RECEIVE_DATA:
                            await self.run_data_loops(wb)
                            return  # exit after loops stop

                        case PluginStatus.PERMISSIONS_ERROR:
                            print("Permission error")
                            return

                        case PluginStatus.ERROR:
                            print("General error")
                            return

        except Exception as e:
            print("Connection error:", e)

    async def initialConnection(self, wb):
        print("Requesting API state...")

        await wb.send(json.dumps({
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": "state",
            "messageType": "APIStateRequest"
        }))

        response = json.loads(await wb.recv())
        print("API State Response:", response)

        if self.vSettings.getToken() is None:
            self.state = PluginStatus.GET_AUTH_TOKEN
        else:
            self.state = PluginStatus.AWAIT_PERMISSIONS

    async def getAuthToken(self, wb):
        print("Requesting auth token...")

        ## open popup
        # window = VTubeStudioPluginAuthWindow()
        # window.show()

        await wb.send(json.dumps({
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": "token",
            "messageType": "AuthenticationTokenRequest",
            "data": {
                "pluginName": PLUGIN_NAME,
                "pluginDeveloper": PLUGIN_AUTHOR
            }
        }))

        response = json.loads(await wb.recv())
        print("Token Response:", response)

        try:
            self.vSettings.setToken(response["data"]["authenticationToken"])
            self.state = PluginStatus.AWAIT_PERMISSIONS
            ## close window cause we received the token
            # window.accept()
        except KeyError:
            self.state = PluginStatus.ERROR

    async def authRequest(self, wb):
        print("Sending auth request...")

        await wb.send(json.dumps({
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": "auth",
            "messageType": "AuthenticationRequest",
            "data": {
                "pluginName": PLUGIN_NAME,
                "pluginDeveloper": PLUGIN_AUTHOR,
                "authenticationToken": self.vSettings.getToken()
            }
        }))

        response = json.loads(await wb.recv())
        print("Auth Response:", response)

        if response.get("data", {}).get("authenticated", False):
            print("Authenticated!")
            self.state = PluginStatus.SEND_AND_RECEIVE_DATA
        else:
            self.state = PluginStatus.PERMISSIONS_ERROR

    async def run_data_loops(self, wb):
        print("Starting data loops...")

        await wb.send(json.dumps({
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": "RequestParamCreation",
            "messageType": "ParameterCreationRequest",
            "data": {
                "parameterName": "MyParam",
                "explanation": "This is my new parameter.",
                "min": -50,
                "max": 50,
                "defaultValue": 10
            }
        }))

        response = json.loads(await wb.recv())
        print(response)
        # sys.exit(0)

        async def send_loop():
            while self.running:
                try:
                    start = time.perf_counter()
                    await wb.send(json.dumps({
                        "apiName": "VTubeStudioPublicAPI",
                        "apiVersion": "1.0",
                        "requestID": f"params-{time.time()}",
                        "messageType": "InputParameterListRequest",
                    }))

                    elapsed = time.perf_counter() - start
                    await asyncio.sleep(max(0.0, self.interval - elapsed))

                except Exception as e:
                    print("Send error:", e)
                    self.state = PluginStatus.ERROR
                    break

        async def receive_loop():
            while self.running:
                try:
                    msg = await wb.recv()
                    response = json.loads(msg)

                    msg_type = response.get("messageType")

                    if msg_type == "InputParameterListResponse":
                        processedData = self.converter.convert(response["data"])
                        if len(self.vParamList) < 1:
                            self.vParamList = self.converter.getParameterNamesAsList(response["data"])
                            self.parameter_list_ready.emit(self.vParamList)
                            print("emitting list")
                        print(processedData)

                    else:
                        print(msg_type)
                        pass

                except Exception as e:
                    print("Receive error:", e)
                    self.state = PluginStatus.ERROR
                    break

        await asyncio.gather(send_loop(), receive_loop())

    def stop(self):
        self.running = False

class VTubeStudioPluginAuthWindow(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("VTube Studio Permissions Request")
        self.setFixedSize(300, 120)
        icon_path = fu.resource_path("icons/rtfelogo.png")
        self.setWindowIcon(QIcon(str(icon_path)))

        label = QLabel("To proceed please accept permissions in VTube Studio. This window will disappear when authentication is completed.")
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.handleCancelButton)

        layout = QVBoxLayout()
        horizontal_layout = QHBoxLayout()
        layout.addWidget(label)
        horizontal_layout.addWidget(cancel_button)
        layout.addLayout(horizontal_layout)

        self.setLayout(layout)

    def handleCancelButton(self):
        self.accept()

class VTubeStudioSettingsData:
    def __init__(self, settings: QSettings):
        self.settings = settings
        self.token = settings.value("VTubeStudioToken", None)

        self.mappings = {i: None for i in DESIRED_BLENDSHAPES}
        raw = self.settings.value("VTubeStudioMappings", "{}")

        # redundant but pycharm is complaining
        if raw is None:
            raw = "{}"

        try:
            loaded = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            loaded = {}

        self.mappings.update(loaded)
        print(self.mappings)

    def saveMappings(self):
        self.settings.setValue(
            "VTubeStudioMappings",
            json.dumps(self.mappings)
        )

    def setToken(self, token: str):
        self.token = token
        self.saveToken()

    def getToken(self):
        return self.token

    def saveToken(self):
        self.settings.setValue(
            "VTubeStudioToken", self.token
        )

    def updateMapping(self, key, value):
        self.mappings[key] = value
        # I'm not super sure about this, but it does make it more resilient to crashes
        self.saveMappings()

    def getValue(self, key, default=None):
        # print(key)
        return self.mappings.get(key, default)


class VTubeStudioParameterConverter:
    def __init__(self, mappings: VTubeStudioSettingsData):
        self.mappings = mappings

    def normalizeParam(self, value: float, min_val: float, max_val: float) -> float:
        if max_val == min_val:
            return 0.0
        normalized = (value - min_val) / (max_val - min_val)
        return max(0.0, min(1.0, normalized))

    def getParameterNamesAsList(self, data):
        return [
            p["name"]
            for group in ("customParameters", "defaultParameters")
            for p in data.get(group, [])
        ]

    def convert(self, data):
        ret = {}
        param_map = {
            p["name"]: p
            for group in ("customParameters", "defaultParameters")
            for p in data.get(group, [])
        }
        for i in DESIRED_BLENDSHAPES:
            vParamName = self.mappings.getValue(i)
            if i is None:
                continue
            vParam = param_map.get(vParamName)

            if vParam is not None:
                ret[i] = self.normalizeParam(vParam["value"], vParam["min"], vParam["max"])

        return ret


if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    settings = QSettings("ThetaBork", "FacialExpressionsCompanion")
    thread = VTubeStudioDataHandler(settings)
    thread.start()

    sys.exit(app.exec())