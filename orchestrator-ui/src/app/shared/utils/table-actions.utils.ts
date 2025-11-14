/**
 * Table action utilities for handling table actions and menu operations
 * Centralized logic for table action processing
 */

import { TableAction, TableActionGroup } from '../types/table.types';

/**
 * Default action icon mapping
 */
const DEFAULT_ACTION_ICONS: Record<string, string> = {
  view_details: 'lucideInfo',
  view_logs: 'lucideTerminal',
  scale_cluster: 'lucideCog',
  add_nodes: 'lucidePlus',
  cordon_cluster: 'lucidePause',
  drain_cluster: 'lucideDownload',
  delete_cluster: 'lucideTrash2',
  edit: 'lucideEdit',
  copy: 'lucideCopy',
  export: 'lucideDownload',
  import: 'lucideUpload',
  refresh: 'lucideRefresh',
  restart: 'lucideRotateCcw',
  start: 'lucidePlay',
  stop: 'lucideSquare',
  pause: 'lucidePause',
  resume: 'lucidePlay',
  cancel: 'lucideX',
  approve: 'lucideCheck',
  reject: 'lucideX',
  configure: 'lucideSettings',
  monitor: 'lucideActivity',
  backup: 'lucideHardDrive',
  restore: 'lucideUndo',
  migrate: 'lucideMove',
  clone: 'lucideCopy',
  archive: 'lucideArchive',
  unarchive: 'lucideUnarchive',
};

/**
 * Create table action with default properties
 */
export const createTableAction = (
  id: string,
  label: string,
  options: Partial<TableAction> = {}
): TableAction => {
  return {
    id,
    label,
    icon: DEFAULT_ACTION_ICONS[id] || 'lucideMoreHorizontal',
    disabled: false,
    visible: true,
    ...options,
  };
};

/**
 * Create table action group
 */
export const createTableActionGroup = (
  id: string,
  actions: TableAction[],
  label?: string
): TableActionGroup => {
  return {
    id,
    label: label || null,
    actions,
  };
};

/**
 * Filter actions by visibility
 */
export const filterVisibleActions = (actions: TableAction[]): TableAction[] => {
  return actions.filter((action) => action.visible !== false);
};

/**
 * Filter actions by enabled state
 */
export const filterEnabledActions = (actions: TableAction[]): TableAction[] => {
  return actions.filter((action) => action.disabled !== true);
};

/**
 * Get action by ID
 */
export const getActionById = (
  actions: TableAction[],
  id: string
): TableAction | undefined => {
  return actions.find((action) => action.id === id);
};

/**
 * Check if action is available for given context
 */
export const isActionAvailable = (
  action: TableAction,
  context: Record<string, unknown> = {}
): boolean => {
  // Check basic visibility and enabled state
  if (action.visible === false || action.disabled === true) {
    return false;
  }

  // Context-specific availability checks
  const { status, permissions, userRole } = context;

  // Example: delete action only available for non-running items
  if (action.id === 'delete_cluster' && status === 'running') {
    return false;
  }

  // Example: start action only available for stopped items
  if (action.id === 'start' && status === 'running') {
    return false;
  }

  // Example: stop action only available for running items
  if (action.id === 'stop' && status !== 'running') {
    return false;
  }

  // Example: admin-only actions
  const adminOnlyActions = ['delete_cluster', 'migrate', 'backup'];
  if (adminOnlyActions.includes(action.id) && userRole !== 'admin') {
    return false;
  }

  // Permission-based checks
  if (permissions && Array.isArray(permissions)) {
    const requiredPermissions: Record<string, string> = {
      delete_cluster: 'cluster.delete',
      edit: 'cluster.edit',
      configure: 'cluster.configure',
      scale_cluster: 'cluster.scale',
    };

    const requiredPermission = requiredPermissions[action.id];
    if (requiredPermission && !permissions.includes(requiredPermission)) {
      return false;
    }
  }

  return true;
};

/**
 * Get available actions for given context
 */
export const getAvailableActions = (
  actions: TableAction[],
  context: Record<string, unknown> = {}
): TableAction[] => {
  return actions.filter((action) => isActionAvailable(action, context));
};

/**
 * Group actions by category
 */
export const groupActionsByCategory = (
  actions: TableAction[]
): TableActionGroup[] => {
  const groups: Record<string, TableAction[]> = {
    view: [],
    edit: [],
    control: [],
    admin: [],
    other: [],
  };

  const categoryMapping: Record<string, string> = {
    view_details: 'view',
    view_logs: 'view',
    edit: 'edit',
    configure: 'edit',
    start: 'control',
    stop: 'control',
    pause: 'control',
    resume: 'control',
    restart: 'control',
    scale_cluster: 'control',
    add_nodes: 'control',
    cordon_cluster: 'admin',
    drain_cluster: 'admin',
    delete_cluster: 'admin',
    backup: 'admin',
    restore: 'admin',
    migrate: 'admin',
  };

  actions.forEach((action) => {
    const category = categoryMapping[action.id] || 'other';
    groups[category].push(action);
  });

  return Object.entries(groups)
    .filter(([, actions]) => actions.length > 0)
    .map(([category, actions]) => ({
      id: category,
      label: formatCategoryLabel(category),
      actions,
    }));
};

