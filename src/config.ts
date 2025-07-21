import * as dotenv from "dotenv";
import * as path from "path";

dotenv.config();

export interface ServerConfig {
  server: {
    host: string;
    port: number;
  };
  audio: {
    chunkSize: number;
    channels: number;
    sampleRate: number;
    sampleSize: number;
  };
  logging: {
    directory: string;
    retentionDays: number;
    level: "info" | "warn" | "error" | "debug";
  };
  security: {
    allowedIps: string[];
  };
  websocket: {
    maxConnections: number;
    connectionTimeout: number;
  };
  environment: {
    nodeEnv: "development" | "production" | "test";
    debug: boolean;
  };
}

class ConfigManager {
  private config: ServerConfig;

  constructor() {
    this.config = this.loadConfig();
    this.validateConfig();
  }

  private loadConfig(): ServerConfig {
    return {
      server: {
        host: process.env.SERVER_HOST || "0.0.0.0",
        port: parseInt(process.env.SERVER_PORT || "8765", 10),
      },
      audio: {
        chunkSize: parseInt(process.env.AUDIO_CHUNK_SIZE || "1024", 10),
        channels: parseInt(process.env.AUDIO_CHANNELS || "1", 10),
        sampleRate: parseInt(process.env.AUDIO_SAMPLE_RATE || "44100", 10),
        sampleSize: parseInt(process.env.AUDIO_SAMPLE_SIZE || "16", 10),
      },
      logging: {
        directory: process.env.LOG_DIRECTORY || "logs",
        retentionDays: parseInt(process.env.LOG_RETENTION_DAYS || "7", 10),
        level:
          (process.env.LOG_LEVEL as "info" | "warn" | "error" | "debug") ||
          "info",
      },
      security: {
        allowedIps: process.env.ALLOWED_IPS
          ? process.env.ALLOWED_IPS.split(",").map((ip) => ip.trim())
          : ["127.0.0.1", "::1", "localhost"],
      },
      websocket: {
        maxConnections: parseInt(process.env.MAX_CONNECTIONS || "1", 10),
        connectionTimeout: parseInt(
          process.env.CONNECTION_TIMEOUT || "30000",
          10
        ),
      },
      environment: {
        nodeEnv:
          (process.env.NODE_ENV as "development" | "production" | "test") ||
          "development",
        debug: process.env.DEBUG === "true",
      },
    };
  }

  private validateConfig(): void {
    const errors: string[] = [];

    // Validate server configuration
    if (this.config.server.port < 1 || this.config.server.port > 65535) {
      errors.push("SERVER_PORT must be between 1 and 65535");
    }

    // Validate audio configuration
    if (
      this.config.audio.chunkSize < 64 ||
      this.config.audio.chunkSize > 8192
    ) {
      errors.push("AUDIO_CHUNK_SIZE must be between 64 and 8192");
    }

    if (![1, 2].includes(this.config.audio.channels)) {
      errors.push("AUDIO_CHANNELS must be 1 (mono) or 2 (stereo)");
    }

    if (
      this.config.audio.sampleRate < 8000 ||
      this.config.audio.sampleRate > 192000
    ) {
      errors.push("AUDIO_SAMPLE_RATE must be between 8000 and 192000");
    }

    if (![8, 16, 24, 32].includes(this.config.audio.sampleSize)) {
      errors.push("AUDIO_SAMPLE_SIZE must be 8, 16, 24, or 32");
    }

    // Validate logging configuration
    if (
      this.config.logging.retentionDays < 1 ||
      this.config.logging.retentionDays > 365
    ) {
      errors.push("LOG_RETENTION_DAYS must be between 1 and 365");
    }

    if (
      !["info", "warn", "error", "debug"].includes(this.config.logging.level)
    ) {
      errors.push("LOG_LEVEL must be one of: info, warn, error, debug");
    }

    // Validate security configuration
    if (this.config.security.allowedIps.length === 0) {
      errors.push("ALLOWED_IPS cannot be empty");
    }

    // Validate WebSocket configuration
    if (
      this.config.websocket.maxConnections < 1 ||
      this.config.websocket.maxConnections > 1000
    ) {
      errors.push("MAX_CONNECTIONS must be between 1 and 1000");
    }

    if (
      this.config.websocket.connectionTimeout < 1000 ||
      this.config.websocket.connectionTimeout > 300000
    ) {
      errors.push(
        "CONNECTION_TIMEOUT must be between 1000 and 300000 milliseconds"
      );
    }

    if (errors.length > 0) {
      throw new Error(`Configuration validation failed:\n${errors.join("\n")}`);
    }
  }

  public getConfig(): ServerConfig {
    return { ...this.config }; // Return a copy to prevent modification
  }

  public get(key: keyof ServerConfig): any {
    return this.config[key];
  }

  public getServerConfig() {
    return this.config.server;
  }

  public getAudioConfig() {
    return this.config.audio;
  }

  public getLoggingConfig() {
    return this.config.logging;
  }

  public getSecurityConfig() {
    return this.config.security;
  }

  public getWebSocketConfig() {
    return this.config.websocket;
  }

  public getEnvironmentConfig() {
    return this.config.environment;
  }

  public isDevelopment(): boolean {
    return this.config.environment.nodeEnv === "development";
  }

  public isProduction(): boolean {
    return this.config.environment.nodeEnv === "production";
  }

  public isDebugEnabled(): boolean {
    return this.config.environment.debug;
  }

  public printConfig(): void {
    console.log("=== Server Configuration ===");
    console.log("Server:", this.config.server);
    console.log("Audio:", this.config.audio);
    console.log("Logging:", this.config.logging);
    console.log("Security:", {
      allowedIps: this.config.security.allowedIps.length + " IPs",
    });
    console.log("WebSocket:", this.config.websocket);
    console.log("Environment:", this.config.environment);
    console.log("================================");
  }

  public updateConfig(updates: Partial<ServerConfig>): void {
    this.config = { ...this.config, ...updates };
    this.validateConfig();
  }

  public reloadConfig(): void {
    dotenv.config({ override: true });
    this.config = this.loadConfig();
    this.validateConfig();
  }
}

// Create singleton instance
export const configManager = new ConfigManager();

// Export default configuration
export const config = configManager.getConfig();

// Convenience exports
export const serverConfig = configManager.getServerConfig();
export const audioConfig = configManager.getAudioConfig();
export const loggingConfig = configManager.getLoggingConfig();
export const securityConfig = configManager.getSecurityConfig();
export const webSocketConfig = configManager.getWebSocketConfig();
export const environmentConfig = configManager.getEnvironmentConfig();

// Helper functions
export const isDevelopment = () => configManager.isDevelopment();
export const isProduction = () => configManager.isProduction();
export const isDebugEnabled = () => configManager.isDebugEnabled();
export const printConfig = () => configManager.printConfig();

export default configManager;
