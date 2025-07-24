import * as WebSocket from "ws";
import { Server as WebSocketServer } from "ws";
import { IncomingMessage } from "http";
import { spawn, ChildProcess } from "child_process";
import { Logger } from "./log";
import {
  audioConfig,
  serverConfig,
  loggingConfig,
  securityConfig,
  webSocketConfig,
  isDevelopment,
  isDebugEnabled,
  printConfig,
} from "./config";
import { setVolumeWindows, setVolumeMac } from "./utils";

const CHUNK = audioConfig.chunkSize;
const CHANNELS = audioConfig.channels;
const RATE = audioConfig.sampleRate;
const SAMPLE_SIZE = audioConfig.sampleSize;

interface AudioMessage {
  type: "audio" | "ping";
  data?: string;
}

interface PongMessage {
  type: "pong";
}

class AudioServer {
  private host: string;
  private port: number;
  private currentClient: WebSocket | null = null;
  private allowedIps: string[];
  private server: WebSocketServer | null = null;
  private ffplayProcess: ChildProcess | null = null;
  private logger: Logger;

  constructor(host?: string, port?: number, allowedIps?: string[]) {
    this.host = host || serverConfig.host;
    this.port = port || serverConfig.port;
    this.allowedIps = allowedIps || securityConfig.allowedIps;
    this.logger = new Logger(
      loggingConfig.directory,
      loggingConfig.retentionDays
    );

    if (isDebugEnabled()) {
      console.log("Debug mode enabled");
      printConfig();
    }

    this.initializeAudio();
  }

  private initializeAudio(): void {
    try {
      const message = "Audio output (ffplay) ready for initialization";
      console.log(message);
      this.logger.writeLog(message, "info");

      const configMessage = `Audio config: ${CHANNELS} channel(s), ${RATE}Hz, ${SAMPLE_SIZE}-bit`;
      console.log(configMessage);
      this.logger.writeLog(configMessage, "info");
    } catch (error) {
      const errorMessage = `Error initializing audio output: ${error}`;
      console.error(errorMessage);
      this.logger.writeLog(errorMessage, "error");
      throw error;
    }
  }

  private logAudioDevices(): void {
    const deviceInfo = "Audio Device Information:";
    const separator = "-".repeat(50);
    const speakerInfo = "Using ffplay for real-time audio output";
    const configInfo = `Configuration: ${CHANNELS} channel(s), ${RATE}Hz, ${SAMPLE_SIZE}-bit`;

    console.log(`\n${deviceInfo}`);
    console.log(separator);
    console.log(speakerInfo);
    console.log(configInfo);
    console.log(separator);
    console.log();

    // Log to file
    this.logger.writeLog(
      `${deviceInfo} - ${speakerInfo} - ${configInfo}`,
      "info"
    );
  }

  private initializeFFPlay(): void {
    try {
      if (this.ffplayProcess) {
        console.log("Terminating existing FFplay process...");
        this.ffplayProcess.kill();
        this.ffplayProcess = null;
      }

      console.log("Starting FFplay with configuration:");
      console.log(`  - Format: s16le (16-bit signed little endian)`);
      console.log(`  - Sample Rate: ${RATE}Hz`);
      console.log(`  - Channels: ${CHANNELS}`);
      console.log(`  - Volume: 3.0x`);

      const args = [
        "-f",
        "s16le",
        "-ar",
        RATE.toString(),
        "-i",
        "pipe:0",
        "-nodisp",
        "-autoexit",
        "-af",
        "volume=3.0",
        "-probesize",
        "32",
        "-analyzeduration",
        "0",
        "-fflags",
        "nobuffer",
        "-flags",
        "low_delay",
        "-loglevel",
        "quiet",
      ];

      console.log(`FFplay command: ffplay ${args.join(" ")}`);
      this.ffplayProcess = spawn("ffplay", args);

      if (this.ffplayProcess.stdin) {
        const message =
          "FFplay process initialized successfully for real-time audio";
        console.log(message);
        this.logger.writeLog(message, "info");
      }

      // Capture stderr to see ffplay logs
      if (this.ffplayProcess.stderr) {
        this.ffplayProcess.stderr.on("data", (data) => {
          const stderr = data.toString().trim();
          // Only log non-empty stderr that's not just status updates
          if (stderr && !stderr.includes("nan") && !stderr.includes("fd=")) {
            console.log("FFplay stderr:", stderr);
          }
        });
      }

      // Capture stdout to see ffplay logs
      if (this.ffplayProcess.stdout) {
        this.ffplayProcess.stdout.on("data", (data) => {
          console.log("FFplay stdout:", data.toString().trim());
        });
      }

      this.ffplayProcess.on("error", (error) => {
        const errorMessage = `FFplay process error: ${error.message}`;
        console.error(errorMessage);
        this.logger.writeLog(errorMessage, "error");
      });

      this.ffplayProcess.on("exit", (code) => {
        const exitMessage = `FFplay process exited with code: ${code}`;
        console.log(exitMessage);
        this.logger.writeLog(exitMessage, "info");
        this.ffplayProcess = null;
      });
    } catch (error) {
      const errorMessage = `Error initializing FFplay: ${error}`;
      console.error(errorMessage);
      this.logger.writeLog(errorMessage, "error");
      throw error;
    }
  }

