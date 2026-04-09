#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Smartphone handheld mock features and Hardware Abstraction Layer."""

# Standard packages
import sys

# Installed packages
from PySide6.QtCore import QStandardPaths, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QLineEdit

# Local-like modules
## TEMP (force tracing):
## os.environ.setdefault("DEBUG_LEVEL", "5")
from mezcla import debug, system

# Local modules
from feature_stubs import _title, _hint, _sep, BaseMenuWidget

# ===========================================================================
# Hardware Abstraction Layer (HAL)
# ===========================================================================
class HardwareFacade:
    """Base class for hardware interaction."""
    def authenticate_biometric(self):
        """Mock biometric authentication."""
        return False
    def vibrate(self, duration_ms):
        """Mock device vibration for the specified duration."""
    def notify(self, title, message):
        """Mock system notification."""
    def share_text(self, text):
        """Mock text sharing intent."""
    def get_gps(self, callback):
        """Mock GPS location retrieval."""

class DesktopHardware(HardwareFacade):
    """Hardware implementation for desktop environments."""
    def __init__(self):
        super().__init__()
        self._source = None
        self._callback = None

    def authenticate_biometric(self):
        """Simulate biometric authentication on desktop."""
        print("Desktop: Simulated Auth Success")
        return True
    def vibrate(self, duration_ms):
        """Simulate device vibration on desktop."""
        print(f"Desktop: Simulated vibration for {duration_ms}ms")
    def notify(self, title, message):
        """Display a desktop notification."""
        print(f"Desktop Notification: {title} - {message}")
    def share_text(self, text):
        """Simulate sharing text from desktop."""
        print(f"Desktop Share: {text}")
    def get_gps(self, callback):
        """Retrieve GPS coordinates using QtPositioning or a fallback."""
        try:
            # pylint: disable=import-outside-toplevel,import-error,unused-import
            from PySide6.QtPositioning import QGeoPositionInfoSource
            self._source = QGeoPositionInfoSource.createDefaultSource(None)
            if self._source:
                self._callback = callback
                self._source.positionUpdated.connect(self._on_position_updated)
                self._source.startUpdates()
            else:
                callback(lat=37.7749, lon=-122.4194)
        except ImportError:
            system.print_exception_info("QWebEngineView import")
            callback(lat=37.7749, lon=-122.4194)

    def _on_position_updated(self, info):
        """Handle position updates from the system geo source."""
        if info.isValid():
            coord = info.coordinate()
            self._callback(lat=coord.latitude(), lon=coord.longitude())
        else:
            self._callback(lat=37.7749, lon=-122.4194)

class AndroidHardware(HardwareFacade):
    """Hardware implementation for Android devices."""
    def authenticate_biometric(self):
        """Authenticate using Android biometric APIs."""
        try:
            from jnius import autoclass  # pylint: disable=import-outside-toplevel,import-error,unused-import
            return True
        except ImportError:
            return False
            
    def vibrate(self, duration_ms):
        """Vibrate the Android device."""
        try:
            from plyer import vibrator  # pylint: disable=import-outside-toplevel,import-error
            vibrator.vibrate(time=duration_ms/1000.0)
        except Exception as exc:
            debug.trace_exception_info(5, f"AndroidHardware.vibrate: {exc}")
            
    def notify(self, title, message):
        """Post an Android system notification."""
        try:
            from plyer import notification  # pylint: disable=import-outside-toplevel,import-error
            notification.notify(title=title, message=message)
        except Exception as exc:
            debug.trace_exception_info(5, f"AndroidHardware.notify: {exc}")
            
    def share_text(self, text):
        """Trigger the Android system share sheet via intents."""
        try:
            from jnius import autoclass  # pylint: disable=import-outside-toplevel,import-error
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            String = autoclass('java.lang.String')
            intent = Intent()
            intent.setAction(Intent.ACTION_SEND)
            intent.putExtra(Intent.EXTRA_TEXT, String(text))
            intent.setType("text/plain")
            chooser = Intent.createChooser(intent, String("Share via"))
            PythonActivity.mActivity.startActivity(chooser)
        except Exception as exc:
            debug.trace_exception_info(5, f"AndroidHardware.share_text: {exc}")
            
    def get_gps(self, callback):
        """Start Android GPS updates via Plyer."""
        try:
            from plyer import gps  # pylint: disable=import-outside-toplevel,import-error
            gps.configure(on_location=callback)
            gps.start()
        except Exception as exc:
            debug.trace_exception_info(5, f"AndroidHardware.get_gps: {exc}")

