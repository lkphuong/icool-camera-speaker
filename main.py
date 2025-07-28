import asyncio
import websockets
import json
import pyaudio
import base64
import logging
import os
from datetime import datetime

# Audio configuration
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

class AudioServer:
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        
        # Setup logging
        self.setup_logging()
        
        # Initialize audio
        self.p = pyaudio.PyAudio()
        self.setup_audio_stream()

    def setup_logging(self):
        """Setup simple logging"""
        logs_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        # Setup logger
        self.logger = logging.getLogger('AudioServer')
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create file handler
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
    
    def setup_audio_stream(self):
        """Setup audio output stream"""
        try:
            self.stream = self.p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                output=True,
                frames_per_buffer=CHUNK
            )
            self.logger.info("Audio stream initialized successfully")
            
        except Exception as error:
            self.logger.error(f"Error opening audio stream: {error}")
            self.p.terminate()
            raise
    
    async def handle_client(self, websocket, path):
        """Handle client connection and audio data"""
        client_addr = websocket.remote_address
        self.logger.info(f"Client connected: {client_addr}")

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    self.logger.error(f"Received message from {client_addr}")
                    if data.get("type") == "audio":
                        audio_b64 = data.get("data", "")
                        if audio_b64:
                            audio_data = base64.b64decode(audio_b64)
                            self.play_audio(audio_data)
                            
                    elif data.get("type") == "ping":
                        await websocket.send(json.dumps({"type": "pong"}))
                        
                except json.JSONDecodeError:
                    self.logger.error(f"Invalid JSON from client {client_addr}")
                except Exception as e:
                    self.logger.error(f"Error processing message from {client_addr}: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"Client {client_addr} disconnected")
        except Exception as error:
            self.logger.error(f"Error handling client {client_addr}: {error}")
        finally:
            self.logger.info(f"Client {client_addr} session ended")

    def play_audio(self, audio_data):
        """Play audio data through the output stream"""
        if len(audio_data) == 0:
            self.logger.warning("No audio data to play")
            return
        
        expected_size = CHUNK * 2  # 2 bytes per sample
        original_size = len(audio_data)

        # Adjust audio data size to match expected chunk size
        if len(audio_data) > expected_size:
            audio_data = audio_data[:expected_size]
        elif len(audio_data) < expected_size:
            audio_data += b'\x00' * (expected_size - len(audio_data))

        try:
            self.stream.write(audio_data)
            self.logger.debug(f"Audio played successfully - Size: {original_size} -> {len(audio_data)} bytes")
            
        except Exception as e:
            self.logger.error(f"Error playing audio: {e}")
            # Try to recover by recreating the stream
            try:
                self.logger.info("Attempting to recover audio stream...")
                self.stream.stop_stream()
                self.stream.close()
                self.setup_audio_stream()
                
                # Try playing again
                self.stream.write(audio_data)
                self.logger.info("Audio stream recovered and audio played successfully")
                
            except Exception as recovery_error:
                self.logger.error(f"Failed to recover audio stream: {recovery_error}")

    async def start(self):
        """Start the WebSocket server"""
        self.logger.info(f"Audio Server starting at ws://{self.host}:{self.port}")
        
        try:
            async with websockets.serve(self.handle_client, self.host, self.port):
                self.logger.info("Server is ready to accept connections")
                self.logger.info("Waiting for clients to connect...")
                
                await asyncio.Future()  # run forever
        except Exception as error:
            self.logger.error(f"Error starting server: {error}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        self.logger.info("Cleaning up resources...")
        
        if hasattr(self, 'stream'):
            try:
                self.stream.stop_stream()
                self.stream.close()
                self.logger.info("Audio stream closed")
            except Exception as e:
                self.logger.error(f"Error closing audio stream: {e}")
                
        if hasattr(self, 'p'):
            try:
                self.p.terminate()
                self.logger.info("PyAudio terminated")
            except Exception as e:
                self.logger.error(f"Error terminating PyAudio: {e}")
                
        self.logger.info("Cleanup complete")

async def main():
    """Main function to run the audio server"""
    server = AudioServer(host='0.0.0.0', port=8765)
    try:
        await server.start()
    except KeyboardInterrupt:
        server.logger.info("Server stopped by user")
    finally: 
        server.cleanup()

if __name__ == "__main__":
    print("Simple Audio Server")
    print("Server will receive and play audio via WebSocket")
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")