  private isIpAllowed(ip: string): boolean {
    // In development mode, allow all IPs for easier testing
    if (isDevelopment()) {
      return true;
    }
    return this.allowedIps.includes(ip);
  }

  private async handleClient(
    ws: WebSocket,
    request: IncomingMessage
  ): Promise<void> {
    const clientAddr = `${request.socket.remoteAddress}:${request.socket.remotePort}`;
    const clientIp = request.socket.remoteAddress || "";

    const origin = request.headers.origin;

    // Check IP allowlist if not in development mode
    if (!this.isIpAllowed(clientIp)) {
      const rejectMessage = `Client ${clientAddr} is not allowed (IP: ${clientIp})`;
      console.log(rejectMessage);
      this.logger.writeLog(rejectMessage, "warn");
      ws.close(403, "Forbidden - IP not allowed");
      return;
    }

    // Check max connections limit
    if (this.currentClient !== null && webSocketConfig.maxConnections === 1) {
      const busyMessage = `Rejecting client ${clientAddr} - server busy (max connections: ${webSocketConfig.maxConnections})`;
      console.log(busyMessage);
      this.logger.writeLog(busyMessage, "warn");
      ws.close(1013, "Server busy - maximum connections reached");
      return;
    }

    const connectMessage = `Client connected: ${clientAddr}`;

    //#region open volume control
    // Set volume for both platforms
    if (process.platform === "darwin") {
      await setVolumeMac(70); // Set macOS volume to 70%
    } else {
      await setVolumeWindows(100); // Set Windows volume to 100%
    }
    //#endregion

    // Initialize ffplay for this client session
    this.initializeFFPlay();

    console.log(connectMessage);
    this.logger.writeLog(connectMessage, "info");
    this.currentClient = ws;

    ws.on("message", (data: WebSocket.Data) => {
      try {
        const message: AudioMessage = JSON.parse(data.toString());
        const receiveMessage = `Received audio data from ${clientAddr}`;
        console.log(receiveMessage);
        console.log(`Message from ${clientAddr}:`, message);
        this.logger.writeLog(
          `${receiveMessage} - Type: ${message.type}`,
          "info"
        );

        if (message.type === "audio") {
          const audioB64 = message.data || "";
          console.log("Processing audio data", audioB64);
          console.log(`Received audio data from ${clientAddr}`);

          if (audioB64) {
            const audioData = Buffer.from(audioB64, "base64");
            this.playAudio(audioData);
          }
        } else if (message.type === "ping") {
          const pongMessage: PongMessage = { type: "pong" };
          ws.send(JSON.stringify(pongMessage));
        }
      } catch (error) {
        if (error instanceof SyntaxError) {
          console.log(`Invalid JSON from client ${clientAddr}`);
        } else {
          const errorMessage = `Error handling message from client ${clientAddr}: ${error}`;
          console.log(errorMessage);
          this.logger.writeLog(errorMessage, "error");
        }
      }
    });

    ws.on("close", (code: number, reason: Buffer) => {
      // Use Mac volume control on macOS
      if (process.platform === "darwin") {
        setVolumeMac(50); // Mute volume on disconnect
      } else {
        setVolumeWindows(1); // Mute volume on disconnect
      }

      // Stop ffplay process when client disconnects
      if (this.ffplayProcess && !this.ffplayProcess.killed) {
        this.ffplayProcess.kill();
        this.ffplayProcess = null;
      }

      const disconnectMessage = `Client ${clientAddr} disconnected`;
      console.log(disconnectMessage);
      this.logger.writeLog(disconnectMessage, "info");
      this.currentClient = null;
      const resetMessage = `Client ${clientAddr} has been reset`;
      console.log(resetMessage);
      this.logger.writeLog(resetMessage, "info");
    });

    ws.on("error", (error: Error) => {
      setVolumeWindows(1); // Mute volume on error

      // Stop ffplay process on error
      if (this.ffplayProcess && !this.ffplayProcess.killed) {
        this.ffplayProcess.kill();
        this.ffplayProcess = null;
      }

      const errorMessage = `Error with client ${clientAddr}: ${error}`;
      console.log(errorMessage);
      this.logger.writeLog(errorMessage, "error");
      this.currentClient = null;
      const resetMessage = `Client ${clientAddr} has been reset`;
      console.log(resetMessage);
      this.logger.writeLog(resetMessage, "info");
    });
  }