/**
 * Format category label for display
 */
export const formatCategoryLabel = (category: string): string => {
  const labels: Record<string, string> = {
    view: 'View',
    edit: 'Edit',
    control: 'Control',
    admin: 'Administration',
    other: 'Other',
  };

  return (
    labels[category] || category.charAt(0).toUpperCase() + category.slice(1)
  );
};

/**
 * Sort actions by priority
 */
export const sortActionsByPriority = (
  actions: TableAction[]
): TableAction[] => {
  const priorityOrder: Record<string, number> = {
    view_details: 1,
    edit: 2,
    configure: 3,
    start: 4,
    stop: 5,
    pause: 6,
    resume: 7,
    restart: 8,
    scale_cluster: 9,
    add_nodes: 10,
    view_logs: 11,
    backup: 12,
    restore: 13,
    migrate: 14,
    clone: 15,
    export: 16,
    import: 17,
    cordon_cluster: 18,
    drain_cluster: 19,
    delete_cluster: 20,
  };

  return [...actions].sort((a, b) => {
    const priorityA = priorityOrder[a.id] || 999;
    const priorityB = priorityOrder[b.id] || 999;
    return priorityA - priorityB;
  });
};

/**
 * Create standard CRUD actions
 */
export const createCrudActions = (
  options: {
    includeView?: boolean;
    includeEdit?: boolean;
    includeDelete?: boolean;
    includeClone?: boolean;
  } = {}
): TableAction[] => {
  const {
    includeView = true,
    includeEdit = true,
    includeDelete = true,
    includeClone = false,
  } = options;

  const actions: TableAction[] = [];

  if (includeView) {
    actions.push(createTableAction('view_details', 'View Details'));
  }

  if (includeEdit) {
    actions.push(createTableAction('edit', 'Edit'));
  }

  if (includeClone) {
    actions.push(createTableAction('clone', 'Clone'));
  }

  if (includeDelete) {
    actions.push(createTableAction('delete', 'Delete'));
  }

  return actions;
};

/**
 * Create cluster-specific actions
 */
export const createClusterActions = (): TableAction[] => {
  return [
    createTableAction('view_details', 'View Details'),
    createTableAction('view_logs', 'View Logs'),
    createTableAction('scale_cluster', 'Scale Cluster'),
    createTableAction('add_nodes', 'Add Nodes'),
    createTableAction('cordon_cluster', 'Cordon Cluster'),
    createTableAction('drain_cluster', 'Drain Cluster'),
    createTableAction('delete_cluster', 'Delete Cluster'),
  ];
};

/**
 * Create workload-specific actions
 */
export const createWorkloadActions = (): TableAction[] => {
  return [
    createTableAction('view_details', 'View Details'),
    createTableAction('edit', 'Edit'),
    createTableAction('start', 'Start'),
    createTableAction('stop', 'Stop'),
    createTableAction('restart', 'Restart'),
    createTableAction('view_logs', 'View Logs'),
    createTableAction('delete', 'Delete'),
  ];
};

/**
 * Create alert-specific actions
 */
export const createAlertActions = (): TableAction[] => {
  return [
    createTableAction('view_details', 'View Details'),
    createTableAction('acknowledge', 'Acknowledge'),
    createTableAction('resolve', 'Resolve'),
    createTableAction('escalate', 'Escalate'),
    createTableAction('delete', 'Delete'),
  ];
};

/**
 * Validate table action
 */
export const isValidTableAction = (action: unknown): action is TableAction => {
  return (
    typeof action === 'object' &&
    action !== null &&
    'id' in action &&
    'label' in action &&
    'icon' in action &&
    typeof (action as TableAction).id === 'string' &&
    typeof (action as TableAction).label === 'string' &&
    typeof (action as TableAction).icon === 'string'
  );
};

/**
 * Validate table action group
 */
export const isValidTableActionGroup = (
  group: unknown
): group is TableActionGroup => {
  return (
    typeof group === 'object' &&
    group !== null &&
    'id' in group &&
    'actions' in group &&
    typeof (group as TableActionGroup).id === 'string' &&
    Array.isArray((group as TableActionGroup).actions) &&
    (group as TableActionGroup).actions.every(isValidTableAction)
  );
};

/**
 * Get action confirmation message
 */
export const getActionConfirmationMessage = (
  action: TableAction,
  itemName = 'item'
): string | null => {
  const destructiveActions = ['delete', 'delete_cluster', 'drain_cluster'];

  if (destructiveActions.some((id) => action.id.includes(id))) {
    return `Are you sure you want to ${action.label.toLowerCase()} "${itemName}"? This action cannot be undone.`;
  }

  return null;
};

/**
 * Check if action requires confirmation
 */
export const doesActionRequireConfirmation = (action: TableAction): boolean => {
  const confirmationActions = [
    'delete',
    'delete_cluster',
    'drain_cluster',
    'migrate',
  ];
  return confirmationActions.some((id) => action.id.includes(id));
};
