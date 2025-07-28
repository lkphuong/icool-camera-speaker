import asyncio
import websockets
import json
import pyaudio
import base64
import logging
import os
from datetime import datetime, timedelta
import glob
import platform

# Volume control imports
if platform.system() == "Windows":
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume, AudioSession
        from comtypes import CLSCTX_ALL, CoInitialize, CoUninitialize
        from ctypes import cast, POINTER
        import comtypes
        VOLUME_CONTROL_AVAILABLE = True
        print("Windows volume control available")
    except ImportError as e:
        VOLUME_CONTROL_AVAILABLE = False
        print(f"pycaw not available - volume control disabled: {e}")
else:
    VOLUME_CONTROL_AVAILABLE = False
    print("Volume control only available on Windows")

# Configuration for audio
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

class AudioServer:
    def __init__(self, host="localhost", port=8765, allowed_ips=None):
        self.host = host
        self.port = port
        self.current_client = None
        self.allowed_ips = allowed_ips or ["127.0.0.1", "::1", "localhost"]
        
        # Initialize COM for Windows volume control
        if platform.system() == "Windows" and VOLUME_CONTROL_AVAILABLE:
            try:
                CoInitialize()
            except Exception as e:
                print(f"Warning: COM initialization failed: {e}")
        
        # Setup logging
        self.setup_logging()
        
        # Setup volume control
        self.volume_endpoint = None
        if VOLUME_CONTROL_AVAILABLE:
            self.setup_volume_control()

        # Initialize audio output
        self.p = pyaudio.PyAudio()
        
        # Log available audio devices
        self.log_audio_devices()
        
        try:
            # Get the default output device for Windows
            if platform.system() == "Windows":
                device_index = self.get_best_output_device()
            else:
                device_index = None
                
            self.stream = self.p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                output=True,
                frames_per_buffer=CHUNK,
                output_device_index=device_index
            )
            
            # Log the device being used
            if device_index is not None:
                device_info = self.p.get_device_info_by_index(device_index)
            else:
                device_info = self.p.get_default_output_device_info()
            self.logger.info(f"Audio output initialized on device: {device_info['name']} (Device ID: {device_info['index']})")
            
        except Exception as error:
            self.logger.error(f"Error opening audio output: {error}")
            self.p.terminate()
            raise

    def setup_logging(self):
        """Setup logging with rotation and cleanup old files"""
        # Create logs directory if not exists
        logs_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        # Clean up old log files (older than 7 days)
        self.cleanup_old_logs(logs_dir)
        
        # Setup logger
        self.logger = logging.getLogger('AudioServer')
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create file handler with daily rotation
        log_filename = os.path.join(logs_dir, f"{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def cleanup_old_logs(self, logs_dir):
        """Remove log files older than 7 days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=7)
            log_files = glob.glob(os.path.join(logs_dir, "*.log"))
            
            for log_file in log_files:
                try:
                    file_date_str = os.path.basename(log_file).replace(".log", "")
                    file_date = datetime.strptime(file_date_str, '%Y%m%d')
                    
                    if file_date < cutoff_date:
                        os.remove(log_file)
                        print(f"Removed old log file: {log_file}")
                except Exception as e:
                    print(f"Error processing log file {log_file}: {e}")
                    
        except Exception as e:
            print(f"Error during log cleanup: {e}")
    
    def get_best_output_device(self):
        """Find the best output device for Windows"""
        try:
            device_count = self.p.get_device_count()
            default_device = self.p.get_default_output_device_info()
            
            # First, try to use the default device
            if default_device['maxOutputChannels'] > 0:
                return default_device['index']
            
            # If default doesn't work, find any device with output channels
            for i in range(device_count):
                try:
                    info = self.p.get_device_info_by_index(i)
                    if info['maxOutputChannels'] > 0:
                        return i
                except:
                    continue
                    
            return None
        except Exception as e:
            self.logger.error(f"Error finding output device: {e}")
            return None
    
    def setup_volume_control(self):
        """Setup Windows volume control"""
        if not VOLUME_CONTROL_AVAILABLE:
            return
            
        try:
            # Initialize COM if not already done
            try:
                CoInitialize()
            except:
                pass  # COM might already be initialized
                
            devices = AudioUtilities.GetSpeakers()
            if devices is None:
                self.logger.error("No audio devices found")
                return
                
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self.volume_endpoint = cast(interface, POINTER(IAudioEndpointVolume))
            
            # Test the volume interface
            current_volume = self.volume_endpoint.GetMasterScalarVolume()
            self.logger.info(f"Volume control initialized successfully. Current volume: {current_volume * 100:.1f}%")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize volume control: {e}")
            self.volume_endpoint = None
    
    def set_volume(self, volume_percent):
        """Set system volume (0-100%)"""
        if not VOLUME_CONTROL_AVAILABLE or not self.volume_endpoint:
            self.logger.debug(f"Volume control not available, cannot set volume to {volume_percent}%")
            return False
        
        try:
            # Clamp volume between 0 and 100
            volume_percent = max(0, min(100, volume_percent))
            volume_level = volume_percent / 100.0
            
            # Use the correct method for setting volume
            self.volume_endpoint.SetMasterScalarVolume(volume_level, None)
            
            # Verify the volume was set
            actual_volume = self.volume_endpoint.GetMasterScalarVolume()
            actual_percent = actual_volume * 100
            
            self.logger.info(f"Volume set to {volume_percent}% (actual: {actual_percent:.1f}%)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set volume to {volume_percent}%: {e}")
            
            # Try alternative approach using AudioSession
            try:
                self.logger.info("Trying alternative volume control method...")
                sessions = AudioUtilities.GetAllSessions()
                for session in sessions:
                    if session.Process and session.Process.name() == "python.exe":
                        volume_interface = session.SimpleAudioVolume
                        volume_interface.SetMasterVolume(volume_level, None)
                        self.logger.info(f"Alternative method: Volume set to {volume_percent}%")
                        return True
            except Exception as e2:
                self.logger.error(f"Alternative volume control also failed: {e2}")
            
            return False

    def get_volume(self):
        """Get current system volume (0-100%)"""
        if not VOLUME_CONTROL_AVAILABLE or not self.volume_endpoint:
            return None
        
        try:
            volume_level = self.volume_endpoint.GetMasterScalarVolume()
            return int(volume_level * 100)
        except Exception as e:
            self.logger.error(f"Failed to get volume: {e}")
            return None

    def log_audio_devices(self):
        """Log thông tin về tất cả audio devices có sẵn"""
        self.logger.info("Available Audio Devices:")
        self.logger.info("-" * 50)
        
        device_count = self.p.get_device_count()
        default_output = self.p.get_default_output_device_info()
        
        for i in range(device_count):
            try:
                info = self.p.get_device_info_by_index(i)
                device_type = "OUTPUT" if info['maxOutputChannels'] > 0 else "INPUT"
                is_default = "DEFAULT" if info['index'] == default_output['index'] else ""
                
                self.logger.info(f"  [{i}] {device_type} {is_default}")
                self.logger.info(f"      Name: {info['name']}")
                self.logger.info(f"      Max Channels: In={info['maxInputChannels']}, Out={info['maxOutputChannels']}")
                self.logger.info(f"      Sample Rate: {info['defaultSampleRate']}")
                
            except Exception as e:
                self.logger.error(f"  [{i}] Error getting device info: {e}")
        
        self.logger.info("-" * 50)
        self.logger.info(f"Default Output Device: {default_output['name']} (ID: {default_output['index']})")
        self.logger.info("")

    def f(self, ip):
        return True
        #return ip in self.allowed_ips
    
    async def handle_client(self, websocket, path):
        client_addr = websocket.remote_address
        client_ip = client_addr[0]

        origin = websocket.request_headers.get('Origin')
        # if not self.is_ip_allowed(client_ip):
        #     self.logger.warning(f"Client {client_addr} is not allowed")
        #     await websocket.close(code=403, reason="Forbidden - IP not allowed")
        #     return

        # if self.current_client is not None:
        #     self.logger.warning(f"Rejecting client {client_addr} - another client is already connected")
        #     await websocket.close(code=1013, reason="Server busy - only one client allowed")
        #     return

        self.logger.info(f"Client connected: {client_addr}")
        self.current_client = websocket
        
        # Set volume to 100% when client connects
        current_volume = self.get_volume()
        if current_volume is not None:
            self.logger.info(f"Current system volume: {current_volume}%")
        
        success = self.set_volume(100)
        if not success:
            self.logger.warning("Failed to set volume to 100% - continuing without volume control")

        try:
            async for message in websocket:
                data = json.loads(message)
                #self.logger.debug(f"Received audio data from {client_addr}")
                #self.logger.debug(f"Message from {client_addr}: {data}")
                if data.get("type") == "audio":
                    audio_b64 = data.get("data", "")
                    # self.logger.debug("Processing audio data ", audio_b64)
                    # self.logger.debug(f"Received audio data from {client_addr}")
                    if audio_b64:
                        audio_data = base64.b64decode(audio_b64)
                        self.play_audio(audio_data)
                elif data.get("type") == "ping":
                    await websocket.send(json.dumps({"type": "pong"}))
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"Client {client_addr} disconnected")
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON from client {client_addr}")
        except Exception as error:
            self.logger.error(f"Error handling client {client_addr}: {error}")
        finally:
            self.current_client = None
            # Set volume to 0% when client disconnects
            self.set_volume(0)
            self.logger.info(f"Client {client_addr} has been reset")

    def play_audio(self, audio_data):
        if len(audio_data) == 0:
            self.logger.warning("No audio data to play")
            return
        
        expected_size = CHUNK * 2 # 2 bytes per sample
        original_size = len(audio_data)

        if len(audio_data) > expected_size:
            audio_data = audio_data[:expected_size]
        elif len(audio_data) < expected_size:
            audio_data += b'\x00' * (expected_size - len(audio_data))

        try:
            # Check if stream is still active
            if not self.stream.is_active():
                self.logger.warning("Audio stream is not active, attempting to restart...")
                self.stream.start_stream()
            
            # Get current device info for logging
            try:
                if hasattr(self.stream, '_output_device_index') and self.stream._output_device_index is not None:
                    device_info = self.p.get_device_info_by_index(self.stream._output_device_index)
                else:
                    device_info = self.p.get_default_output_device_info()
                
                self.logger.debug(f"Playing audio on: {device_info['name']} (Device ID: {device_info['index']})")
            except Exception as e:
                self.logger.debug(f"Could not get device info: {e}")
            
            self.logger.debug(f"Audio stats: Original={original_size} bytes, Processed={len(audio_data)} bytes, Expected={expected_size} bytes")
            
            # Write audio data to stream
            self.stream.write(audio_data)
            self.logger.debug("Audio played successfully")
            
        except Exception as e:
            self.logger.error(f"Error playing audio: {e}")
            # Try to recover by recreating the stream
            try:
                self.logger.info("Attempting to recover audio stream...")
                self.stream.stop_stream()
                self.stream.close()
                
                # Recreate stream
                device_index = None
                if platform.system() == "Windows":
                    device_index = self.get_best_output_device()
                
                self.stream = self.p.open(
                    format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    output=True,
                    frames_per_buffer=CHUNK,
                    output_device_index=device_index
                )
                
                # Try playing again
                self.stream.write(audio_data)
                self.logger.info("Audio stream recovered and audio played successfully")
                
            except Exception as recovery_error:
                self.logger.error(f"Failed to recover audio stream: {recovery_error}")

    async def start(self):
        self.logger.info(f"Simple Audio Server starting at ws://{self.host}:{self.port}")
        
        try:
            async with websockets.serve(self.handle_client, self.host, self.port):
                self.logger.info("Server is ready to accept connections")
                self.logger.info("Waiting for client to connect...")
                
                await asyncio.Future()  # run forever
        except Exception as error:
            self.logger.error(f"Error starting server: {error}")
        finally:
            self.cleanup()

    def cleanup(self):
        self.logger.info("Cleaning up...")
        # Set volume to 0% on cleanup
        self.set_volume(0)
        
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
        if hasattr(self, 'p'):
            self.p.terminate()
            
        # Cleanup COM for Windows
        if platform.system() == "Windows" and VOLUME_CONTROL_AVAILABLE:
            try:
                CoUninitialize()
            except Exception as e:
                self.logger.debug(f"COM cleanup warning: {e}")
                
        self.logger.info("Cleanup complete.")

async def main():

    allowed_ips = ["127.0.0.1", "::1", "localhost", "118.69.196.115"]

    server = AudioServer(host='0.0.0.0', allowed_ips=allowed_ips)
    try:
        await server.start()
    except KeyboardInterrupt:
        server.logger.info("Stopping server...")
    finally: 
        server.cleanup()

if __name__ == "__main__":
    print("Simple Audio Server")
    print("Server will play audio received via WebSocket.")
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")