  private playAudio(audioData: Buffer): void {
    if (audioData.length === 0) {
      const noDataMessage = "No audio data to play";
      console.log(noDataMessage);
      this.logger.writeLog(noDataMessage, "warn");
      return;
    }

    console.log(`Received audio buffer: ${audioData.length} bytes`);

    // Debug: Log audio data statistics
    const audioArray = new Int16Array(
      audioData.buffer,
      audioData.byteOffset,
      audioData.length / 2
    );
    const maxSample = Math.max(...Array.from(audioArray).map(Math.abs));
    const avgSample =
      Array.from(audioArray).reduce((sum, val) => sum + Math.abs(val), 0) /
      audioArray.length;

    console.log(
      `Audio stats - Max: ${maxSample}, Avg: ${avgSample.toFixed(
        2
      )}, Samples: ${audioArray.length}`
    );

    if (maxSample === 0) {
      console.warn("Audio data is silent (all zeros)!");
    } else if (maxSample < 100) {
      console.warn(`Audio data is very quiet (max: ${maxSample})`);
    }

    const expectedSize = CHUNK * 2; // 2 bytes per sample (16-bit)
    const originalSize = audioData.length;
    let processedAudioData = audioData;

    // Adjust audio data size
    if (audioData.length > expectedSize) {
      processedAudioData = audioData.subarray(0, expectedSize);
      console.log(`Trimmed audio data to ${processedAudioData.length} bytes`);
    } else if (audioData.length < expectedSize) {
      const padding = Buffer.alloc(expectedSize - audioData.length);
      processedAudioData = Buffer.concat([audioData, padding]);
      console.log(`Padded audio data to ${processedAudioData.length} bytes`);
    }

    try {
      // Initialize ffplay if not already running
      if (!this.ffplayProcess || this.ffplayProcess.killed) {
        console.log("FFplay not running, initializing...");
        this.initializeFFPlay();
      }

      if (
        this.ffplayProcess &&
        this.ffplayProcess.stdin &&
        !this.ffplayProcess.stdin.destroyed
      ) {
        console.log(
          `Writing ${processedAudioData.length} bytes to FFplay stdin`
        );

        // Check if stdin is writable
        if (!this.ffplayProcess.stdin.writable) {
          console.error("FFplay stdin is not writable!");
          this.logger.writeLog("FFplay stdin is not writable", "error");
          return;
        }

        const writeResult = this.ffplayProcess.stdin.write(processedAudioData);

        // Force flush to reduce buffering delay
        if (this.ffplayProcess.stdin.uncork) {
          this.ffplayProcess.stdin.uncork();
        }

        console.log(`FFplay stdin write result: ${writeResult}`);

        // Log first few bytes of audio data for debugging
        const firstBytes = processedAudioData.subarray(0, 16);
        console.log(
          `First 16 bytes:`,
          Array.from(firstBytes)
            .map((b) => b.toString(16).padStart(2, "0"))
            .join(" ")
        );
      } else {
        const errorMessage = "FFplay process not available or stdin destroyed";
        console.log(errorMessage);
        console.log(`FFplay process status:`, {
          exists: !!this.ffplayProcess,
          killed: this.ffplayProcess?.killed,
          stdinExists: !!this.ffplayProcess?.stdin,
          stdinDestroyed: this.ffplayProcess?.stdin?.destroyed,
          stdinWritable: this.ffplayProcess?.stdin?.writable,
        });
        this.logger.writeLog(errorMessage, "error");

        // Try to reinitialize ffplay
        console.log("Attempting to reinitialize FFplay...");
        this.initializeFFPlay();
      }
    } catch (error) {
      const errorMessage = `Error playing audio via ffplay: ${error}`;
      console.error(errorMessage);
      this.logger.writeLog(errorMessage, "error");
    }
  }

