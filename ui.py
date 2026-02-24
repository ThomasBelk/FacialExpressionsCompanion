from PySide6.QtWidgets import (
    QWidget, QLineEdit, QPushButton,
    QHBoxLayout, QLabel, QSizePolicy, QComboBox
)
from PySide6.QtCore import Signal
from pygrabber.dshow_graph import FilterGraph


class FormField(QWidget):
    def __init__(self, title, placeholder, /, parent=None):
        super().__init__(parent)
        self.lineEdit = QLineEdit()
        self.lineEdit.setPlaceholderText(placeholder)
        self.lineEdit.setEchoMode(QLineEdit.EchoMode.Password)

        self.toggle_btn = QPushButton("Show")
        self.toggle_btn.setCheckable(True)  # Can stay pressed
        self.toggle_btn.setMaximumWidth(60)
        self.toggle_btn.clicked.connect(self.toggle_show)

        label = QLabel(title)

        label.setSizePolicy(label.sizePolicy().horizontalPolicy(), QSizePolicy.Policy.Fixed)
        self.lineEdit.setSizePolicy(self.lineEdit.sizePolicy().horizontalPolicy(), QSizePolicy.Policy.Fixed)
        self.toggle_btn.setSizePolicy(self.toggle_btn.sizePolicy().horizontalPolicy(), QSizePolicy.Policy.Fixed)

        h_layout = QHBoxLayout()
        h_layout.addWidget(label)
        h_layout.addWidget(self.lineEdit)
        h_layout.addWidget(self.toggle_btn)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(8)

        self.setLayout(h_layout)

    def toggle_show(self):
        if self.toggle_btn.isChecked():
            self.lineEdit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_btn.setText("Hide")
        else:
            self.lineEdit.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_btn.setText("Show")

    def setValidator(self, validator):
        self.lineEdit.setValidator(validator)

    def setText(self, text):
        self.lineEdit.setText(text)

    def getText(self):
        return self.lineEdit.text()

    def connectEditEvent(self, func):
        self.lineEdit.textEdited.connect(func)

class ToggleButton(QPushButton):
    toggledState = Signal(bool)

    def __init__(self, text_on="Show", text_off="Hide", initial_state=False, max_width=60, min_width=40, parent=None):
        super().__init__(text_on, parent)
        self.text_on = text_on
        self.text_off = text_off
        self.setCheckable(True)
        self.setMinimumWidth(min_width)
        self.setMaximumWidth(max_width)
        self.setChecked(initial_state)
        self._on_clicked()
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), QSizePolicy.Policy.Fixed)
        self.clicked.connect(self._on_clicked)

    def _on_clicked(self):
        if self.isChecked():
            self.setText(self.text_off)
        else:
            self.setText(self.text_on)
        self.toggledState.emit(self.isChecked())


class CameraSelector(QComboBox):
    cameraChanged = Signal(int, str)  # index, name

    def __init__(self, parent=None):
        super().__init__(parent)

        self.devices = self.findCameras()
        self.populateCameras()

        self.currentIndexChanged.connect(self._onIndexChanged)

    def findCameras(self):
        graph = FilterGraph()
        return graph.get_input_devices()  # List[str]

    def populateCameras(self):
        self.clear()

        for index, device in enumerate(self.devices):
            self.addItem(device, index)

    def currentCameraIndex(self) -> int:
        return self.currentData()

    def currentCameraName(self) -> str:
        return self.currentText()

    def findIndexFromName(self, name) -> int:
        if name is None:
            return 0
        for index, device in enumerate(self.devices):
            if device == name:
                return index
        return 0 # the default it to try what would be the first camera

    def setCameraIndex(self, index):
        self.setCurrentIndex(index)

    def _onIndexChanged(self, index):
        self.cameraChanged.emit(
            self.currentCameraIndex(),
            self.currentCameraName()
        )