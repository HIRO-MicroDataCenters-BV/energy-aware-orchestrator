/**
 * Navigation-related types and interfaces
 * Centralized types for navigation components and breadcrumbs
 */

/**
 * Breadcrumb item interface
 */
export interface BreadcrumbItem {
  label: string;
  url: string | null;
  icon?: string;
  disabled?: boolean;
}

/**
 * Navigation menu item interface
 */
export interface MenuItem {
  id: string;
  label: string;
  url?: string;
  icon?: string;
  children?: MenuItem[];
  disabled?: boolean;
  visible?: boolean;
  badge?: string | number;
  external?: boolean;
}

/**
 * Navigation configuration
 */
export interface NavigationConfig {
  items: MenuItem[];
  showBreadcrumbs?: boolean;
  showUserMenu?: boolean;
  showLanguageSelector?: boolean;
}

/**
 * Breadcrumb configuration
 */
export interface BreadcrumbConfig {
  items: BreadcrumbItem[];
  separator?: string;
  maxItems?: number;
  showHome?: boolean;
}

/**
 * Route metadata for breadcrumb generation
 */
export interface RouteMetadata {
  breadcrumb?: string;
  title?: string;
  icon?: string;
  hideInBreadcrumbs?: boolean;
  url?: string | null;
}

/**
 * Navigation state interface
 */
export interface NavigationState {
  currentRoute: string;
  breadcrumbs: BreadcrumbItem[];
  activeMenuItem?: string;
}

/**
 * Type guard for menu item
 */
export const isMenuItem = (item: unknown): item is MenuItem => {
  return (
    typeof item === 'object' &&
    item !== null &&
    'id' in item &&
    'label' in item &&
    typeof (item as MenuItem).id === 'string' &&
    typeof (item as MenuItem).label === 'string'
  );
};

/**
 * Type guard for breadcrumb item
 */
export const isBreadcrumbItem = (item: unknown): item is BreadcrumbItem => {
  return (
    typeof item === 'object' &&
    item !== null &&
    'label' in item &&
    'url' in item &&
    typeof (item as BreadcrumbItem).label === 'string'
  );
};
