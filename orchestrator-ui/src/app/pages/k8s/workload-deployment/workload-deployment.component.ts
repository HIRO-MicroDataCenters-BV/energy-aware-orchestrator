import { CommonModule, isPlatformBrowser } from '@angular/common';
import { Component, OnInit, OnDestroy, Inject, PLATFORM_ID, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Subject, takeUntil, interval, forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideTrash2, lucideRefreshCw } from '@ng-icons/lucide';
import { HlmIconDirective } from '@spartan-ng/ui-icon-helm';
import { HlmAlertDialogComponent, HlmAlertDialogImports } from '@spartan-ng/ui-alertdialog-helm';
import { BrnAlertDialogContentDirective } from '@spartan-ng/brain/alert-dialog';
import { AddWorkloadDialogComponent } from './add-workload-dialog.component';
import { WorkloadService } from '../../../shared/services/workload.service';
// The pods API response has fields like phase, node_name, containers, etc.
import { HlmSidebarService } from '../../../../../libs/ui/ui-sidebar-helm/src/lib/hlm-sidebar.service';
import { EnergyAvailabilityService } from '../../../shared/services/energy-availability.service';
import { K8sConnectionTestResponse } from '../../../shared/models/kubernetes.model';
import { HighchartsChartComponent } from 'highcharts-angular';
import * as Highcharts from 'highcharts';

export interface WorkloadItem {
  id: string;
  name: string;
  type: 'Critical' | 'Preferred' | 'Optional';
  status: 'Created' | 'Scheduled' | 'Running' | 'Completed' | 'Failed';
  energyRequirement: number; // watts
  estimatedDuration: number; // minutes
  submittedAt: Date;
  scheduledAt?: Date;
  deadline?: Date;
  escalatedFrom?: 'Preferred' | 'Optional';
  description: string;
  cpuCores: number;
  memoryMB: number;
}

export interface EnergySchedulingRule {
  type: 'Critical' | 'Preferred' | 'Optional';
  scheduleImmediate: boolean;
  escalationTimeHours: number;
  escalatesTo?: 'Critical' | 'Preferred';
  color: string;
  bgColor: string;
  icon: string;
}

@Component({
  selector: 'app-workload-deployment',
  standalone: true,
  imports: [CommonModule, FormsModule, NgIcon, HlmIconDirective, ...HlmAlertDialogImports, BrnAlertDialogContentDirective, AddWorkloadDialogComponent, HighchartsChartComponent],
  providers: [provideIcons({ lucideTrash2, lucideRefreshCw })],
  templateUrl: './workload-deployment.component.html',
  styleUrls: ['./workload-deployment.component.css']
})
export class WorkloadDeploymentComponent implements OnInit, OnDestroy {
  @ViewChild('deleteConfirmDialog', { static: false }) deleteConfirmDialog!: HlmAlertDialogComponent;

  private destroy$ = new Subject<void>();

  workloads: WorkloadItem[] = [];
  deploymentRequests: any[] = [];
  pods: any[] = [];
  appPods: any[] = [];
  expandedApps: Set<string> = new Set();
  availableEnergy = 0;
  totalEnergyDemand = 0;
  energyForecast: any[] = [];
  currentEnergySlot: any = null;
  upcomingEnergySlots: any[] = [];
  chartEnergySlots: any[] = [];
  maxChartEnergy: number = 0;
  isEnergyForecastExpanded: boolean = false;

  // Highcharts
  chartOptions: Highcharts.Options = {};

  k8sConnectionStatus: 'checking' | 'connected' | 'disconnected' = 'checking';
  k8sConnectionMessage = '';
  requestToDelete: any = null;
  deleteNotification: { show: boolean; type: 'success' | 'error'; message: string } = {
    show: false,
    type: 'success',
    message: ''
  };
  isRefreshing = false;
  
