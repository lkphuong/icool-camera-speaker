import * as WebSocket from "ws";
import { Server as WebSocketServer } from "ws";
import { IncomingMessage } from "http";
import Speaker = require("speaker");
import { Logger, writeLog } from "./log";
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
import { setVolumeWindows } from "./utils";

// Audio configuration from environment
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
  private speaker: Speaker | null = null;
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
      this.speaker = new Speaker({
        channels: CHANNELS,
        bitDepth: SAMPLE_SIZE,
        sampleRate: RATE,
      });

      const message = "Audio output initialized successfully";
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
    const speakerInfo = "Using Node.js Speaker module for audio output";
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
    await setVolumeWindows(100); // Set initial volume to 100% on Windows
    //#endregion

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
      setVolumeWindows(0); // Mute volume on disconnect
      const disconnectMessage = `Client ${clientAddr} disconnected`;
      console.log(disconnectMessage);
      this.logger.writeLog(disconnectMessage, "info");
      this.currentClient = null;
      const resetMessage = `Client ${clientAddr} has been reset`;
      console.log(resetMessage);
      this.logger.writeLog(resetMessage, "info");
    });

    ws.on("error", (error: Error) => {
      setVolumeWindows(0); // Mute volume on error
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

    const expectedSize = CHUNK * 2; // 2 bytes per sample (16-bit)
    const originalSize = audioData.length;
    let processedAudioData = audioData;

    // Adjust audio data size
    if (audioData.length > expectedSize) {
      processedAudioData = audioData.subarray(0, expectedSize);
    } else if (audioData.length < expectedSize) {
      const padding = Buffer.alloc(expectedSize - audioData.length);
      processedAudioData = Buffer.concat([audioData, padding]);
    }

    try {
      if (this.speaker && !this.speaker.destroyed) {
        this.speaker.write(processedAudioData);
      } else {
        const errorMessage = "Speaker not available or destroyed";
        console.log(errorMessage);
        this.logger.writeLog(errorMessage, "error");
      }
    } catch (error) {
      const errorMessage = `Error playing audio: ${error}`;
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

    if (this.speaker && !this.speaker.destroyed) {
      this.speaker.end();
      this.speaker = null;
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
