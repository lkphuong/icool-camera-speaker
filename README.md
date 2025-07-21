# iCool Camera Speaker

A WebSocket audio server built with TypeScript that receives audio data over WebSocket connections and plays it through system speakers. The application can be run as a Windows service for continuous operation.

## Features

- Real-time audio streaming via WebSocket
- IP-based access control for security
- Configurable logging with automatic log rotation
- Environment-based configuration
- Windows service support for background operation
- Configurable audio parameters (sample rate, channels, chunk size)
- Connection monitoring and timeout handling

## Prerequisites

- Node.js (v14 or higher)
- npm or yarn
- Windows OS (for service functionality)

## Installation

```bash
npm install
```

## Configuration

1. Copy the environment template file:

   ```bash
   cp .env.example .env
   ```

2. Configure your environment variables in `.env`:

   ```bash
   # Server Configuration
   SERVER_HOST=0.0.0.0
   SERVER_PORT=8765

   # Audio Configuration
   AUDIO_CHUNK_SIZE=1024
   AUDIO_CHANNELS=1
   AUDIO_SAMPLE_RATE=44100
   AUDIO_SAMPLE_SIZE=16

   # Logging Configuration
   LOG_DIRECTORY=logs
   LOG_RETENTION_DAYS=7
   LOG_LEVEL=info

   # Security Configuration
   ALLOWED_IPS=127.0.0.1,::1,localhost,your.client.ip.here

   # WebSocket Configuration
   MAX_CONNECTIONS=1
   CONNECTION_TIMEOUT=30000

   # Environment
   NODE_ENV=production
   DEBUG=false
   ```

## Development

### Running in Development Mode

```bash
# Run directly with ts-node
npm run dev

# Or build and run
npm run build
npm start
```

### Available Scripts

- `npm run build` - Compile TypeScript to JavaScript
- `npm start` - Run the compiled application
- `npm run dev` - Run in development mode with ts-node
- `npm run clean` - Remove compiled files
- `npm run test-config` - Test configuration loading
- `npm run test-server-config` - Test server configuration

## Production Deployment

### Option 1: Direct Execution

```bash
# Build the application
npm run build

# Run the application
npm start
```

### Option 2: Windows Service (Recommended)

1. **Build the application:**

   ```bash
   npm run build
   ```

2. **Update service configuration:**

   - Open `node-service.js`
   - Update the `script` path to your absolute path:

   ```javascript
   script: "C:\\path\\to\\your\\project\\dist\\main.js";
   ```

3. **Install and start the service:**

   ```bash
   node node-service.js
   ```

4. **Verify service installation:**

   - Open Windows Services (`services.msc`)
   - Look for "iCool Camera Speaker Service"
   - Ensure the status is "Running"
   - Set **Startup Type** to **Automatic** for auto-start on boot

5. **Service Management:**

   ```bash
   # Check service status
   sc query "icool-camera-speaker"

   # Start service manually
   sc start "icool-camera-speaker"

   # Stop service
   sc stop "icool-camera-speaker"
   ```

## Usage

### WebSocket Client Connection

Connect to the WebSocket server using the configured host and port:

```javascript
const ws = new WebSocket("ws://SERVER_HOST:SERVER_PORT");

// Send audio data
ws.send(
  JSON.stringify({
    type: "audio",
    data: base64EncodedAudioData,
  })
);

// Send ping for connection check
ws.send(
  JSON.stringify({
    type: "ping",
  })
);
```

### Audio Format

The server expects audio data in the following format:

- **Sample Rate:** Configurable (default: 44100 Hz)
- **Channels:** Configurable (default: 1 - mono)
- **Sample Size:** Configurable (default: 16-bit)
- **Format:** Base64 encoded PCM audio data

## Logging

Logs are automatically written to the configured log directory with the following features:

- **Daily log rotation** - New log file created each day
- **Automatic cleanup** - Old logs removed based on retention policy
- **Configurable levels** - info, warn, error, debug
- **Structured logging** - Timestamps and formatted output

## Security

- **IP Whitelist:** Only configured IP addresses can connect
- **Connection Limits:** Maximum number of concurrent connections
- **Timeout Handling:** Automatic disconnection of inactive clients

## Troubleshooting

### Common Issues

1. **Service fails to start:**

   - Verify the script path in `node-service.js` is correct
   - Check Windows Event Viewer for detailed error messages
   - Ensure Node.js is installed and accessible system-wide

2. **Audio not playing:**

   - Check system audio settings and speakers
   - Verify audio format matches configuration
   - Review logs for audio-related errors

3. **Connection refused:**

   - Verify the server is running and listening on the correct port
   - Check firewall settings
   - Ensure client IP is in the allowed list

4. **High memory usage:**
   - Adjust `max-old-space-size` in `node-service.js`
   - Review audio chunk size and connection timeout settings

### Log Analysis

Check the application logs in the configured log directory:

```bash
# View today's logs
tail -f logs/$(date +%Y-%m-%d).log

# View recent errors
grep "ERROR" logs/*.log | tail -20
```

## License

MIT