class IOSHardware(HardwareFacade):
    """Hardware implementation for iOS devices."""
    def authenticate_biometric(self):
        """Authenticate using iOS biometric APIs (stub)."""
        print("iOS Auth: To be implemented")
        return False
    def vibrate(self, duration_ms):
        """Vibrate the iOS device (stub)."""
        print(f"iOS Vibrate: To be implemented ({duration_ms}ms)")
    def notify(self, title, message):
        """Post an iOS system notification (stub)."""
        print(f"iOS Notify: To be implemented - {title}")
    def share_text(self, text):
        """Trigger the iOS share sheet (stub)."""
        print("iOS Share: To be implemented")
    def get_gps(self, callback):
        """Start iOS GPS updates (stub)."""
        print("iOS GPS: To be implemented")
        callback(lat=0.0, lon=0.0)


def get_hardware():
    """Factory to retrieve hardware based on current OS."""
    from PySide6.QtCore import QSysInfo
    os_type = QSysInfo.productType()
    debug.trace(6, f"in: get_hardware; sys.platform={sys.platform!r}, QSysInfo.productType()={os_type!r}")
    result = None
    if os_type == "android":
        result = AndroidHardware()
    elif os_type == "ios":
        result = IOSHardware()
    else:
        result = DesktopHardware()
    debug.trace(5, f"get_hardware() => {result!r}")
    return result
    

hw = get_hardware()

class BiometricAuthWidget(QWidget):
    """1. Biometric Auth - hardware API simulation or real API"""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(_title("🔐  Biometric Auth"))
        layout.addWidget(_hint("Test integration with hardware-level APIs (Fingerprint/Face Unlock)."))
        layout.addWidget(_sep())
        
        self.status = QLabel("Status: Unauthenticated")
        layout.addWidget(self.status)
        
        btn = QPushButton("Authenticate")
        btn.clicked.connect(self.authenticate)
        layout.addWidget(btn)
        layout.addStretch()

    def authenticate(self):
        """Invoke biometric authentication routine."""
        success = hw.authenticate_biometric()
        if success:
            self.status.setText("Status: Auth Success (or Android skeleton called)")
        else:
            self.status.setText("Status: Auth Failed or Skeleton only")

class VoiceCommandWidget(QWidget):
    """2. Voice Command - microphone buffer handling"""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(_title("🗣  Voice Command"))
        layout.addWidget(_hint("Implement 'Wake Word' detection or basic voice-to-text."))
        layout.addWidget(_sep())
        
        self.status = QLabel("Status: Idle")
        layout.addWidget(self.status)
        
        btn = QPushButton("Listen for Wake Word")
        btn.clicked.connect(self.listen)
        layout.addWidget(btn)
        layout.addStretch()

    def listen(self):
        """Start listening for audio wake words."""
        self.status.setText("Status: Listening... (Using PySide6 QtMultimedia / QAudioSource in real app)")
        # In a real app:
        # from PySide6.QtMultimedia import QAudioSource, QMediaFormat
        # self.audio_source = QAudioSource(QMediaFormat.AudioCodec.Wave)
        # self.io_device = self.audio_source.start()

class CameraPreviewWidget(QWidget):
    """3. Camera Preview - Display a low-latency live feed with a custom UI overlay."""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(_title("📸  Camera Preview"))
        layout.addWidget(_hint("Display a low-latency live feed. (Requires PySide6.QtMultimedia)"))
        layout.addWidget(_sep())
        
        self.status = QLabel("Camera Feed Placeholder")
        self.status.setStyleSheet("background: #000; color: #fff; min-height: 200px;")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status)
        
        btn = QPushButton("Start Camera")
        btn.clicked.connect(self.start_camera)
        layout.addWidget(btn)
        layout.addStretch()

    def start_camera(self):
        """Initialize and start simulated camera preview."""
        self.status.setText("Camera started (Simulated). Use QCamera and QVideoWidget.")
        # from PySide6.QtMultimedia import QCamera, QMediaCaptureSession
        # from PySide6.QtMultimediaWidgets import QVideoWidget
        # self.camera = QCamera()
        # self.captureSession = QMediaCaptureSession()
        # self.captureSession.setCamera(self.camera)
        # self.videoWidget = QVideoWidget()
        # self.captureSession.setVideoOutput(self.videoWidget)
        # self.camera.start()

