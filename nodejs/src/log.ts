import * as fs from "fs";
import * as path from "path";

export class Logger {
  private logDir: string;
  private maxDays: number;

  constructor(logDir: string = "logs", maxDays: number = 7) {
    this.logDir = logDir;
    this.maxDays = maxDays;
    this.ensureLogDirectory();
  }

  private ensureLogDirectory(): void {
    if (!fs.existsSync(this.logDir)) {
      fs.mkdirSync(this.logDir, { recursive: true });
      console.log(`Created log directory: ${this.logDir}`);
    }
  }

  public writeToFile(
    filename: string,
    content: string,
    append: boolean = true
  ): void {
    try {
      const filePath = path.join(this.logDir, filename);
      const timestamp = new Date().toISOString();
      const logEntry = `[${timestamp}] ${content}\n`;

      if (append) {
        fs.appendFileSync(filePath, logEntry, "utf8");
      } else {
        fs.writeFileSync(filePath, logEntry, "utf8");
      }

      console.log(`Log written to: ${filePath}`);
    } catch (error) {
      console.error("Error writing to log file:", error);
    }
  }

  public writeLog(
    content: string,
    level: "info" | "error" | "warn" | "debug" = "info"
  ): void {
    const today = new Date().toISOString().split("T")[0];
    const filename = `${today}.log`;
    const logContent = `[${level.toUpperCase()}] ${content}`;

    this.writeToFile(filename, logContent);
  }

  public cleanOldLogs(): void {
    try {
      const files = fs.readdirSync(this.logDir);
      const now = Date.now();
      const maxAge = this.maxDays * 24 * 60 * 60 * 1000;

      let deletedCount = 0;

      files.forEach((file) => {
        const filePath = path.join(this.logDir, file);
        const stats = fs.statSync(filePath);

        if (stats.isFile()) {
          const fileAge = now - stats.mtime.getTime();

          if (fileAge > maxAge) {
            fs.unlinkSync(filePath);
            console.log(
              `Deleted old log file: ${file} (${Math.floor(
                fileAge / (24 * 60 * 60 * 1000)
              )} days old)`
            );
            deletedCount++;
          }
        }
      });

      if (deletedCount === 0) {
        console.log("No old log files to delete");
      } else {
        console.log(`Cleaned up ${deletedCount} old log file(s)`);
      }
    } catch (error) {
      console.error("Error cleaning old logs:", error);
    }
  }

  public logWithCleanup(
    content: string,
    level: "info" | "error" | "warn" | "debug" = "info"
  ): void {
    this.cleanOldLogs();
    this.writeLog(content, level);
  }

  public getLogFiles(): string[] {
    try {
      const files = fs.readdirSync(this.logDir);
      return files.filter((file) => {
        const filePath = path.join(this.logDir, file);
        return fs.statSync(filePath).isFile();
      });
    } catch (error) {
      console.error("Error getting log files:", error);
      return [];
    }
  }

  public readLogFile(filename: string): string {
    try {
      const filePath = path.join(this.logDir, filename);
      return fs.readFileSync(filePath, "utf8");
    } catch (error) {
      console.error(`Error reading log file ${filename}:`, error);
      return "";
    }
  }

  public getLogStats(): {
    filename: string;
    size: number;
    created: Date;
    modified: Date;
  }[] {
    try {
      const files = this.getLogFiles();
      return files.map((file) => {
        const filePath = path.join(this.logDir, file);
        const stats = fs.statSync(filePath);
        return {
          filename: file,
          size: stats.size,
          created: stats.birthtime,
          modified: stats.mtime,
        };
      });
    } catch (error) {
      console.error("Error getting log stats:", error);
      return [];
    }
  }
}

export const logger = new Logger();

export const writeLog = (
  content: string,
  level: "info" | "error" | "warn" | "debug" = "info"
) => {
  logger.writeLog(content, level);
};

export const writeLogFile = (
  filename: string,
  content: string,
  append: boolean = true
) => {
  logger.writeToFile(filename, content, append);
};

export const cleanLogs = () => {
  logger.cleanOldLogs();
};

export const logWithCleanup = (
  content: string,
  level: "info" | "error" | "warn" | "debug" = "info"
) => {
  logger.logWithCleanup(content, level);
};
