import asyncio
import websockets
import json
import pyaudio
import base64

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
            print(f"✅ Audio output initialized on device: {device_info['name']} (Device ID: {device_info['index']})")
            
        except Exception as error:
            print(f"❌ Error opening audio output: {error}")
            self.p.terminate()
            raise

    def log_audio_devices(self):
        """Log thông tin về tất cả audio devices có sẵn"""
        print("\n🔊 Available Audio Devices:")
        print("-" * 50)
        
        device_count = self.p.get_device_count()
        default_output = self.p.get_default_output_device_info()
        
        for i in range(device_count):
            try:
                info = self.p.get_device_info_by_index(i)
                device_type = "🔊 OUTPUT" if info['maxOutputChannels'] > 0 else "🎤 INPUT"
                is_default = "⭐ DEFAULT" if info['index'] == default_output['index'] else ""
                
                print(f"  [{i}] {device_type} {is_default}")
                print(f"      Name: {info['name']}")
                print(f"      Max Channels: In={info['maxInputChannels']}, Out={info['maxOutputChannels']}")
                print(f"      Sample Rate: {info['defaultSampleRate']}")
                print()
                
            except Exception as e:
                print(f"  [{i}] ❌ Error getting device info: {e}")
        
        print("-" * 50)
        print(f"🎯 Default Output Device: {default_output['name']} (ID: {default_output['index']})")
        print()

    def is_ip_allowed(self, ip):
        return True
        #return ip in self.allowed_ips
    
    async def handle_client(self, websocket, path):
        client_addr = websocket.remote_address
        client_ip = client_addr[0]

        origin = websocket.request_headers.get('Origin')
        if not self.is_ip_allowed(client_ip):
            print(f"❌ Client {client_addr} is not allowed")
            await websocket.close(code=403, reason="Forbidden - IP not allowed")
            return

        # if self.current_client is not None:
        #     print(f"❌ Rejecting client {client_addr} - another client is already connected")
        #     await websocket.close(code=1013, reason="Server busy - only one client allowed")
        #     return

        print(f"✅ Client connected: {client_addr}")
        self.current_client = websocket

        try:
            async for message in websocket:
                data = json.loads(message)
                print(f"🔊 Received audio data from {client_addr}")
                print(f"🔊 Message from {client_addr}: {data}")
                if data.get("type") == "audio":
                    audio_b64 = data.get("data", "")
                    print("🔊 Processing audio data ", audio_b64)
                    print(f"🔊 Received audio data from {client_addr}")
                    if audio_b64:
                        audio_data = base64.b64decode(audio_b64)
                        self.play_audio(audio_data)
                elif data.get("type") == "ping":
                    await websocket.send(json.dumps({"type": "pong"}))
        except websockets.exceptions.ConnectionClosed:
            print(f"❌ Client {client_addr} disconnected")
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON from client {client_addr}")
        except Exception as error:
            print(f"❌ Error handling client {client_addr}: {error}")
        finally:
            self.current_client = None
            print(f"🔄 Client {client_addr} has been reset")

    def play_audio(self, audio_data):
        if len(audio_data) == 0:
            print("❌ No audio data to play")
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
            print(f"🎵 Playing audio on: {device_info['name']} (Device ID: {device_info['index']})")
            print(f"📊 Audio stats: Original={original_size} bytes, Processed={len(audio_data)} bytes, Expected={expected_size} bytes")
            
            self.stream.write(audio_data)
            print(f"✅ Audio played successfully")
            
        except Exception as e:
            print(f"❌ Error playing audio: {e}")

    async def start(self):
        print(f"🌐 Simple Audio Server starting at ws://{self.host}:{self.port}")
        
        try:
            async with websockets.serve(self.handle_client, self.host, self.port):
                print("✅ Server is ready to accept connections")
                print("🔊 Waiting for client to connect...")
                
                await asyncio.Future()  # run forever
        except Exception as error:
            print(f"❌ Error starting server: {error}")
        finally:
            self.cleanup()

    def cleanup(self):
        print("🔄 Cleaning up...")
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
        if hasattr(self, 'p'):
            self.p.terminate()
        print("✅ Cleanup complete.")

async def main():

    allowed_ips = ["127.0.0.1", "::1", "localhost", "118.69.196.115"]

    server = AudioServer(host='0.0.0.0', allowed_ips=allowed_ips)
    try:
        await server.start()
    except KeyboardInterrupt:
        print("\n❌ Stopping server...")
    finally: 
        server.cleanup()

if __name__ == "__main__":
    print("🎙️ Simple Audio Server")
    print("Server will play audio received via WebSocket.")
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Error: {e}")
