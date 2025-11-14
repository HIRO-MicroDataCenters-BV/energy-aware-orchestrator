import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { environment } from '../../../environments/environment';

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

export interface LogEntry {
  level: LogLevel;
  message: string;
  timestamp: Date;
  data?: unknown;
  source?: string;
}

@Injectable({
  providedIn: 'root',
})
export class LoggerService {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly isBrowser = isPlatformBrowser(this.platformId);
  private readonly isProduction = environment.production;
  private readonly logLevel: LogLevel = this.isProduction
    ? LogLevel.WARN
    : LogLevel.DEBUG;
  private logs: LogEntry[] = [];
  private readonly maxLogs = 1000;

  debug(message: string, data?: unknown, source?: string): void {
    this.log(LogLevel.DEBUG, message, data, source);
  }

  info(message: string, data?: unknown, source?: string): void {
    this.log(LogLevel.INFO, message, data, source);
  }

  warn(message: string, data?: unknown, source?: string): void {
    this.log(LogLevel.WARN, message, data, source);
  }

  error(message: string, error?: unknown, source?: string): void {
    this.log(LogLevel.ERROR, message, error, source);
  }

  private log(
    level: LogLevel,
    message: string,
    data?: unknown,
    source?: string
  ): void {
    if (level < this.logLevel) {
      return;
    }

    const logEntry: LogEntry = {
      level,
      message,
      timestamp: new Date(),
      data,
      source,
    };

    this.addToLogs(logEntry);
    this.outputToConsole(logEntry);

    if (this.isProduction && level >= LogLevel.ERROR) {
      this.sendToExternalService(logEntry);
    }
  }

  private addToLogs(entry: LogEntry): void {
    this.logs.push(entry);
    if (this.logs.length > this.maxLogs) {
      this.logs.shift();
    }
  }

  private outputToConsole(entry: LogEntry): void {
    if (this.isProduction || !this.isBrowser) {
      return;
    }

    const timestamp = entry.timestamp.toISOString();
    const source = entry.source ? `[${entry.source}]` : '';
    const logMessage = `${timestamp} ${source} ${entry.message}`;

    switch (entry.level) {
      case LogLevel.DEBUG:
        console.debug(logMessage, entry.data);
        break;
      case LogLevel.INFO:
        console.info(logMessage, entry.data);
        break;
      case LogLevel.WARN:
        console.warn(logMessage, entry.data);
        break;
      case LogLevel.ERROR:
        console.error(logMessage, entry.data);
        break;
    }
  }

  private sendToExternalService(entry: LogEntry): void {
    // External logging integration can be added here
    // For now, we'll just acknowledge the entry parameter to avoid warnings
    if (entry && this.isBrowser) {
      // Future: send to external logging service
    }
  }

  getLogs(level?: LogLevel): LogEntry[] {
    if (level !== undefined) {
      return this.logs.filter((log) => log.level >= level);
    }
    return [...this.logs];
  }

  clearLogs(): void {
    this.logs = [];
  }

  downloadLogs(): void {
    if (!this.isBrowser) {
      return;
    }

    const logsJson = JSON.stringify(this.logs, null, 2);
    const blob = new Blob([logsJson], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `app-logs-${new Date().toISOString()}.json`;
    link.click();
    window.URL.revokeObjectURL(url);
  }
}
