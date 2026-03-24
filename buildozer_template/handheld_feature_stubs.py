"""Smartphone handheld mock features and Hardware Abstraction Layer."""
import sys
from PySide6.QtCore import QStandardPaths, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QLineEdit
from feature_stubs import _title, _hint, _sep, BaseMenuWidget

# ===========================================================================
# Hardware Abstraction Layer (HAL)
# ===========================================================================
class HardwareFacade:
    """Base class for hardware interaction."""
    def authenticate_biometric(self):
        """Mock auth."""
        return False
    def vibrate(self, duration_ms):
        """Mock vibrate."""
    def notify(self, title, message):
        """Mock notify."""
    def share_text(self, text):
        """Mock share."""
    def get_gps(self, callback):
        """Mock gps."""

class DesktopHardware(HardwareFacade):
    """Hardware implementation for desktop environments."""
    def authenticate_biometric(self):
        print("Desktop: Simulated Auth Success")
        return True
    def vibrate(self, duration_ms):
        print(f"Desktop: Simulated vibration for {duration_ms}ms")
    def notify(self, title, message):
        print(f"Desktop Notification: {title} - {message}")
    def share_text(self, text):
        print(f"Desktop Share: {text}")
    def get_gps(self, callback):
        callback(lat=37.7749, lon=-122.4194)

class AndroidHardware(HardwareFacade):
    """Hardware implementation for Android devices."""
    def authenticate_biometric(self):
        try:
            from jnius import autoclass  # pylint: disable=import-outside-toplevel,import-error,unused-import
            return True
        except ImportError:
            return False
            
    def vibrate(self, duration_ms):
        try:
            from plyer import vibrator  # pylint: disable=import-outside-toplevel,import-error
            vibrator.vibrate(time=duration_ms/1000.0)
        except Exception:  # pylint: disable=broad-exception-caught
            pass
            
    def notify(self, title, message):
        try:
            from plyer import notification  # pylint: disable=import-outside-toplevel,import-error
            notification.notify(title=title, message=message)
        except Exception:  # pylint: disable=broad-exception-caught
            pass
            
    def share_text(self, text):
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
        except Exception:  # pylint: disable=broad-exception-caught
            pass
            
    def get_gps(self, callback):
        try:
            from plyer import gps  # pylint: disable=import-outside-toplevel,import-error
            gps.configure(on_location=callback)
            gps.start()
        except Exception:  # pylint: disable=broad-exception-caught
            pass

class IOSHardware(HardwareFacade):
    """Hardware implementation for iOS devices."""
    def authenticate_biometric(self):
        return False
    # Additional iOS specifics using pyobjus/plyer would go here

def get_hardware():
    """Factory to retrieve hardware based on current OS."""
    if sys.platform == "android":
        return AndroidHardware()
    if sys.platform == "ios":
        return IOSHardware()
    return DesktopHardware()

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
        """Mock authentication routine."""
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
        """Start listening for audio."""
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
        """Initialize and start camera preview."""
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
        """Send a push notification."""
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
        """Trigger haptic feedback for duration_ms."""
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
        """Load and display standard images."""
        self.list_widget.clear()
        paths = QStandardPaths.standardLocations(QStandardPaths.StandardLocation.PicturesLocation)
        if paths:
            self.list_widget.addItem(f"Searching in: {paths[0]}")
            # Skeleton: scan paths[0] for .jpg/.png and add QListWidgetItem with icon
        else:
            self.list_widget.addItem("No standard Pictures location found.")

class MultiTouchMapWidget(QWidget):
    """7. Multi-Touch Map - Pinch-to-zoom fluidity."""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(_title("🗺  Multi-Touch Map"))
        layout.addWidget(_hint("Test pinch-to-zoom. (Requires touch display)"))
        layout.addWidget(_sep())
        
        self.map_area = QLabel("Map Area\\n(Pinch me)")
        self.map_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.map_area.setStyleSheet("background: #2a2a2a; border: 1px solid #555; min-height: 200px;")
        self.map_area.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)
        layout.addWidget(self.map_area)
        layout.addStretch()

    def eventFilter(self, obj, event):
        """Handle touch events for pinch-to-zoom."""
        # In a real widget, you override event() or viewportEvent() to handle QEvent.Type.TouchBegin
        # and parse QTouchEvent to scale/rotate content.
        return super().eventFilter(obj, event)

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
        """Start acquiring GPS coordinates."""
        hw.get_gps(self.on_location)
        self.status.setText("GPS requested via HardwareFacade.")

    def on_location(self, **kwargs):
        """Callback for when GPS location updates."""
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
        """Initiate BLE device scan."""
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
        """Trigger system share intent."""
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

