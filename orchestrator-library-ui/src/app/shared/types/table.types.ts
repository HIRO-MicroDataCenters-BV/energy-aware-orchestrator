/**
 * Table-related types and interfaces
 * Centralized types for table components and related functionality
 */

import { Observable } from 'rxjs';

/**
 * Generic table data interface
 * Can be extended for specific table types
 */
export interface BaseTableData {
  id: string;
  [key: string]: unknown;
}

/**
 * Cluster table data structure
 */
export interface ClusterTableData extends BaseTableData {
  cluster_name: string;
  status: number; // 0-2: 0 - inactive, 1 - running, 2 - success, -1 - warning, -2 - failed
  workloads: number;
  nodes: number;
  cpu_usage: number; // percent
  memory_usage: number; // percent
}

/**
 * Pod table data structure
 */
export interface PodTableData extends BaseTableData {
  pod_name: string;
  namespace: string;
  status: string;
  pod_id: string;
  node_name?: string;
  created_at?: string;
  pod_parent_kind?: string;
}

/**
 * Alert table data structure
 */
export interface AlertTableData extends BaseTableData {
  alert_type: string;
  alert_description: string;
  pod_id: string;
  node_id: string;
  created_at: string;
}

/**
 * Table action definition
 */
export interface TableAction {
  id: string;
  label: string;
  icon: string;
  disabled?: boolean;
  visible?: boolean;
}

/**
 * Table action group definition
 */
export interface TableActionGroup {
  id: string;
  label?: string | null;
  actions: TableAction[];
}

/**
 * Table column definition
 */
export interface TableColumn {
  key: string;
  label: string;
  sortable?: boolean;
  filterable?: boolean;
  width?: string;
  align?: 'left' | 'center' | 'right';
  type?: 'text' | 'number' | 'date' | 'status' | 'progress' | 'badge';
}

/**
 * Table configuration interface
 */
export interface TableConfig {
  columns: TableColumn[];
  actions?: TableAction[];
  actionGroups?: TableActionGroup[];
  tabs?: string[];
  showHeader?: boolean;
  showFooter?: boolean;
  hasRowAction?: boolean;
  pageSize?: number;
  pageSizes?: number[];
}

/**
 * Table data source configuration
 */
export interface TableDataSource<T = BaseTableData> {
  data: Observable<T[]> | T[];
  loading?: boolean;
  error?: string | null;
}

/**
 * Table filter configuration
 */
export interface TableFilter {
  column: string;
  value: unknown;
  operator?:
    | 'equals'
    | 'contains'
    | 'startsWith'
    | 'endsWith'
    | 'greaterThan'
    | 'lessThan';
}

/**
 * Table sort configuration
 */
export interface TableSort {
  column: string;
  direction: 'ASC' | 'DESC';
}

/**
 * Table state interface
 */
export interface TableState {
  filters: TableFilter[];
  sort: TableSort | null;
  pageIndex: number;
  pageSize: number;
  searchQuery?: string;
  selectedTab?: string;
}

/**
 * Column visibility configuration
 */
export interface ColumnVisibility {
  name: string;
  selected: boolean;
}

/**
 * Table row click event data
 */
export interface TableRowClickEvent<T = BaseTableData> {
  row: T;
  index: number;
  column?: string;
}

/**
 * Table action click event data
 */
export interface TableActionClickEvent<T = BaseTableData> {
  action: TableAction;
  row: T;
  index: number;
}

/**
 * Status mapping for consistent status display
 */
export enum TableStatus {
  INACTIVE = 0,
  RUNNING = 1,
  SUCCESS = 2,
  WARNING = -1,
  FAILED = -2,
}

/**
 * Status display configuration
 */
export interface StatusConfig {
  value: string | number;
  label: string;
  color: string;
  bgColor: string;
  icon: string;
}

/**
 * Type guards for table data
 */
export const isClusterTableData = (data: unknown): data is ClusterTableData => {
  return (
    typeof data === 'object' &&
    data !== null &&
    'cluster_name' in data &&
    'status' in data &&
    'id' in data
  );
};

export const isPodTableData = (data: unknown): data is PodTableData => {
  return (
    typeof data === 'object' &&
    data !== null &&
    'pod_name' in data &&
    'namespace' in data &&
    'id' in data
  );
};

export const isAlertTableData = (data: unknown): data is AlertTableData => {
  return (
    typeof data === 'object' &&
    data !== null &&
    'alert_type' in data &&
    'alert_description' in data &&
    'id' in data
  );
};
