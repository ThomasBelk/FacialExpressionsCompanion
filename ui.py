from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QLineEdit, QPushButton,
    QHBoxLayout, QLabel, QSizePolicy, QComboBox, QScrollArea, QVBoxLayout, QDialog, QCheckBox
)
from PySide6.QtCore import Signal, QTimer, Qt
from pygrabber.dshow_graph import FilterGraph
from blendshapes import DESIRED_PARAMETERS
from vtube_studio_plugin import VTubeStudioSettingsData
import file_utils as fu


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

    def __init__(self, text_on="Show", text_off="Hide", initial_state=False, max_width=60, min_width=40, tooltip_on="", tooltip_off="", parent=None):
        super().__init__(text_on, parent)
        self.text_on = text_on
        self.text_off = text_off
        self.tooltip_on = tooltip_on
        self.tooltip_off = tooltip_off
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
            self.setToolTip(self.tooltip_off)
        else:
            self.setText(self.text_on)
            self.setToolTip(self.tooltip_on)
        self.toggledState.emit(self.isChecked())

    def mySetChecked(self, state):
        self.setChecked(state)
        if state:
            self.setText(self.text_off)
            self.setToolTip(self.tooltip_off)
        else:
            self.setText(self.text_on)
            self.setToolTip(self.tooltip_on)


class MappingWidget(QWidget):
    mappingChanged = Signal(str, str, bool)
    def __init__(self, selectedVTSParam=None, mapToParam=None, inverted=False, parent=None):
        super().__init__(parent)
        self.vtsParams = []

        self.selectedVTSParam = selectedVTSParam
        self.mapToParam = mapToParam
        self.invertCheckbox = QCheckBox("Invert Parameter")
        self.invertCheckbox.setChecked(inverted)

        self.selectedVTSParamDropDown=NoHoverScrollComboBox()
        self.selectedVTSParamDropDown.setFixedWidth(175)
        self.selectedVTSParamDropDown.addItem("None")
        self.mapToParamLabel = QLabel(self.mapToParam)
        layout = QHBoxLayout()
        layout.addWidget(self.mapToParamLabel)
        layout.addWidget(self.selectedVTSParamDropDown)
        layout.addWidget(self.invertCheckbox)
        self.setLayout(layout)
        self.setFixedWidth(425)

    # this will run after we get parameters from vtube studio
    def lateSetup(self, vtsParams):
        self.vtsParams = vtsParams
        self.selectedVTSParamDropDown.blockSignals(True)

        self.selectedVTSParamDropDown.clear()
        self.selectedVTSParamDropDown.addItem("None")
        self.selectedVTSParamDropDown.addItems(self.vtsParams)

        index = self.selectedVTSParamDropDown.findText(self.selectedVTSParam)
        if index != -1:
            self.selectedVTSParamDropDown.setCurrentIndex(index)
        else:
            self.selectedVTSParamDropDown.setCurrentIndex(0)

        self.selectedVTSParamDropDown.blockSignals(False)

        # by connecting it should not be reset to none by onChanged
        self.selectedVTSParamDropDown.currentTextChanged.connect(self.onChanged)
        self.invertCheckbox.toggled.connect(self.onChanged)

    def onChanged(self, *args):
        self.selectedVTSParam = self.selectedVTSParamDropDown.currentText()
        self.mappingChanged.emit(self.mapToParam, self.selectedVTSParam, self.invertCheckbox.isChecked())