  public async start(): Promise<void> {
    const startMessage = `Simple Audio Server starting at ws://${this.host}:${this.port}`;
    console.log(startMessage);
    this.logger.writeLog(startMessage, "info");

    this.logAudioDevices();

    // Clean old logs when starting
    this.logger.cleanOldLogs();

    try {
      this.server = new WebSocketServer({
        host: this.host,
        port: this.port,
      });

      this.server.on(
        "connection",
        (ws: WebSocket, request: IncomingMessage) => {
          this.handleClient(ws, request);
        }
      );

      this.server.on("error", (error: Error) => {
        console.error("WebSocket server error:", error);
      });

      console.log("Server is ready to accept connections");
      console.log("Waiting for client to connect...");

      // Keep the server running
      return new Promise<void>((resolve, reject) => {
        process.on("SIGINT", () => {
          console.log("\nReceived SIGINT, shutting down gracefully...");
          this.cleanup();
          resolve();
        });

        process.on("SIGTERM", () => {
          console.log("\nReceived SIGTERM, shutting down gracefully...");
          this.cleanup();
          resolve();
        });

        this.server?.on("error", (error: Error) => {
          reject(error);
        });
      });
    } catch (error) {
      console.error("Error starting server:", error);
      this.cleanup();
      throw error;
    }
  }

  public cleanup(): void {
    console.log("Cleaning up...");

    if (this.currentClient) {
      this.currentClient.close();
      this.currentClient = null;
    }

    if (this.server) {
      this.server.close();
      this.server = null;
    }

    if (this.ffplayProcess && !this.ffplayProcess.killed) {
      this.ffplayProcess.kill();
      this.ffplayProcess = null;
    }

    console.log("Cleanup complete.");
  }
}

async function main(): Promise<void> {
  // Use configuration from .env file
  console.log("=== Audio WebSocket Server ===");
  console.log(`Environment: ${isDevelopment() ? "Development" : "Production"}`);
  console.log(`Server: ${serverConfig.host}:${serverConfig.port}`);
  console.log(`Max Connections: ${webSocketConfig.maxConnections}`);
  console.log(`Allowed IPs: ${securityConfig.allowedIps.join(", ")}`);
  console.log("===============================");

  const server = new AudioServer();

  try {
    await server.start();
  } catch (error) {
    if (error instanceof Error && error.message.includes("SIGINT")) {
      console.log("Cancelled, stopping server...");
    } else {
      console.error("Unhandled error:", error);
    }
  } finally {
    server.cleanup();
  }
}

if (require.main === module) {
  console.log("Simple Audio Server");
  console.log("Server will play audio received via WebSocket.");

  main().catch((error) => {
    console.error("Error outside main loop:", error);
    process.exit(1);
  });
}

export { AudioServer };
