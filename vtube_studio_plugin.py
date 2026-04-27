import asyncio
import websockets
import json
import time

from PySide6.QtCore import Qt, QThread, Signal, QSettings
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
import file_utils as fu
from enum import Enum, auto

from blendshapes import DESIRED_PARAMETERS

PLUGIN_NAME = "Real Facial Expressions (Hytale Expression Tracking Plugin)"
PLUGIN_AUTHOR = "Thomas Belk"
DEFAULT_WEBSOCKET_URI = "ws://localhost:8001"

class PluginStatus(Enum):
    STARTUP = auto()
    GET_AUTH_TOKEN = auto()
    AWAIT_PERMISSIONS = auto()
    SEND_AND_RECEIVE_DATA = auto()
    PERMISSIONS_ERROR = auto()


class VTubeStudioDataHandler(QThread):
    studio_tracking_ready = Signal(object)
    parameter_list_ready = Signal(list)
    accept_auth_notification = Signal(bool)
    vts_error = Signal(str, bool)

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
        self.authFailCount = 0

        self.send_task = None
        self.recv_task = None

    def setRate(self, rate):
        self.rate = rate
        self.interval = 1 / self.rate

    def run(self):
        asyncio.run(self.mainLoop())

    async def mainLoop(self):
        while self.running:
            result = await self.main()

            if not self.running:
                self.vts_error.emit("", False)
                break

            if result == -1:
                self.state = PluginStatus.STARTUP
                await asyncio.sleep(5)
                self.vts_error.emit("", False)

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
                            result = await self.run_data_loops(wb)
                            return result

                        case PluginStatus.PERMISSIONS_ERROR:
                            m = "Error receiving permissions from VTube Studio. Likely because you denied permissions to the plugin in VTube Studio."
                            self.vts_error.emit(m, True)
                            return -1

        except Exception as e:
            m = "Error connecting to VTube Studio, make sure VTubeStudio is open and plugins are enabled. Error message: " + str(e)
            self.vts_error.emit(m, True)
            return -1

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

        self.accept_auth_notification.emit(True)

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
        self.accept_auth_notification.emit(False)

        try:
            self.vSettings.setToken(response["data"]["authenticationToken"])
            self.state = PluginStatus.AWAIT_PERMISSIONS
        except KeyError as e:
            m = "Error getting auth token from VTube Studio. This could be the result of you rejecting permissions in VTube Studio. Error: " + str(e)
            self.vts_error.emit(m, True)

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
        elif self.authFailCount < 2:
            self.authFailCount += 1
            self.vSettings.setToken(None)
            self.state = PluginStatus.GET_AUTH_TOKEN
        else:
            self.state = PluginStatus.PERMISSIONS_ERROR

    async def run_data_loops(self, wb):
        print("Starting data loops...")

        loop_error = {"failed": False}

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

                except asyncio.CancelledError:
                    break

                except Exception as e:
                    loop_error["failed"] = True
                    self.vts_error.emit(
                        "Failed to send parameter data request to VTube Studio. Error: " + str(e),
                        True
                    )
                    break

        async def receive_loop():
            while self.running:
                try:
                    msg = await asyncio.wait_for(wb.recv(), timeout=1.0)
                    response = json.loads(msg)

                    msg_type = response.get("messageType")

                    if msg_type == "InputParameterListResponse":
                        processedData = self.converter.convert(response["data"])

                        if len(self.vParamList) < 1:
                            self.vParamList = self.converter.getParameterNamesAsList(response["data"])
                            self.parameter_list_ready.emit(self.vParamList)
                        else:
                            self.studio_tracking_ready.emit(processedData)

                    elif msg_type == "APIError":
                        loop_error["failed"] = True
                        self.vts_error.emit("VTubeStudio API error received.", True)
                        break

                except asyncio.TimeoutError:
                    if not self.running:
                        break
                    continue

                except asyncio.CancelledError:
                    break

                except Exception as e:
                    loop_error["failed"] = True
                    self.vts_error.emit(
                        "Failed to receive parameter data from VTube Studio. Error: " + str(e),
                        True
                    )
                    break

        self.send_task = asyncio.create_task(send_loop())
        self.recv_task = asyncio.create_task(receive_loop())

        await asyncio.gather(
            self.send_task,
            self.recv_task
        )

        if loop_error["failed"]:
            return -1

        return 0

    def stop(self):
        self.running = False
        if self.send_task:
            self.send_task.cancel()
        if self.recv_task:
            self.recv_task.cancel()
        self.quit()
        self.wait()

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

        self.mappings = {i: {"value": None, "inverted": False} for i in DESIRED_PARAMETERS}
        raw = self.settings.value("VTubeStudioMappings", "{}")

        if raw is None:
            raw = "{}"

        try:
            loaded = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            loaded = {}

        for k, v in loaded.items():
            self.mappings[k] = {
                "value": v.get("value"),
                "inverted": v.get("inverted", False)
            }


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
        self.settings.setValue("VTubeStudioToken", self.token)

    def updateMapping(self, key, value=None, inverted=None):
        current = self.mappings.get(key, {"value": None, "inverted": False})

        if value is not None:
            current["value"] = value
        if inverted is not None:
            current["inverted"] = inverted

        self.mappings[key] = current
        self.saveMappings()

    def getValue(self, key, default=None):
        return self.mappings.get(key, {}).get("value", default)

    def isInverted(self, key):
        return self.mappings.get(key, {}).get("inverted", False)


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

    def invertParam(self, value: float):
        return 1 - value

    def convert(self, data):
        ret = {}
        param_map = {
            p["name"]: p
            for group in ("customParameters", "defaultParameters")
            for p in data.get(group, [])
        }
        for i in DESIRED_PARAMETERS:
            vParamName = self.mappings.getValue(i)
            if vParamName is None:
                continue
            vParam = param_map.get(vParamName)

            if vParam is not None:
                ret[i] = self.normalizeParam(vParam["value"], vParam["min"], vParam["max"])
                if self.mappings.isInverted(i):
                    ret[i] = self.invertParam(ret[i])

        return ret


if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    settings = QSettings("ThetaBork", "FacialExpressionsCompanion")
    thread = VTubeStudioDataHandler(settings)
    thread.start()

    sys.exit(app.exec())