  // Scheduling Rules
  schedulingRules: { [key: string]: EnergySchedulingRule } = {
    'Critical': {
      type: 'Critical',
      scheduleImmediate: true,
      escalationTimeHours: 0,
      color: 'text-red-600',
      bgColor: 'bg-red-50 border-red-200',
      icon: '🔥'
    },
    'Preferred': {
      type: 'Preferred',
      scheduleImmediate: false,
      escalationTimeHours: 6,
      escalatesTo: 'Critical',
      color: 'text-orange-600',
      bgColor: 'bg-orange-50 border-orange-200',
      icon: '⭐'
    },
    'Optional': {
      type: 'Optional',
      scheduleImmediate: false,
      escalationTimeHours: 24,
      escalatesTo: 'Preferred',
      color: 'text-blue-600',
      bgColor: 'bg-blue-50 border-blue-200',
      icon: '💡'
    }
  };

  // New workload form
  newWorkload: Partial<WorkloadItem> = {
    name: '',
    type: 'Preferred',
    energyRequirement: 1000,
    estimatedDuration: 30,
    description: '',
    cpuCores: 1,
    memoryMB: 512
  };

  // Using Spartan Alert Dialog instead of manual modal

  constructor(
    @Inject(PLATFORM_ID) private platformId: object,
    public sidebarService: HlmSidebarService,
    private energyService: EnergyAvailabilityService,
    private workloadService: WorkloadService
  ) {}