class PushNotificationsWidget(QWidget):
    """4. Push Notifications - Trigger local alerts."""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(_title("🔔  Push Notifications"))
        layout.addWidget(_hint("Trigger local alerts appearing in the background."))
        layout.addWidget(_sep())
        
        btn = QPushButton("Send Notification")
        btn.clicked.connect(self.notify)
        layout.addWidget(btn)
        
        self.status = QLabel("")
        layout.addWidget(self.status)
        layout.addStretch()

    def notify(self):
        """Trigger a local push notification alert."""
        hw.notify("Test Alert", "This is a local push notification.")
        self.status.setText("Notification requested via HardwareFacade.")

class HapticConfirmationWidget(QWidget):
    """5. Haptic Confirmation - vibration ticks/thuds."""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(_title("📳  Haptic Confirmation"))
        layout.addWidget(_hint("Use sharp vibration 'ticks' for successful actions."))
        layout.addWidget(_sep())
        
        row = QHBoxLayout()
        btn1 = QPushButton("Success (Tick)")
        btn1.clicked.connect(lambda: self.vibrate(50))
        btn2 = QPushButton("Error (Thud)")
        btn2.clicked.connect(lambda: self.vibrate(300))
        row.addWidget(btn1)
        row.addWidget(btn2)
        layout.addLayout(row)
        
        self.status = QLabel("")
        layout.addWidget(self.status)
        layout.addStretch()

    def vibrate(self, duration_ms):
        """Trigger haptic feedback vibration."""
        hw.vibrate(duration_ms)
        self.status.setText(f"Vibration ({duration_ms}ms) requested via HardwareFacade.")

class SmoothGalleryWidget(QWidget):
    """6. Smooth Gallery - load high-res images from DCIM."""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(_title("🖼  Smooth Gallery"))
        layout.addWidget(_hint("Load local images. Typically uses QListView with QFileSystemModel or custom model."))
        layout.addWidget(_sep())
        
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        btn = QPushButton("Load DCIM / Pictures")
        btn.clicked.connect(self.load_images)
        layout.addWidget(btn)

    def load_images(self):
        """Load and display local system images."""
        self.list_widget.clear()
        paths = QStandardPaths.standardLocations(QStandardPaths.StandardLocation.PicturesLocation)
        if paths:
            self.list_widget.addItem(f"Searching in: {paths[0]}")
            # Skeleton: scan paths[0] for .jpg/.png and add QListWidgetItem with icon
        else:
            self.list_widget.addItem("No standard Pictures location found.")

