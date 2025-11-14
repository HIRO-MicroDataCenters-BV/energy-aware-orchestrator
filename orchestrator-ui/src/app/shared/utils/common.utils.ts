import { AbstractControl, ValidationErrors } from '@angular/forms';

export class CommonUtils {
  static isNullOrUndefined(value: unknown): value is null | undefined {
    return value === null || value === undefined;
  }

  static isNullOrEmpty(
    value: string | null | undefined
  ): value is null | undefined | '' {
    return this.isNullOrUndefined(value) || value === '';
  }

  static isNullOrWhitespace(value: string | null | undefined): boolean {
    return this.isNullOrEmpty(value) || value.trim() === '';
  }

  static deepClone<T>(obj: T): T {
    if (obj === null || typeof obj !== 'object') {
      return obj;
    }

    if (obj instanceof Date) {
      return new Date(obj.getTime()) as unknown as T;
    }

    if (obj instanceof Array) {
      return obj.map((item) => this.deepClone(item)) as unknown as T;
    }

    if (typeof obj === 'object') {
      const clonedObj = {} as T;
      for (const key in obj) {
        if (Object.prototype.hasOwnProperty.call(obj, key)) {
          clonedObj[key] = this.deepClone(obj[key]);
        }
      }
      return clonedObj;
    }

    return obj;
  }

  static debounce<T extends (...args: unknown[]) => unknown>(
    func: T,
    delay: number
  ): (...args: Parameters<T>) => void {
    let timeoutId: NodeJS.Timeout;
    return (...args: Parameters<T>) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func(...args), delay);
    };
  }

  static throttle<T extends (...args: unknown[]) => unknown>(
    func: T,
    limit: number
  ): (...args: Parameters<T>) => void {
    let inThrottle: boolean;
    return (...args: Parameters<T>) => {
      if (!inThrottle) {
        func(...args);
        inThrottle = true;
        setTimeout(() => (inThrottle = false), limit);
      }
    };
  }

  static generateUuid(): string {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  static formatBytes(bytes: number, decimals = 2): string {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  }

  static formatNumber(num: number, locale = 'en-US'): string {
    return new Intl.NumberFormat(locale).format(num);
  }

  static capitalize(str: string): string {
    if (this.isNullOrEmpty(str)) return str;
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
  }

  static camelToKebab(str: string): string {
    return str.replace(/([a-z0-9]|(?=[A-Z]))([A-Z])/g, '$1-$2').toLowerCase();
  }

  static kebabToCamel(str: string): string {
    return str.replace(/-([a-z])/g, (g) => g[1].toUpperCase());
  }

  static truncate(str: string, length: number, suffix = '...'): string {
    if (this.isNullOrEmpty(str) || str.length <= length) return str;
    return str.substring(0, length) + suffix;
  }

  static removeDuplicates<T>(array: T[], keyFn?: (item: T) => unknown): T[] {
    if (!keyFn) {
      return [...new Set(array)];
    }

    const seen = new Set();
    return array.filter((item) => {
      const key = keyFn(item);
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
  }

  static groupBy<T, K extends PropertyKey>(
    array: T[],
    keyFn: (item: T) => K
  ): Record<K, T[]> {
    return array.reduce((result, item) => {
      const key = keyFn(item);
      if (!result[key]) {
        result[key] = [];
      }
      result[key].push(item);
      return result;
    }, {} as Record<K, T[]>);
  }

  static flatten<T>(array: (T | T[])[]): T[] {
    return array.reduce((acc: T[], item) => {
      if (Array.isArray(item)) {
        acc.push(...this.flatten(item));
      } else {
        acc.push(item);
      }
      return acc;
    }, [] as T[]);
  }

  static sortBy<T>(
    array: T[],
    ...sortKeys: Array<keyof T | { key: keyof T; direction: 'asc' | 'desc' }>
  ): T[] {
    return [...array].sort((a, b) => {
      for (const sortKey of sortKeys) {
        let key: keyof T;
        let direction: 'asc' | 'desc' = 'asc';

        if (typeof sortKey === 'object') {
          key = sortKey.key;
          direction = sortKey.direction;
        } else {
          key = sortKey;
        }

        const aVal = a[key];
        const bVal = b[key];

        if (aVal < bVal) {
          return direction === 'asc' ? -1 : 1;
        }
        if (aVal > bVal) {
          return direction === 'asc' ? 1 : -1;
        }
      }
      return 0;
    });
  }

  static isEmptyObject(obj: unknown): boolean {
    return obj === null || obj === undefined || Object.keys(obj).length === 0;
  }

  static safeJsonParse<T>(json: string, defaultValue: T): T {
    try {
      return JSON.parse(json);
    } catch {
      return defaultValue;
    }
  }

  static downloadFile(
    data: string | Blob,
    filename: string,
    mimeType = 'text/plain'
  ): void {
    const blob =
      typeof data === 'string' ? new Blob([data], { type: mimeType }) : data;
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  static async copyToClipboard(text: string): Promise<boolean> {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return true;
      } else {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        const success = document.execCommand('copy');
        textArea.remove();
        return success;
      }
    } catch {
      return false;
    }
  }

  static sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  static async retry<T>(
    operation: () => Promise<T>,
    maxAttempts = 3,
    delay = 1000
  ): Promise<T> {
    let lastError: unknown;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error;
        if (attempt < maxAttempts) {
          await this.sleep(delay * Math.pow(2, attempt - 1));
        }
      }
    }

    throw lastError;
  }
}

