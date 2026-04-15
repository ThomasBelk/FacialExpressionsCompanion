import asyncio
import websockets
import json
import time

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
import file_utils as fu
from enum import Enum, auto

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
    def __init__(self, token=None, uri=DEFAULT_WEBSOCKET_URI, parent=None):
        super().__init__(parent)
        self.running = True
        self.state = PluginStatus.STARTUP
        self.uri = uri
        self.token = token

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

        if self.token is None:
            self.state = PluginStatus.GET_AUTH_TOKEN
        else:
            self.state = PluginStatus.AWAIT_PERMISSIONS

    async def getAuthToken(self, wb):
        print("Requesting auth token...")

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
            self.token = response["data"]["authenticationToken"]
            self.state = PluginStatus.AWAIT_PERMISSIONS
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
                "authenticationToken": self.token
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

        async def send_loop():
            while self.running:
                try:
                    await wb.send(json.dumps({
                        "apiName": "VTubeStudioPublicAPI",
                        "apiVersion": "1.0",
                        "requestID": f"params-{time.time()}",
                        "messageType": "InputParameterListRequest",
                    }))

                    await asyncio.sleep(1 / 30)  # ~30 FPS

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
                        params = response["data"].get("defaultParameters", {})
                        print(params)

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
    def __init__(self, url:str):
        super().__init__()
        self.url = url

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


if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    thread = VTubeStudioDataHandler()
    thread.start()

    sys.exit(app.exec())