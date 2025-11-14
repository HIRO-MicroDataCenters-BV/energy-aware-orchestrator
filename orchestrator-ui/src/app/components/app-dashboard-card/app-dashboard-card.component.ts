import {
  Component,
  Input,
  OnInit,
  OnDestroy,
  Inject,
  PLATFORM_ID,
} from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideServer, lucideLayers } from '@ng-icons/lucide';
import { DashboardCardModel } from '../../shared/models/dashboard-card.model';
import { AppTableComponent } from '../app-table/app-table.component';
import { AppSpeedometerComponent } from '../app-speedometer/app-speedometer.component';
import { Observable, Subscription } from 'rxjs';
import {
  K8sClusterInfoResponse,
  K8sNode,
  K8sPod,
} from '../../shared/models/kubernetes.model';
import { TranslocoModule } from '@jsverse/transloco';
import {
  LoadingOverlayComponent,
  ErrorOverlayComponent,
} from '../../shared/components';

interface MetricItem {
  icon: string;
  title: string;
  healthy: boolean;
  readyCount: number;
  totalCount: number;
  failedCount?: number;
  statusText: string;
}

@Component({
  selector: 'app-dashboard-card',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    RouterLinkActive,
    AppTableComponent,
    AppSpeedometerComponent,
    TranslocoModule,
    NgIcon,
    LoadingOverlayComponent,
    ErrorOverlayComponent,
  ],
  providers: [provideIcons({ lucideServer, lucideLayers })],
  templateUrl: './app-dashboard-card.component.html',
  styleUrls: ['./app-dashboard-card.component.scss'],
})
export class AppDashboardCardComponent implements OnInit, OnDestroy {
  @Input() data!: DashboardCardModel;

  private subscription = new Subscription();
  clusterInfo: K8sClusterInfoResponse | null = null;
  nodes: K8sNode[] = [];
  pods: K8sPod[] = [];
  isLoading = false;
  hasError = false;
  isBrowser = false;

  constructor(@Inject(PLATFORM_ID) private platformId: object) {
    this.isBrowser = isPlatformBrowser(this.platformId);
  }

  ngOnInit(): void {
    this.loadCardData();
  }

  ngOnDestroy(): void {
    this.subscription.unsubscribe();
  }

  private loadCardData(): void {
    if (!this.data.dataSource) {
      return;
    }

    this.isLoading = true;
    this.hasError = false;

    if (this.data.type === 'metrics' && this.data.key === 'cluster') {
      this.loadClusterMetrics();
    } else if (this.data.type === 'table') {
      this.loadTableData();
    }
  }

  private loadClusterMetrics(): void {
    this.subscription.add(
      (this.data.dataSource as Observable<K8sClusterInfoResponse>).subscribe({
        next: (clusterInfo) => {
          this.clusterInfo = clusterInfo;
          this.nodes = Array.isArray(clusterInfo.nodes)
            ? clusterInfo.nodes
            : [];
          this.pods = Array.isArray(clusterInfo.pods) ? clusterInfo.pods : [];
          this.isLoading = false;
          this.hasError = false;
        },
        error: () => {
          this.clusterInfo = null;
          this.nodes = [];
          this.pods = [];
          this.isLoading = false;
          this.hasError = true;
        },
      })
    );
  }

  private loadTableData(): void {
    this.subscription.add(
      (this.data.dataSource as Observable<unknown[]>).subscribe({
        next: () => {
          this.isLoading = false;
          this.hasError = false;
        },
        error: () => {
          this.isLoading = false;
          this.hasError = true;
        },
      })
    );
  }

  getCpuSpeedometerConfig() {
    return {
      value: this.getMetricValue('cpu'),
      lowThreshold: 30,
      highThreshold: 60,
      min: 0,
      max: 100,
      unit: '%',
      size: 156,
      showLabels: false,
      animate: true,
    };
  }

  getMemorySpeedometerConfig() {
    return {
      value: this.getMetricValue('memory'),
      lowThreshold: 40,
      highThreshold: 70,
      min: 0,
      max: 100,
      unit: '%',
      size: 156,
      showLabels: false,
      animate: true,
    };
  }

  getNodesReady(): number {
    return this.nodes.filter((node) => node.status === 'Ready').length;
  }

  getTotalNodes(): number {
    return this.nodes.length;
  }

  getPodsRunning(): number {
    return this.pods.filter((pod) => pod.phase === 'Running').length;
  }

  getTotalPods(): number {
    return this.pods.length;
  }

  getPodsFailed(): number {
    return this.pods.filter(
      (pod) =>
        pod.phase === 'Failed' ||
        pod.phase === 'Pending' ||
        pod.phase === 'Unknown'
    ).length;
  }

  areNodesHealthy(): boolean {
    const ready = this.getNodesReady();
    const total = this.getTotalNodes();
    return ready === total && total > 0;
  }

  arePodsHealthy(): boolean {
    const total = this.getTotalPods();
    if (total === 0) return false;

    const failed = this.getPodsFailed();
    // If there are any failed pods, consider unhealthy
    if (failed > 0) return false;

    const running = this.getPodsRunning();
    // All pods should be running for healthy status
    return running === total;
  }

  getMetrics(): MetricItem[] {
    return [
      {
        icon: 'lucideServer',
        title: 'card.nodes',
        healthy: this.areNodesHealthy(),
        readyCount: this.getNodesReady(),
        totalCount: this.getTotalNodes(),
        statusText: 'card.ready',
      },
      {
        icon: 'lucideLayers',
        title: 'card.pods',
        healthy: this.arePodsHealthy(),
        readyCount: this.getPodsRunning(),
        totalCount: this.getTotalPods(),
        failedCount: this.getPodsFailed(),
        statusText: 'card.failed',
      },
    ];
  }

  getMetricValue(type: 'cpu' | 'memory'): number {
    if (!this.clusterInfo || this.isLoading || this.hasError) {
      return 0;
    }
    const value =
      type === 'cpu'
        ? this.clusterInfo.cluster_cpu_utilization || 0
        : this.clusterInfo.cluster_memory_utilization || 0;

    return value;
  }

  getTableColumns(): string[] {
    return ['dashboard_status', 'dashboard_info', 'dashboard_date'];
  }

  getTableActions(): string[] {
    return [];
  }

  getTableTabs(): string[] {
    return [];
  }

  getTablePageSize(): number {
    return 50;
  }

  getDataSource(): Observable<unknown[]> | null {
    return this.data.dataSource as Observable<unknown[]> | null;
  }

  retryLoad(): void {
    this.loadCardData();
  }
}