class MultiTouchMapWidget(QWidget):
    """7. Multi-Touch Map - Standard Google Maps UI."""
    def __init__(self):
        # pylint: disable=import-outside-toplevel,import-error,unused-import
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(_title("🗺  Multi-Touch Map"))
        layout.addWidget(_hint("Standard Google Maps UI via embedded WebView."))
        layout.addWidget(_sep())
        
        self.map_container = QWidget()
        container_layout = QVBoxLayout(self.map_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        from PySide6.QtCore import QSysInfo
        os_type = QSysInfo.productType()
        
        if os_type == "android":
            try:
                from PySide6.QtQuickWidgets import QQuickWidget
                from PySide6.QtCore import QUrl
                self.quick_widget = QQuickWidget()
                self.quick_widget.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
                qml_code = '''
                import QtQuick
                import QtWebView
                Item {
                    WebView {
                        anchors.fill: parent
                        url: "https://www.google.com/maps"
                    }
                }
                '''
                self.quick_widget.setSource(QUrl("data:text/plain;charset=utf-8," + qml_code))
                container_layout.addWidget(self.quick_widget)
            except Exception as exc:
                debug.trace_exception_info(5, f"Android Map Error: {exc}")
                self.map_area = QLabel(f"Android Map Error:\\n{exc}")
                self.map_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
                container_layout.addWidget(self.map_area)
        elif os_type == "ios":
            self.map_area = QLabel("Map Area\\n(iOS WebView to be implemented)")
            self.map_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
            container_layout.addWidget(self.map_area)
        else:
            try:
                from PySide6.QtWebEngineWidgets import QWebEngineView
                from PySide6.QtCore import QUrl
                self.web_view = QWebEngineView()
                self.web_view.load(QUrl("https://www.google.com/maps"))
                container_layout.addWidget(self.web_view)
            except ImportError:
                debug.trace_exception_info(5, "QWebEngineView import")
                self.map_area = QLabel("Desktop Map Area\\n(QWebEngineView not available)")
                self.map_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
                container_layout.addWidget(self.map_area)

        layout.addWidget(self.map_container)
        layout.addStretch()

class RealTimeGPSWidget(QWidget):
    """8. Real-Time GPS - Track movement."""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(_title("📍  Real-Time GPS"))
        layout.addWidget(_hint("Track user movement. (Uses QtPositioning or plyer)"))
        layout.addWidget(_sep())
        
        self.status = QLabel("Location: Unknown")
        layout.addWidget(self.status)
        
        btn = QPushButton("Get GPS Fix")
        btn.clicked.connect(self.get_gps)
        layout.addWidget(btn)
        layout.addStretch()

    def get_gps(self):
        """Initiate GPS location acquisition."""
        hw.get_gps(self.on_location)
        self.status.setText("GPS requested via HardwareFacade.")

    def on_location(self, **kwargs):
        """Handle incoming GPS location updates."""
        self.status.setText(f"Lat: {kwargs.get('lat')}, Lon: {kwargs.get('lon')}")

class BluetoothScannerWidget(QWidget):
    """9. Bluetooth Scanner - Discover nearby BLE devices."""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(_title("📡  Bluetooth Scanner"))
        layout.addWidget(_hint("Discover nearby BLE devices. (Uses QtBluetooth)"))
        layout.addWidget(_sep())
        
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        btn = QPushButton("Scan BLE")
        btn.clicked.connect(self.scan)
        layout.addWidget(btn)

    def scan(self):
        """Initiate a scan for nearby Bluetooth Low Energy devices."""
        self.list_widget.clear()
        self.list_widget.addItem("Scanning... (Skeleton)")
        # from PySide6.QtBluetooth import QBluetoothDeviceDiscoveryAgent
        # self.agent = QBluetoothDeviceDiscoveryAgent()
        # self.agent.deviceDiscovered.connect(self.device_discovered)
        # self.agent.start()

class ShareSheetWidget(QWidget):
    """10. Share Sheet - Android Share menu."""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(_title("📤  Share Sheet"))
        layout.addWidget(_hint("Use native Android 'Share' menu via intents."))
        layout.addWidget(_sep())
        
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Text to share...")
        layout.addWidget(self.text_input)
        
        btn = QPushButton("Share Text")
        btn.clicked.connect(self.share)
        layout.addWidget(btn)
        
        self.status = QLabel("")
        layout.addWidget(self.status)
        layout.addStretch()

    def share(self):
        """Trigger the system-native share sheet for the input text."""
        text = self.text_input.text()
        hw.share_text(text)
        self.status.setText(f"Share intent triggered for: '{text}'")

class SmartphoneFeaturesMenu(BaseMenuWidget):
    """Launcher menu for smartphone feature prototypes."""
    def __init__(self):
        feature_list = [
            ("Auth", BiometricAuthWidget()),
            ("Voice", VoiceCommandWidget()),
            ("Camera", CameraPreviewWidget()),
            ("Push", PushNotificationsWidget()),
            ("Haptic", HapticConfirmationWidget()),
            ("Gallery", SmoothGalleryWidget()),
            ("Map", MultiTouchMapWidget()),
            ("GPS", RealTimeGPSWidget()),
            ("BLE", BluetoothScannerWidget()),
            ("Share", ShareSheetWidget()),
        ]
        super().__init__("Smartphone Features", "Ten useful features in smartphone apps for prototyping.", feature_list)

## OLD:
## def create_feature_tabs():
##     ...
##     return FeatureMenuWidget(feature_list)

