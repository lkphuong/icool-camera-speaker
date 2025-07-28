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
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        from ctypes import cast, POINTER
        VOLUME_CONTROL_AVAILABLE = True
    except ImportError:
        VOLUME_CONTROL_AVAILABLE = False
        print("pycaw not available - volume control disabled")
else:
    VOLUME_CONTROL_AVAILABLE = False

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
            self.stream = self.p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                output=True,
                frames_per_buffer=CHUNK
            )
            
            # Log the device being used
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
    
    def setup_volume_control(self):
        """Setup Windows volume control"""
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self.volume_endpoint = cast(interface, POINTER(IAudioEndpointVolume))
            self.logger.info("Volume control initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize volume control: {e}")
            self.volume_endpoint = None
    
    def set_volume(self, volume_percent):
        """Set system volume (0-100%)"""
        if not VOLUME_CONTROL_AVAILABLE or not self.volume_endpoint:
            return
        
        try:
            volume_level = volume_percent / 100.0
            self.volume_endpoint.SetMasterVolume(volume_level, None)
            self.logger.info(f"Volume set to {volume_percent}%")
        except Exception as e:
            self.logger.error(f"Failed to set volume: {e}")

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
        self.set_volume(100)

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
            # Get current device info
            device_info = self.p.get_default_output_device_info()
            
            # Log audio playback details
            self.logger.debug(f"Playing audio on: {device_info['name']} (Device ID: {device_info['index']})")
            self.logger.debug(f"Audio stats: Original={original_size} bytes, Processed={len(audio_data)} bytes, Expected={expected_size} bytes")
            
            self.stream.write(audio_data)
            self.logger.debug("Audio played successfully")
            
        except Exception as e:
            self.logger.error(f"Error playing audio: {e}")

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