  ngOnInit(): void {
    if (isPlatformBrowser(this.platformId)) {
      this.checkK8sConnection();
      this.loadEnergyData();
      this.loadScheduledDeployments();
      this.loadDeploymentRequests();
      this.startEscalationCheck();
      this.loadPods();
      this.loadAppPods();
      this.startPeriodicRefresh();
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private checkK8sConnection(): void {
    this.k8sConnectionStatus = 'checking';
    this.k8sConnectionMessage = 'Checking connection...';

    this.workloadService.testKubernetesConnection()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response: K8sConnectionTestResponse) => {
          if (response.status === 'connected') {
            this.k8sConnectionStatus = 'connected';
            const versionInfo = response.version ? ` (v${response.version.gitVersion})` : '';
            this.k8sConnectionMessage = `Connected to ${response.api_server}${versionInfo}`;
          } else {
            this.k8sConnectionStatus = 'disconnected';
            this.k8sConnectionMessage = response.error || 'Unable to connect to Kubernetes cluster';
          }
        },
        error: (error) => {
          console.error('Kubernetes connection test failed:', error);
          this.k8sConnectionStatus = 'disconnected';
          this.k8sConnectionMessage = error?.error?.message || 'Unable to connect to Kubernetes cluster';
        }
      });
  }

  private loadEnergyData(): void {
    this.energyService.getEnergyAvailability(100, true, undefined, undefined, undefined, 48)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          if (response && response.availability) {
            this.energyForecast = response.availability;
            this.processEnergyTimeSlots();
          }
          this.updateScheduling();
        },
        error: (err) => {
          console.error('Error loading energy data:', err);
          // Fallback to mock data
          this.availableEnergy = 2500;
          this.currentEnergySlot = null;
          this.upcomingEnergySlots = [];
          this.chartEnergySlots = [];
          this.updateScheduling();
        }
      });
  }

  private processEnergyTimeSlots(): void {
    if (!this.energyForecast || this.energyForecast.length === 0) {
      this.availableEnergy = 0;
      this.currentEnergySlot = null;
      this.upcomingEnergySlots = [];
      this.chartEnergySlots = [];
      this.maxChartEnergy = 0;
      return;
    }

    const now = new Date();

    // Find current time slot (where now is between slot_start_time and slot_end_time)
    this.currentEnergySlot = this.energyForecast.find(slot => {
      const startTime = new Date(slot.slot_start_time);
      const endTime = new Date(slot.slot_end_time);
      return now >= startTime && now < endTime;
    });

    // If no current slot found, use the first one as fallback
    if (!this.currentEnergySlot && this.energyForecast.length > 0) {
      this.currentEnergySlot = this.energyForecast[0];
    }

    // Set available energy from current slot
    this.availableEnergy = this.currentEnergySlot?.available_watts || 0;

    // Get upcoming slots (next 6 slots after current for card display)
    const currentSlotIndex = this.energyForecast.findIndex(s => s.id === this.currentEnergySlot?.id);
    this.upcomingEnergySlots = this.energyForecast.slice(
      currentSlotIndex >= 0 ? currentSlotIndex + 1 : 0,
      (currentSlotIndex >= 0 ? currentSlotIndex + 1 : 0) + 6
    );

    // Prepare chart data - include current slot + upcoming slots for 24 hours
    // Each slot is 6 hours, so 4 slots = 24 hours
    const startIndex = currentSlotIndex >= 0 ? currentSlotIndex : 0;
    this.chartEnergySlots = this.energyForecast.slice(startIndex, startIndex + 4); // 4 slots = 24 hours

    // Calculate max energy for chart scaling
    this.maxChartEnergy = Math.max(
      ...this.chartEnergySlots.map(slot => slot.potential_maximum_watts || slot.available_watts),
      1000 // Minimum to avoid division by zero
    );

    // Update chart
    this.updateChartOptions();
  }

  private updateChartOptions(): void {
    if (this.chartEnergySlots.length === 0) return;

    const categories = this.chartEnergySlots.map(slot => {
      const start = new Date(slot.slot_start_time);
      return start.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
    });

    const availableData = this.chartEnergySlots.map(slot => ({
      y: slot.available_watts / 1000,
      color: this.getChartBarColor(slot.available_watts)
    }));

    this.chartOptions = {
      chart: {
        type: 'column',
        height: 180,
        backgroundColor: 'transparent',
        spacing: [5, 5, 5, 5]
      },
      title: {
        text: undefined
      },
      credits: {
        enabled: false
      },
      xAxis: {
        categories: categories,
        labels: {
          style: {
            fontSize: '9px'
          }
        },
        lineColor: '#e5e7eb',
        tickColor: '#e5e7eb'
      },
      yAxis: {
        title: {
          text: 'kW',
          style: {
            fontSize: '10px'
          }
        },
        labels: {
          style: {
            fontSize: '9px'
          }
        },
        gridLineColor: '#f3f4f6'
      },
      legend: {
        enabled: true,
        itemStyle: {
          fontSize: '9px'
        },
        margin: 5
      },
      tooltip: {
        shared: true,
        style: {
          fontSize: '10px'
        },
        valueSuffix: ' kW'
      },
      plotOptions: {
        column: {
          borderWidth: 0,
          dataLabels: {
            enabled: false
          }
        }
      },
      series: [
        {
          type: 'column',
          name: 'Available',
          data: availableData,
          tooltip: {
            valueSuffix: ' kW'
          }
        }
      ]
    };
  }

  private loadScheduledDeployments(): void {
    this.workloadService.getScheduledDeployments(100, 0)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (items) => {
          this.workloads = (items || []).map(d => this.mapScheduledToWorkload(d));
          this.calculateTotalEnergyDemand();
        },
        error: () => {
          // fallback: no workloads from backend
          this.workloads = [];
          this.calculateTotalEnergyDemand();
        }
      });
  }

  private loadDeploymentRequests(): void {
    this.workloadService.getDeploymentRequests(100, 0)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (items) => {
          console.log("workload requested", items)
          this.deploymentRequests = items || [];
        },
        error: (err) => {
          console.error('❌ Error loading deployment requests:', err);
          this.deploymentRequests = [];
        }
      });
  }

  private mapScheduledToWorkload(d: any): WorkloadItem {
    const type = (String(d?.workload_type || 'Preferred') as 'Critical' | 'Preferred' | 'Optional');
    const deployedAt = d?.deployed_at ? new Date(d.deployed_at) : undefined;
    const status: WorkloadItem['status'] = deployedAt ? 'Running' : 'Scheduled';

    return {
      id: String(d?.id ?? ''),
      name: String(d?.name ?? 'Unnamed'),
      type: type === 'Critical' || type === 'Preferred' || type === 'Optional' ? type : 'Preferred',
      status,
      energyRequirement: Number(d?.estimated_energy_watts ?? 0),
      estimatedDuration: 60,
      submittedAt: d?.created_at ? new Date(d.created_at) : new Date(),
      scheduledAt: deployedAt,
      description: String(d?.description ?? ''),
      cpuCores: 1,
      memoryMB: 512,
    };
  }

  private startEscalationCheck(): void {
    // Check for escalations every minute
    interval(60000)
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        this.checkForEscalations();
      });
  }

  private startPeriodicRefresh(): void {
    // Refresh all tables every minute
    interval(60000)
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        this.refreshAllData();
      });
  }

  refreshAllData(): void {
    this.isRefreshing = true;

    // Create observables for all API calls
    const energyData$ = this.energyService.getEnergyAvailability(100, true, undefined, undefined, undefined, 48).pipe(
      catchError(() => of(null))
    );
    const scheduledDeployments$ = this.workloadService.getScheduledDeployments(100, 0).pipe(
      catchError(() => of([]))
    );
    const deploymentRequests$ = this.workloadService.getDeploymentRequests(100, 0).pipe(
      catchError(() => of([]))
    );
    const pods$ = this.workloadService.getPods().pipe(
      catchError(() => of({ pods: [] }))
    );
    const appPods$ = this.workloadService.getPodsByApp().pipe(
      catchError(() => of({ apps: [] }))
    );

    // Wait for all requests to complete
    forkJoin({
      energyData: energyData$,
      scheduledDeployments: scheduledDeployments$,
      deploymentRequests: deploymentRequests$,
      pods: pods$,
      appPods: appPods$
    })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (results) => {
          // Update energy data
          if (results.energyData && results.energyData.availability) {
            this.energyForecast = results.energyData.availability;
            this.processEnergyTimeSlots();
          } else {
            // Fallback
            this.availableEnergy = 2500;
            this.currentEnergySlot = null;
            this.upcomingEnergySlots = [];
            this.chartEnergySlots = [];
          }
          this.updateScheduling();

          // Update scheduled deployments
          this.workloads = (results.scheduledDeployments || []).map(d => this.mapScheduledToWorkload(d));
          this.calculateTotalEnergyDemand();

          // Update deployment requests
          this.deploymentRequests = results.deploymentRequests || [];

          // Update pods
          this.pods = results.pods?.pods ?? [];

          // Update app pods
          this.appPods = results.appPods?.apps ?? [];

          // Stop animation
          this.isRefreshing = false;
        },
        error: () => {
          // Stop animation even on error
          this.isRefreshing = false;
        }
      });
  }

  private checkForEscalations(): void {
    const now = new Date();
    let hasChanges = false;

    this.workloads.forEach(workload => {
      if (workload.status === 'Created') {
        const hoursWaiting = (now.getTime() - workload.submittedAt.getTime()) / (1000 * 60 * 60);
        const rule = this.schedulingRules[workload.type];

        if (rule.escalatesTo && hoursWaiting >= rule.escalationTimeHours) {
          workload.escalatedFrom = workload.type as 'Preferred' | 'Optional';
          workload.type = rule.escalatesTo as 'Critical' | 'Preferred' | 'Optional';
          hasChanges = true;
        }
      }
    });

    if (hasChanges) {
      this.updateScheduling();
    }
  }

  private updateScheduling(): void {
    this.calculateTotalEnergyDemand();
    this.scheduleWorkloads();
  }

  private loadPods(): void {
    this.workloadService.getPods()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (res) => {
          this.pods = res?.pods ?? [];
        },
        error: () => {
          this.pods = [];
        }
      });
  }

  private loadAppPods(): void {
    this.workloadService.getPodsByApp()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (res) => {
          this.appPods = res?.apps ?? [];
        },
        error: (err) => {
          console.error('❌ Error loading app pods:', err);
          this.appPods = [];
        }
      });
  }

  private calculateTotalEnergyDemand(): void {
    console.log(this.workloads);
    this.totalEnergyDemand = this.workloads
      .filter(w => w.status === 'Created' || w.status === 'Scheduled' || w.status === 'Running')
      .reduce((sum, w) => sum + w.energyRequirement, 0);
  }

  private scheduleWorkloads(): void {
    // Sort by priority: Critical > Preferred > Optional, then by submission time
    const createdWorkloads = this.workloads
      .filter(w => w.status === 'Created')
      .sort((a, b) => {
        const priorityOrder = { 'Critical': 3, 'Preferred': 2, 'Optional': 1 };
        if (priorityOrder[a.type] !== priorityOrder[b.type]) {
          return priorityOrder[b.type] - priorityOrder[a.type];
        }
        return a.submittedAt.getTime() - b.submittedAt.getTime();
      });

    let availableEnergyForScheduling = this.availableEnergy;

    createdWorkloads.forEach(workload => {
      const rule = this.schedulingRules[workload.type];

      if (rule.scheduleImmediate || availableEnergyForScheduling >= workload.energyRequirement) {
        workload.status = 'Scheduled';
        workload.scheduledAt = new Date();

        if (workload.type === 'Critical') {
          // Critical workloads get scheduled immediately
          workload.scheduledAt = new Date();
        } else {
          // Schedule within appropriate timeframe
          const delayHours = workload.type === 'Preferred' ?
            Math.random() * 6 : Math.random() * 24;
          workload.scheduledAt = new Date(Date.now() + delayHours * 3600000);
        }

        availableEnergyForScheduling -= workload.energyRequirement;
      }
    });
  }

  addWorkload(): void {
    if (this.newWorkload.name && this.newWorkload.type) {
      const workload: WorkloadItem = {
        id: 'w' + Date.now(),
        name: this.newWorkload.name,
        type: this.newWorkload.type as 'Critical' | 'Preferred' | 'Optional',
        status: 'Created',
        energyRequirement: this.newWorkload.energyRequirement || 1000,
        estimatedDuration: this.newWorkload.estimatedDuration || 30,
        submittedAt: new Date(),
        description: this.newWorkload.description || '',
        cpuCores: this.newWorkload.cpuCores || 1,
        memoryMB: this.newWorkload.memoryMB || 512
      };

      this.workloads.push(workload);
      this.updateScheduling();
      this.resetForm();
    }
  }

  onDialogSubmitted(payload: Partial<WorkloadItem>): void {
    this.newWorkload = payload;
    this.addWorkload();
    // Refresh the deployment requests table
    this.loadDeploymentRequests();
  }

  deleteWorkload(workloadId: string): void {
    this.workloads = this.workloads.filter(w => w.id !== workloadId);
    this.updateScheduling();
  }

  openDeleteConfirmDialog(request: any): void {
    this.requestToDelete = request;
    this.deleteConfirmDialog.open();
  }

  confirmDelete(): void {
    if (!this.requestToDelete?.id) return;

    const appName = this.requestToDelete.app_name || 'Deployment request';

    this.workloadService.deleteDeploymentRequest(this.requestToDelete.id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          console.log('✅ Deployment request deleted successfully');
          this.showNotification('success', `"${appName}" deleted successfully`);
          this.loadDeploymentRequests();
          this.requestToDelete = null;
        },
        error: (err) => {
          console.error('❌ Failed to delete deployment request:', err);
          this.showNotification('error', `Failed to delete "${appName}". ${err?.error?.message || 'Please try again.'}`);
          this.requestToDelete = null;
        }
      });
  }

  showNotification(type: 'success' | 'error', message: string): void {
    this.deleteNotification = { show: true, type, message };
    setTimeout(() => {
      this.deleteNotification.show = false;
    }, 5000);
  }

  deleteDeploymentRequest(requestId: string): void {
    if (!requestId) return;

    this.workloadService.deleteDeploymentRequest(requestId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.loadDeploymentRequests();
        },
        error: (err) => {
          console.error('❌ Failed to delete deployment request:', err);
          // You could add a toast notification here
        }
      });
  }

  getWorkloadsByStatus(status: string): WorkloadItem[] {
    return this.workloads.filter(w => w.status === status);
  }

  getCreatedRequests(): any[] {
    return this.deploymentRequests.filter(r =>
      r.status === 'Created'
    );
  }

  getScheduledRequests(): any[] {
    return this.deploymentRequests.filter(r =>
      (r.status === 'Scheduled' || r.status === 'Deployed' )
    );
  }

  getEscalationBadge(workload: WorkloadItem): string {
    if (workload.escalatedFrom) {
      return `Escalated from ${workload.escalatedFrom}`;
    }
    return '';
  }

  getTimeUntilDeadline(workload: WorkloadItem): string {
    if (!workload.deadline) return '';
    
    const now = new Date();
    const diff = workload.deadline.getTime() - now.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    
    if (hours < 0) return 'Overdue';
    if (hours < 1) return 'Due soon';
    return `${hours}h remaining`;
  }

  resetForm(): void {
    this.newWorkload = {
      name: '',
      type: 'Preferred',
      energyRequirement: 1000,
      estimatedDuration: 30,
      description: '',
      cpuCores: 1,
      memoryMB: 512
    };
  }

  getStatusColor(status: string): string {
    const colors: { [key: string]: string } = {
      'Created': 'bg-yellow-100 text-yellow-800',
      'Scheduled': 'bg-blue-100 text-blue-800',
      'Running': 'bg-green-100 text-green-800',
      'Completed': 'bg-gray-100 text-gray-800',
      'Failed': 'bg-red-100 text-red-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  }

  getWorkloadTypeClass(type?: string): string {
    const typeColors: { [key: string]: string } = {
      'Critical': 'text-red-600 bg-red-50',
      'Preferred': 'text-orange-600 bg-orange-50',
      'Optional': 'text-blue-600 bg-blue-50'
    };
    return typeColors[type || ''] || 'text-gray-600 bg-gray-50';
  }

  formatDate(date: Date | undefined): string {
    if (!date) return '-';
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  getEnergyUtilizationPercentage(): number {
    return this.availableEnergy > 0 ? (this.totalEnergyDemand / this.availableEnergy) * 100 : 0;
  }

  getEnergyUsageWatts(): number {
    const runningWorkloads = this.workloads.filter(w => w.status === 'Running');
    return runningWorkloads.reduce((sum, w) => sum + w.energyRequirement, 0);
  }

  getEnergyUsagePercentage(): number {
    return this.availableEnergy > 0 ? (this.getEnergyUsageWatts() / this.availableEnergy) * 100 : 0;
  }

  getRunningPods(): any[] {
    return this.pods.filter(p => (p?.phase || '').toLowerCase() === 'running');
  }

  getPodLabel(pod: any, key: string): string {
    return pod?.labels?.[key] ?? '-';
  }

  getContainerNames(pod: any): string {
    const containers = Array.isArray(pod?.containers) ? pod.containers : [];
    return containers.map((c: any) => c?.name).filter(Boolean).join(', ') || '-';
  }

  getRestartCount(pod: any): number {
    const statuses = Array.isArray(pod?.container_statuses) ? pod.container_statuses : [];
    return statuses.reduce((sum: number, s: any) => sum + (s?.restart_count || 0), 0);
  }

  formatDateString(iso?: string): string {
    if (!iso) return '-';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '-';
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  getUniqueNamespaces(pods: any[]): string[] {
    const namespaces = pods.map(pod => pod.namespace).filter(Boolean);
    return [...new Set(namespaces)];
  }

  getPodStatusColor(status: string): string {
    const colors: { [key: string]: string } = {
      'Running': 'bg-green-100 text-green-800',
      'Pending': 'bg-yellow-100 text-yellow-800',
      'Failed': 'bg-red-100 text-red-800',
      'Succeeded': 'bg-blue-100 text-blue-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  }

  getEarliestStartTime(pods: any[]): string {
    const startTimes = pods.map(pod => pod.start_time).filter(Boolean);
    if (startTimes.length === 0) return '-';
    const earliest = startTimes.sort()[0];
    return earliest;
  }

  toggleAppExpansion(appName: string): void {
    if (this.expandedApps.has(appName)) {
      this.expandedApps.delete(appName);
    } else {
      this.expandedApps.add(appName);
    }
  }

  isAppExpanded(appName: string): boolean {
    return this.expandedApps.has(appName);
  }

  getContainerNamesFromPod(pod: any): string {
    const containers = Array.isArray(pod?.containers) ? pod.containers : [];
    return containers.map((c: any) => c?.name).filter(Boolean).join(', ') || '-';
  }

  getRestartCountFromPod(pod: any): number {
    const statuses = Array.isArray(pod?.container_statuses) ? pod.container_statuses : [];
    return statuses.reduce((sum: number, s: any) => sum + (s?.restart_count || 0), 0);
  }

  // Energy slot display methods
  formatTimeSlot(startTime: string, endTime: string): string {
    const start = new Date(startTime);
    const end = new Date(endTime);

    const formatTime = (date: Date) => {
      return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      });
    };

    const formatDate = (date: Date) => {
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
      });
    };

    // If same day, show: "14:00 - 20:00"
    if (start.toDateString() === end.toDateString()) {
      return `${formatTime(start)} - ${formatTime(end)}`;
    }

    // Different days: "Nov 21 14:00 - Nov 22 20:00"
    return `${formatDate(start)} ${formatTime(start)} - ${formatDate(end)} ${formatTime(end)}`;
  }

  getTimeUntilSlot(startTime: string): string {
    const now = new Date();
    const start = new Date(startTime);
    const diffMs = start.getTime() - now.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

    if (diffHours < 0) return 'Now';
    if (diffHours === 0) return `in ${diffMinutes}m`;
    if (diffHours < 24) return `in ${diffHours}h`;
    const diffDays = Math.floor(diffHours / 24);
    return `in ${diffDays}d`;
  }

  getEnergyLevelClass(watts: number): string {
    if (watts >= 40000) return 'bg-green-100 text-green-800 border-green-300';
    if (watts >= 20000) return 'bg-yellow-100 text-yellow-800 border-yellow-300';
    if (watts >= 5000) return 'bg-orange-100 text-orange-800 border-orange-300';
    return 'bg-red-100 text-red-800 border-red-300';
  }

  getEnergyLevelLabel(watts: number): string {
    if (watts >= 40000) return 'High';
    if (watts >= 20000) return 'Medium';
    if (watts >= 5000) return 'Low';
    return 'Very Low';
  }

  // Chart methods
  getChartBarHeight(watts: number): number {
    if (this.maxChartEnergy === 0) return 0;
    const percentage = (watts / this.maxChartEnergy) * 100;
    // Ensure minimum 5% height for visibility
    return Math.max(percentage, 5);
  }

  getChartBarColor(watts: number): string {
    if (watts >= 40000) return '#22c55e'; // green
    if (watts >= 20000) return '#eab308'; // yellow
    if (watts >= 5000) return '#f97316'; // orange
    return '#ef4444'; // red
  }

  formatChartLabel(startTime: string, endTime?: string): string {
    const startDate = new Date(startTime);
    const now = new Date();

    // Format start time
    const startTimeStr = startDate.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });

    // If different day from now, add date
    if (startDate.toDateString() !== now.toDateString()) {
      const dateStr = startDate.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
      });
      return `${dateStr}\n${startTimeStr}`;
    }

    return startTimeStr;
  }

  isCurrentSlotInChart(slot: any): boolean {
    return this.currentEnergySlot && slot.id === this.currentEnergySlot.id;
  }

  getAverageChartEnergy(): number {
    if (this.chartEnergySlots.length === 0) return 0;
    const total = this.chartEnergySlots.reduce((sum, slot) => sum + slot.available_watts, 0);
    return total / this.chartEnergySlots.length / 1000; // Convert to kW
  }

  getChartBarTimeRange(slot: any): string {
    const startDate = new Date(slot.slot_start_time);
    const endDate = new Date(slot.slot_end_time);

    const formatTime = (date: Date) => {
      return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      });
    };

    return `${formatTime(startDate)} - ${formatTime(endDate)}`;
  }

  toggleEnergyForecast(): void {
    this.isEnergyForecastExpanded = !this.isEnergyForecastExpanded;
  }
}
