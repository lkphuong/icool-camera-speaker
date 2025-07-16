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
        try:
            self.stream = self.p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                output=True,
                frames_per_buffer=CHUNK
            )
            print("✅ Audio output initialized")
        except Exception as error:
            print(f"❌ Error opening audio output: {error}")
            self.p.terminate()
            raise
    def is_ip_allowed(self, ip):
        return ip in self.allowed_ips
    
    async def handle_client(self, websocket, path):
        client_addr = websocket.remote_address
        client_ip = client_addr[0]

        origin = websocket.request_headers.get('Origin')
        if not self.is_ip_allowed(client_ip):
            print(f"❌ Client {client_addr} is not allowed")
            await websocket.close(code=403, reason="Forbidden - IP not allowed")
            return

        if self.current_client is not None:
            print(f"❌ Rejecting client {client_addr} - another client is already connected")
            await websocket.close(code=1013, reason="Server busy - only one client allowed")
            return

        print(f"✅ Client connected: {client_addr}")
        self.current_client = websocket

        try:
            async for message in websocket:
                data = json.loads(message)
                print(f"🔊 Received audio data from {client_addr}")
                if data.get("type") == "audio":
                    audio_b64 = data.get("data", "")
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

        if len(audio_data) > expected_size:
            audio_data = audio_data[:expected_size]
        elif len(audio_data) < expected_size:
            audio_data += b'\x00' * (expected_size - len(audio_data))

        self.stream.write(audio_data)

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

    server = AudioServer(allowed_ips=allowed_ips)
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
    