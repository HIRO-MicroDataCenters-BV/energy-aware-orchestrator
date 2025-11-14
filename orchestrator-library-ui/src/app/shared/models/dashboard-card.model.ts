import { Observable } from 'rxjs';
import { K8sClusterInfoResponse } from './kubernetes.model';

export interface DashboardCardModel {
  key: string;
  title: string;
  type: 'metrics' | 'table';
  dataSource:
    | Observable<unknown[]>
    | Observable<K8sClusterInfoResponse>
    | K8sClusterInfoResponse
    | null;
  actions?: {
    label: string;
    icon?: string;
    link: string;
  }[];
}
