/**
 * Storage Utilities
 * Safe utilities for working with localStorage in SSR and browser environments
 */

/**
 * Check if localStorage is available
 * @returns True if localStorage is available
 */
export const isLocalStorageAvailable = (): boolean => {
  try {
    return (
      typeof window !== 'undefined' &&
      typeof localStorage !== 'undefined' &&
      localStorage !== null
    );
  } catch {
    return false;
  }
};

/**
 * Safely get item from localStorage
 * @param key Storage key
 * @returns Value from localStorage or null if not available/found
 */
export const getStorageItem = (key: string): string | null => {
  if (!isLocalStorageAvailable()) {
    return null;
  }

  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
};

/**
 * Safely set item in localStorage
 * @param key Storage key
 * @param value Value to store
 * @returns True if successful, false otherwise
 */
export const setStorageItem = (key: string, value: string): boolean => {
  if (!isLocalStorageAvailable()) {
    return false;
  }

  try {
    localStorage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
};

/**
 * Safely remove item from localStorage
 * @param key Storage key
 * @returns True if successful, false otherwise
 */
export const removeStorageItem = (key: string): boolean => {
  if (!isLocalStorageAvailable()) {
    return false;
  }

  try {
    localStorage.removeItem(key);
    return true;
  } catch {
    return false;
  }
};

/**
 * Safely clear all localStorage
 * @returns True if successful, false otherwise
 */
export const clearStorage = (): boolean => {
  if (!isLocalStorageAvailable()) {
    return false;
  }

  try {
    localStorage.clear();
    return true;
  } catch {
    return false;
  }
};

/**
 * Get item from localStorage and parse as JSON
 * @param key Storage key
 * @returns Parsed object or null if not available/invalid JSON
 */
export const getStorageObject = <T = unknown>(key: string): T | null => {
  const item = getStorageItem(key);
  if (!item) {
    return null;
  }

  try {
    return JSON.parse(item) as T;
  } catch {
    return null;
  }
};

/**
 * Set object in localStorage as JSON
 * @param key Storage key
 * @param value Object to store
 * @returns True if successful, false otherwise
 */
export const setStorageObject = (key: string, value: unknown): boolean => {
  try {
    const jsonString = JSON.stringify(value);
    return setStorageItem(key, jsonString);
  } catch {
    return false;
  }
};

/**
 * Check if a key exists in localStorage
 * @param key Storage key
 * @returns True if key exists, false otherwise
 */
export const hasStorageItem = (key: string): boolean => {
  return getStorageItem(key) !== null;
};

/**
 * Get all keys from localStorage
 * @returns Array of all localStorage keys
 */
export const getStorageKeys = (): string[] => {
  if (!isLocalStorageAvailable()) {
    return [];
  }

  try {
    const keys: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key) {
        keys.push(key);
      }
    }
    return keys;
  } catch {
    return [];
  }
};

/**
 * Get localStorage usage info
 * @returns Object with storage usage information
 */
export const getStorageInfo = (): {
  isAvailable: boolean;
  itemCount: number;
  keys: string[];
  estimatedSize: number;
} => {
  const isAvailable = isLocalStorageAvailable();

  if (!isAvailable) {
    return {
      isAvailable: false,
      itemCount: 0,
      keys: [],
      estimatedSize: 0,
    };
  }

  const keys = getStorageKeys();
  let estimatedSize = 0;

  keys.forEach((key) => {
    const value = getStorageItem(key);
    if (value) {
      estimatedSize += key.length + value.length;
    }
  });

  return {
    isAvailable: true,
    itemCount: keys.length,
    keys,
    estimatedSize,
  };
};

/**
 * Token-specific utilities
 */
export const TokenStorage = {
  /**
   * Get access token
   * @param tokenKey Token storage key
   * @returns Access token or null
   */
  getAccessToken: (tokenKey: string): string | null => {
    return getStorageItem(tokenKey);
  },

  /**
   * Set access token
   * @param tokenKey Token storage key
   * @param token Token value
   * @returns True if successful
   */
  setAccessToken: (tokenKey: string, token: string): boolean => {
    return setStorageItem(tokenKey, token);
  },

  /**
   * Clear access token
   * @param tokenKey Token storage key
   * @returns True if successful
   */
  clearAccessToken: (tokenKey: string): boolean => {
    return removeStorageItem(tokenKey);
  },

  /**
   * Check if access token exists
   * @param tokenKey Token storage key
   * @returns True if token exists
   */
  hasAccessToken: (tokenKey: string): boolean => {
    return hasStorageItem(tokenKey);
  },
};

/**
 * Session storage utilities (for data that should not persist across browser sessions)
 */
export const SessionStorage = {
  /**
   * Check if sessionStorage is available
   * @returns True if sessionStorage is available
   */
  isAvailable: (): boolean => {
    try {
      return (
        typeof window !== 'undefined' &&
        typeof sessionStorage !== 'undefined' &&
        sessionStorage !== null
      );
    } catch {
      return false;
    }
  },

  /**
   * Get item from sessionStorage
   * @param key Storage key
   * @returns Value or null
   */
  getItem: (key: string): string | null => {
    if (!SessionStorage.isAvailable()) {
      return null;
    }

    try {
      return sessionStorage.getItem(key);
    } catch {
      return null;
    }
  },

  /**
   * Set item in sessionStorage
   * @param key Storage key
   * @param value Value to store
   * @returns True if successful
   */
  setItem: (key: string, value: string): boolean => {
    if (!SessionStorage.isAvailable()) {
      return false;
    }

    try {
      sessionStorage.setItem(key, value);
      return true;
    } catch {
      return false;
    }
  },

  /**
   * Remove item from sessionStorage
   * @param key Storage key
   * @returns True if successful
   */
  removeItem: (key: string): boolean => {
    if (!SessionStorage.isAvailable()) {
      return false;
    }

    try {
      sessionStorage.removeItem(key);
      return true;
    } catch {
      return false;
    }
  },

  /**
   * Clear all sessionStorage
   * @returns True if successful
   */
  clear: (): boolean => {
    if (!SessionStorage.isAvailable()) {
      return false;
    }

    try {
      sessionStorage.clear();
      return true;
    } catch {
      return false;
    }
  },
};