class VTubeStudioSettingWidget(QWidget):
    def __init__(self, settings_mappings:VTubeStudioSettingsData, parent=None):
        super().__init__(parent)
        self.settingsMappings = settings_mappings
        self.vParamList = []

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        mainLayout = QVBoxLayout(self)

        label = QLabel("VTube Studio Mappings")
        label.setAlignment(Qt.AlignCenter)
        font = label.font()
        font.setPointSize(16)
        label.setFont(font)

        mainLayout.addWidget(label)

        mainLayout.addWidget(self.scroll)

        self.container = QWidget()
        self.scroll.setWidget(self.container)

        self.hbox = QHBoxLayout(self.container)
        self.hbox.setSpacing(20)

        self.widgets = []
        for i in DESIRED_PARAMETERS:
            w = MappingWidget(self.settingsMappings.getValue(i, "None"), i, self.settingsMappings.isInverted(i))
            if len(self.vParamList) > 0:
                w.lateSetup(self.vParamList)
            w.mappingChanged.connect(self.updateMapping)
            self.widgets.append(w)

        self.current_columns = 0
        QTimer.singleShot(0, self.rebuild_layout)

    def updateVTubeStudioParamOptions(self, paramsList):
        print("Called with list", paramsList)
        if len(self.vParamList) != len(paramsList):
            self.vParamList = paramsList
            for w in self.widgets:
                if isinstance(w, MappingWidget):
                    w.lateSetup(paramsList)

    def updateMapping(self, key, value, invertedFlag):
        self.settingsMappings.updateMapping(key, value, invertedFlag)

    def get_column_count(self, width):
        # this feels a bit dumb magic numbers and all, and max 4 columns? but I also don't know if I don't think 5 columns is readable
        # never thought I would miss CSS. On second thought idk man. CSS makes me sad
        if width < 900:
            return 1
        elif width < 1400:
            return 2
        elif width < 1850:
            return 3
        else:
            return 4

    def rebuild_layout(self):
        width = self.scroll.viewport().width()
        cols = self.get_column_count(width)

        if cols == self.current_columns:
            return

        self.current_columns = cols

        while self.hbox.count():
            item = self.hbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        columns = [QVBoxLayout() for _ in range(cols)]

        for i, widget in enumerate(self.widgets):
            columns[i % cols].addWidget(widget)

        for col in columns:
            col.addStretch()
            colWidget = QWidget()
            colWidget.setLayout(col)
            self.hbox.addWidget(colWidget)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.rebuild_layout()

    def showEvent(self, event):
        super().showEvent(event)
        self.rebuild_layout()

# this is just so that you don't accidentally change the combo box option when trying to scroll
class NoHoverScrollComboBox(QComboBox):
    def wheelEvent(self, event):
        event.ignore()


class CameraSelector(NoHoverScrollComboBox):
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

    def setCameraIndex(self, index:int):
        self.setCurrentIndex(index)

    def _onIndexChanged(self, index):
        self.cameraChanged.emit(
            self.currentCameraIndex(),
            self.currentCameraName()
        )


class SimpleDialog(QDialog):
    def __init__(self, title:str, bodyText:str, width=400, height=120, useTimer=False, useLeftButton=False, useRightButton=True, leftButtonText="Accept", rightButtonText="Cancel", selector=None, parent=None):
        super().__init__()
        self.bodyText = bodyText
        self.useLeftButton = useLeftButton
        self.useRightButton = useRightButton
        self.leftButtonText = leftButtonText
        self.rightButtonText = rightButtonText
        self.timer = QTimer()
        self.timerWord = "Closing"
        self.timer.timeout.connect(self.updateCountdown)
        self.timerLabel = QLabel()
        self.timerLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.countdown_seconds = None

        self.setWindowTitle(title)
        self.setFixedSize(width, height)
        icon_path = fu.resource_path("icons/rtfelogo.png")
        self.setWindowIcon(QIcon(str(icon_path)))

        self.label = QLabel(self.bodyText)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.leftButton = QPushButton(self.leftButtonText)
        self.rightButton = QPushButton(self.rightButtonText)
        self.leftButton.clicked.connect(self.handleLeftButton)
        self.rightButton.clicked.connect(self.handleRightButton)

        self.toggleButtonVisibility(self.leftButton, self.useLeftButton)
        self.toggleButtonVisibility(self.rightButton, self.useRightButton)


        layout = QVBoxLayout()
        horizontal_layout = QHBoxLayout()
        layout.addWidget(self.label, 1)
        if selector:
            layout.addWidget(selector)
        if useTimer:
            layout.addWidget(self.timerLabel)
        horizontal_layout.addWidget(self.leftButton)
        horizontal_layout.addWidget(self.rightButton)
        layout.addLayout(horizontal_layout, 0)

        self.setLayout(layout)

    def startCountdown(self, seconds: int, word="Closing"):
        self.countdown_seconds = seconds
        self.timerWord = word
        self.updateCountdown()
        self.timer.start(1000)

    def updateCountdown(self):
        if self.countdown_seconds is None:
            return

        print(self.countdown_seconds)
        self.timerLabel.setText(f"{self.timerWord} in {self.countdown_seconds} seconds...")

        if self.countdown_seconds <= 0:
            self.timer.stop()
            return

        self.countdown_seconds -= 1

    def setBodyText(self, bodyText:str):
        self.bodyText = bodyText
        self.label.setText(self.bodyText)

    def getBodyText(self):
        return self.bodyText

    def handleRightButton(self):
        self.accept()

    def toggleButtonVisibility(self, button:QPushButton, active):
        if active:
            button.setEnabled(True)
            button.setHidden(False)
        else:
            button.setEnabled(False)
            button.setHidden(True)

    def handleLeftButton(self):
        # does python allow passing lambdas as function arguments? I think it does
        pass

    def closeEvent(self, event):
        if self.timer.isActive():
            self.timer.stop()
        super().closeEvent(event)
