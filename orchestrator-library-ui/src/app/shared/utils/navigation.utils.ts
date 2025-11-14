/**
 * Navigation utilities for breadcrumbs and route management
 * Centralized logic for navigation components
 */

import { BreadcrumbItem, RouteMetadata } from '../types/navigation.types';

/**
 * Default route metadata mapping
 */
const DEFAULT_ROUTE_METADATA: Record<string, RouteMetadata> = {
  overview: {
    breadcrumb: 'overview',
    title: 'Overview',
    icon: 'lucideHome',
  },
  k8s: {
    breadcrumb: 'kubernetes',
    title: 'Kubernetes Dashboard',
    icon: 'lucideServer',
  },
  emdc: {
    breadcrumb: 'emdc',
    title: 'EMDC',
    icon: 'lucideSettings',
    url: null,
  },
  alerts: {
    breadcrumb: 'alerts',
    title: 'Alerts',
    icon: 'lucideAlertTriangle',
  },
  clusters: {
    breadcrumb: 'clusters',
    title: 'Clusters',
    icon: 'lucideServer',
  },
  actions: {
    breadcrumb: 'actions',
    title: 'Actions',
    icon: 'lucideActivity',
  },
  workloads: {
    breadcrumb: 'workloads',
    title: 'Workloads',
    icon: 'lucideActivity',
    url: null,
  },
  request_decisions: {
    breadcrumb: 'request_decisions',
    title: 'Request Decisions',
    icon: 'lucideCheckCircle',
  },
  cog: {
    breadcrumb: 'cog',
    title: 'COG',
    icon: 'lucideCog',
  },
  details: {
    breadcrumb: 'details',
    title: 'Details',
    icon: 'lucideInfo',
  },
  error: {
    breadcrumb: 'error',
    title: 'Error',
    icon: 'lucideAlertCircle',
  },
  'not-found': {
    breadcrumb: '404',
    title: 'Page Not Found',
    icon: 'lucideSearch',
  },
  forbidden: {
    breadcrumb: '403',
    title: 'Forbidden',
    icon: 'lucideShield',
  },
  'server-error': {
    breadcrumb: '500',
    title: 'Server Error',
    icon: 'lucideServer',
  },
};

/**
 * Generate breadcrumbs from URL path
 */
export const generateBreadcrumbs = (
  url: string,
  customMetadata: Record<string, RouteMetadata> = {}
): BreadcrumbItem[] => {
  const segments = url.split('/').filter((segment) => segment.length > 0);
  const breadcrumbs: BreadcrumbItem[] = [];

  if (segments.length === 0) {
    return breadcrumbs;
  }

  // Merge custom metadata with defaults
  const metadata = { ...DEFAULT_ROUTE_METADATA, ...customMetadata };

  let currentPath = '';

  for (let i = 0; i < segments.length; i++) {
    const segment = segments[i];
    currentPath += `/${segment}`;
    const isLastSegment = i === segments.length - 1;

    // Get metadata for this segment
    const routeMetadata = metadata[segment];
    // Create breadcrumb item
    const breadcrumb: BreadcrumbItem = {
      label: routeMetadata?.breadcrumb || formatSegmentLabel(segment),
      url: isLastSegment
        ? null
        : routeMetadata?.url !== undefined
        ? routeMetadata.url
        : currentPath,
      icon: routeMetadata?.icon,
    };

    breadcrumbs.push(breadcrumb);
  }
  return breadcrumbs;
};

/**
 * Format segment label for display
 */