export class FormUtils {
  static emailValidator(control: AbstractControl): ValidationErrors | null {
    const email = control.value;
    if (!email) return null;

    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return emailRegex.test(email) ? null : { invalidEmail: true };
  }

  static strongPasswordValidator(
    control: AbstractControl
  ): ValidationErrors | null {
    const password = control.value;
    if (!password) return null;

    const errors: ValidationErrors = {};

    if (password.length < 8) {
      errors['minLength'] = true;
    }

    if (!/(?=.*[a-z])/.test(password)) {
      errors['requiresLowercase'] = true;
    }

    if (!/(?=.*[A-Z])/.test(password)) {
      errors['requiresUppercase'] = true;
    }

    if (!/(?=.*\d)/.test(password)) {
      errors['requiresNumber'] = true;
    }

    if (!/(?=.*[@$!%*?&])/.test(password)) {
      errors['requiresSpecialChar'] = true;
    }

    return Object.keys(errors).length > 0 ? errors : null;
  }

  static urlValidator(control: AbstractControl): ValidationErrors | null {
    const url = control.value;
    if (!url) return null;

    try {
      new URL(url);
      return null;
    } catch {
      return { invalidUrl: true };
    }
  }

  static markAllAsTouched(formGroup: {
    controls: Record<string, { markAsTouched: () => void; controls?: unknown }>;
    get: (
      key: string
    ) => { markAsTouched: () => void; controls?: unknown } | null;
  }): void {
    Object.keys(formGroup.controls).forEach((key) => {
      const control = formGroup.get(key);
      control?.markAsTouched();

      if (control?.controls) {
        this.markAllAsTouched(control as unknown as typeof formGroup);
      }
    });
  }

  static getFormErrors(
    formGroup: {
      controls: Record<string, { errors?: unknown; controls?: unknown }>;
      get: (key: string) => { errors?: unknown; controls?: unknown } | null;
    },
    formErrors: Record<string, unknown> = {}
  ): Record<string, unknown> {
    Object.keys(formGroup.controls).forEach((key) => {
      const control = formGroup.get(key);
      const controlErrors = control?.errors;
      if (controlErrors) {
        formErrors[key] = controlErrors;
      }

      if (control?.controls) {
        formErrors[key] = this.getFormErrors(
          control as unknown as typeof formGroup,
          formErrors[key] as Record<string, unknown>
        );
      }
    });

    return formErrors;
  }
}

export class DateUtils {
  static toISOString(date: Date | string | number): string {
    return new Date(date).toISOString();
  }

  static isValidDate(date: unknown): boolean {
    return date instanceof Date && !isNaN(date.getTime());
  }

  static getRelativeTime(date: Date | string | number, locale = 'en'): string {
    const now = new Date();
    const targetDate = new Date(date);
    const diffInSeconds = Math.floor(
      (now.getTime() - targetDate.getTime()) / 1000
    );

    const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });

    const intervals = [
      { label: 'year', seconds: 31536000 },
      { label: 'month', seconds: 2592000 },
      { label: 'day', seconds: 86400 },
      { label: 'hour', seconds: 3600 },
      { label: 'minute', seconds: 60 },
      { label: 'second', seconds: 1 },
    ];

    for (const interval of intervals) {
      const count = Math.floor(diffInSeconds / interval.seconds);
      if (count !== 0) {
        return rtf.format(
          -count,
          interval.label as Intl.RelativeTimeFormatUnit
        );
      }
    }

    return rtf.format(0, 'second');
  }

  static addTime(
    date: Date,
    amount: number,
    unit: 'years' | 'months' | 'days' | 'hours' | 'minutes' | 'seconds'
  ): Date {
    const result = new Date(date);

    switch (unit) {
      case 'years':
        result.setFullYear(result.getFullYear() + amount);
        break;
      case 'months':
        result.setMonth(result.getMonth() + amount);
        break;
      case 'days':
        result.setDate(result.getDate() + amount);
        break;
      case 'hours':
        result.setHours(result.getHours() + amount);
        break;
      case 'minutes':
        result.setMinutes(result.getMinutes() + amount);
        break;
      case 'seconds':
        result.setSeconds(result.getSeconds() + amount);
        break;
    }

    return result;
  }
}