export const formatSegmentLabel = (segment: string): string => {
  // Handle UUIDs and IDs
  if (isUUID(segment)) {
    return `ID: ${segment.substring(0, 8)}...`;
  }

  // Handle underscore and hyphen separated words
  return segment
    .replace(/[_-]/g, ' ')
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

/**
 * Check if string is a UUID
 */
export const isUUID = (str: string): boolean => {
  const uuidRegex =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return uuidRegex.test(str);
};

/**
 * Check if string is a short ID (likely a database ID)
 */
export const isShortId = (str: string): boolean => {
  // Check for common ID patterns (alphanumeric, length > 8)
  return /^[a-z0-9]{8,}$/i.test(str);
};

/**
 * Get page title from breadcrumbs
 */
export const getPageTitle = (breadcrumbs: BreadcrumbItem[]): string => {
  if (breadcrumbs.length === 0) {
    return 'Application';
  }

  const lastBreadcrumb = breadcrumbs[breadcrumbs.length - 1];
  return lastBreadcrumb.label;
};

/**
 * Get parent route from current route
 */
export const getParentRoute = (currentRoute: string): string | null => {
  const segments = currentRoute
    .split('/')
    .filter((segment) => segment.length > 0);

  if (segments.length <= 1) {
    return null;
  }

  segments.pop(); // Remove last segment
  return '/' + segments.join('/');
};

/**
 * Check if route is active
 */
export const isRouteActive = (route: string, currentRoute: string): boolean => {
  if (route === currentRoute) {
    return true;
  }

  // Check if current route starts with the given route (for nested routes)
  return currentRoute.startsWith(route + '/');
};

/**
 * Get route depth (number of segments)
 */
export const getRouteDepth = (route: string): number => {
  return route.split('/').filter((segment) => segment.length > 0).length;
};

/**
 * Extract route parameters from URL
 */
export const extractRouteParams = (route: string): Record<string, string> => {
  const segments = route.split('/').filter((segment) => segment.length > 0);
  const params: Record<string, string> = {};

  // Simple parameter extraction for common patterns
  segments.forEach((segment) => {
    if (isUUID(segment)) {
      params['id'] = segment;
    }
  });

  return params;
};

/**
 * Build route from segments
 */
export const buildRoute = (segments: string[]): string => {
  return '/' + segments.filter((segment) => segment.length > 0).join('/');
};

/**
 * Get route segments from URL
 */
export const getRouteSegments = (url: string): string[] => {
  return url.split('/').filter((segment) => segment.length > 0);
};

/**
 * Check if route requires authentication
 */
export const isProtectedRoute = (route: string): boolean => {
  const publicRoutes = ['/error', '/not-found', '/forbidden', '/server-error'];
  return !publicRoutes.some((publicRoute) => route.startsWith(publicRoute));
};

/**
 * Get route icon from metadata
 */
export const getRouteIcon = (
  segment: string,
  customMetadata: Record<string, RouteMetadata> = {}
): string | undefined => {
  const metadata = { ...DEFAULT_ROUTE_METADATA, ...customMetadata };
  return metadata[segment]?.icon;
};

/**
 * Get route title from metadata
 */
export const getRouteTitle = (
  segment: string,
  customMetadata: Record<string, RouteMetadata> = {}
): string => {
  const metadata = { ...DEFAULT_ROUTE_METADATA, ...customMetadata };
  return metadata[segment]?.title || formatSegmentLabel(segment);
};

/**
 * Validate breadcrumb item
 */
export const isValidBreadcrumbItem = (
  item: unknown
): item is BreadcrumbItem => {
  return (
    typeof item === 'object' &&
    item !== null &&
    'label' in item &&
    'url' in item &&
    typeof (item as BreadcrumbItem).label === 'string'
  );
};

/**
 * Filter out invalid breadcrumb items
 */
export const filterValidBreadcrumbs = (items: unknown[]): BreadcrumbItem[] => {
  return items.filter(isValidBreadcrumbItem);
};

/**
 * Truncate breadcrumbs to maximum length
 */
export const truncateBreadcrumbs = (
  breadcrumbs: BreadcrumbItem[],
  maxItems = 5
): BreadcrumbItem[] => {
  if (breadcrumbs.length <= maxItems) {
    return breadcrumbs;
  }

  // Keep first item, ellipsis, and last items
  const firstItem = breadcrumbs[0];
  const lastItems = breadcrumbs.slice(-(maxItems - 2));

  const ellipsisItem: BreadcrumbItem = {
    label: '...',
    url: null,
    disabled: true,
  };

  return [firstItem, ellipsisItem, ...lastItems];
};
