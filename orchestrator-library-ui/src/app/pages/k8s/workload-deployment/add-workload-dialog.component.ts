import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Output, ViewChild, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { BrnAlertDialogContentDirective } from '@spartan-ng/brain/alert-dialog';
import { HlmAlertDialogComponent, HlmAlertDialogImports } from '@spartan-ng/ui-alertdialog-helm';
import { HlmDatePickerComponent } from '@spartan-ng/ui-datepicker-helm';
import type { WorkloadItem } from './workload-deployment.component';
import { WorkloadService } from '../../../shared/services/workload.service';
import type { WorkloadDefinitionResponse } from '../../../shared/interfaces/workload.interface';

@Component({
  selector: 'app-add-workload-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, ...HlmAlertDialogImports, BrnAlertDialogContentDirective, HlmDatePickerComponent],
  template: `
    <hlm-alert-dialog #dialog="hlmAlertDialog">
      <hlm-alert-dialog-content *brnAlertDialogContent class="max-w-6xl w-full min-w-[800px]">
        <hlm-alert-dialog-header class="relative">
          <button type="button" (click)="close()" class="absolute top-0 right-0 p-1 text-gray-400 hover:text-gray-600 transition-colors cursor-pointer">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
          <h3 hlmAlertDialogTitle>Schedule Workload</h3>
          <p hlmAlertDialogDescription class="mt-1 text-xs text-gray-600">Schedule an existing workload definition.</p>
        </hlm-alert-dialog-header>

        <div class="max-h-[calc(100vh-200px)] overflow-y-auto pr-2 pb-6">
          <!-- Error Notification -->
          <div *ngIf="errorNotification.show"
               class="bg-red-50 border border-red-300 rounded-lg p-3 mb-3">
            <div class="flex items-start gap-2">
              <span class="text-red-600 text-lg">⚠️</span>
              <div class="flex-1">
                <p class="text-sm font-semibold text-red-800">{{ errorNotification.message }}</p>
                <div *ngIf="errorNotification.details" class="mt-2 text-xs text-red-700 space-y-1">
                  <div><strong>Deployment ID:</strong> {{ errorNotification.details.deployment_id }}</div>
                  <div><strong>Deployed At:</strong> {{ errorNotification.details.deployed_at }}</div>
                  <div><strong>Status:</strong> <span class="px-1.5 py-0.5 bg-red-100 rounded">{{ errorNotification.details.status }}</span></div>
                </div>
                <p class="mt-2 text-xs text-red-600">The application is already running. Please check the deployment table below.</p>
              </div>
              <button (click)="hideError()"
                      class="text-red-400 hover:text-red-600 cursor-pointer text-lg leading-none">
                ×
              </button>
            </div>
          </div>

          <div class="space-y-3 mt-0">
          <!-- Section 1: Select existing workload to schedule -->
          <div class="border rounded p-3 bg-blue-50">
            <div class="flex items-center justify-between mb-1">
              <label class="text-sm font-semibold text-blue-900">1) Select existing workload</label>
              <div class="flex items-center gap-4 text-xs">
                <label class="inline-flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    class="w-4 h-4 border border-gray-400 rounded-sm bg-white accent-blue-600 cursor-pointer"
                    [checked]="scheduleMode === 'now'"
                    (change)="setScheduleMode('now')"
                  />
                  <span>Schedule now</span>
                </label>
                <label class="inline-flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    class="w-4 h-4 border border-gray-400 rounded-sm bg-white accent-blue-600 cursor-pointer"
                    [checked]="scheduleMode === 'later'"
                    (change)="setScheduleMode('later')"
                  />
                  <span>Schedule later</span>
                </label>
              </div>
            </div>
            <select
              [(ngModel)]="selectedDefinitionId"
              name="definition"
              class="mt-2 w-full px-2 py-1 border border-blue-200 rounded text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white">
              <option [ngValue]="''">-- None --</option>
              <option *ngFor="let d of workloadDefinitions" [ngValue]="d.id">
                {{ d.name }} ({{ d.namespace }}) — {{ d.workload_type }}{{ d.deployment_type ? ' — [' + d.deployment_type + ']' : '' }}
              </option>
            </select>
            <div *ngIf="!workloadDefinitions || workloadDefinitions.length === 0" class="mt-2 text-[11px] text-blue-800">
              No saved workloads found.
            </div>
            <div *ngIf="selectedDefinitionId" class="mt-2 text-[11px] text-gray-600">
              <ng-container *ngIf="selectedDefinition as sel">
                <div>
                  Type:
                  <span class="px-1 py-0.5 rounded text-xs font-medium" [class]="getWorkloadTypeClass(sel.workload_type)">
                    {{ sel.workload_type }}
                  </span>
                </div>
                <div *ngIf="sel.deployment_type" class="mt-1">
                  Deployment Type:
                  <span class="px-2 py-0.5 rounded text-xs font-semibold bg-purple-100 text-purple-700 border border-purple-300">
                    {{ sel.deployment_type }}
                  </span>
                </div>
                <div>Estimated Energy: <span class="font-medium">{{ sel.estimated_energy_required || '-' }} W</span></div>
                <div>Description: <span class="font-medium">{{ sel.description || '-' }}</span></div>
              </ng-container>
            </div>
            <!-- Conditional schedule action -->
            <div class="flex justify-end mt-2">
              <button
                *ngIf="scheduleMode === 'now'"
                type="button"
                (click)="scheduleExisting()"
                [disabled]="!selectedDefinitionId || schedulingExisting"
                class="px-2 py-1 text-xs bg-blue-600 text-white rounded cursor-pointer hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {{ schedulingExisting ? 'Scheduling...' : 'Schedule selected now' }}
              </button>
              <button
                *ngIf="scheduleMode === 'later'"
                type="button"
                (click)="scheduleExistingAtTime()"
                [disabled]="!selectedDefinitionId || schedulingExisting || !isExistingScheduleTimeValid()"
                class="px-2 py-1 text-xs bg-blue-600 text-white rounded cursor-pointer hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {{ schedulingExisting ? 'Scheduling...' : 'Schedule at selected time' }}
              </button>
            </div>
            <!-- Schedule later controls -->
            <div class="mt-3" *ngIf="scheduleMode === 'later'">
              <div class="text-[11px] font-semibold text-blue-900 mb-1">Schedule at specific date/time</div>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <hlm-date-picker
                  [(ngModel)]="existingScheduleDateObj"
                  [min]="minDateObj"
                >
                  Pick a date
                </hlm-date-picker>
                <input
                  type="time"
                  [(ngModel)]="existingScheduleTime"
                  class="w-full px-2 py-1 border border-blue-200 rounded text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
                />
              </div>
              <div *ngIf="existingScheduleError" class="mt-1 text-[11px] text-red-600">
                {{ existingScheduleError }}
              </div>
            </div>
          </div>

          <!-- Scheduling Rules Info -->
          <div class="bg-blue-50 rounded border border-blue-200 p-3 mt-3">
            <h4 class="text-xs font-semibold text-blue-900 mb-2">Energy-Aware Workload Scheduling Rules</h4>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs">
              <div class="flex items-center gap-1">
                <div><strong class="text-red-600">Critical:</strong> Immediate</div>
              </div>
              <div class="flex items-center gap-1">
                <div><strong class="text-orange-600">Preferred:</strong> 6h → Critical</div>
              </div>
              <div class="flex items-center gap-1">
                <div><strong class="text-blue-600">Optional:</strong> 24h → Preferred</div>
              </div>
            </div>
          </div>

          </div>
        </div>
      </hlm-alert-dialog-content>
    </hlm-alert-dialog>
  `,
})
export class AddWorkloadDialogComponent implements OnInit {
  @ViewChild('dialog', { read: HlmAlertDialogComponent }) dialog?: HlmAlertDialogComponent;

  @Output() submitted = new EventEmitter<Partial<WorkloadItem>>();

  workloadDefinitions: WorkloadDefinitionResponse[] = [];
  selectedDefinitionId: string = '';
  schedulingExisting = false;
  errorNotification: { show: boolean; message: string; details?: any } = {
    show: false,
    message: '',
    details: undefined
  };
  // Scheduling later controls (existing workload)
  existingScheduleDate: string = '';
  existingScheduleDateObj?: Date;
  existingScheduleTime: string = '';
  existingScheduleError: string = '';
  minDate: string = '';
  minDateObj?: Date;
  scheduleMode: 'now' | 'later' = 'now';
  get selectedDefinition(): WorkloadDefinitionResponse | undefined {
    return this.workloadDefinitions.find(d => String(d.id) === String(this.selectedDefinitionId));
  }

  constructor(private readonly workloadService: WorkloadService) {}

  ngOnInit(): void {
    // Initialize min date and defaults
    const today = new Date();
    this.minDate = today.toISOString().split('T')[0];
    this.minDateObj = new Date(this.minDate + 'T00:00:00');
    this.existingScheduleDate = this.minDate;
    this.existingScheduleDateObj = new Date(this.minDate + 'T00:00:00');
    const defaultTime = new Date(today.getTime() + 60 * 60 * 1000);
    this.existingScheduleTime = defaultTime.toTimeString().slice(0, 5);

    this.workloadService.getWorkloadDefinitions(100, 0).subscribe({
      next: (items) => {
        this.workloadDefinitions = items || [];
      },
      error: () => {
        this.workloadDefinitions = [];
      }
    });
  }

  open(): void {
    this.dialog?.open();
  }

  close(): void {
    this.hideError();
    this.dialog?.close();
  }

  setScheduleMode(mode: 'now' | 'later'): void {
    this.scheduleMode = mode;
  }

  private resetForm(): void {
    this.selectedDefinitionId = '';
    this.hideError();
    this.scheduleMode = 'now';
    this.resetExistingScheduleInputs();
  }

  // Removed auto-populate to keep sections independent

  scheduleExisting(): void {
    const def = this.workloadDefinitions.find(d => String(d.id) === String(this.selectedDefinitionId));
    if (!def || this.schedulingExisting) return;
    this.schedulingExisting = true;
    const body = {
      app_definition_id: def.id,
      estimated_energy_watts: Number(def.estimated_energy_required ?? 0)
    };
    this.workloadService.createScheduledDeployment(body).subscribe({
      next: (created) => {
        this.schedulingExisting = false;
        const mappedType = (created?.workload_type as 'Critical' | 'Preferred' | 'Optional') || 'Preferred';
        const payload: Partial<WorkloadItem> = {
          id: String(created?.id ?? 'w' + Date.now()),
          name: created?.app_name ?? def.name,
          type: mappedType,
          status: 'Scheduled',
          energyRequirement: Number(created?.estimated_energy_watts ?? def.estimated_energy_required ?? 0),
          estimatedDuration: 60,
          submittedAt: new Date(),
          description: created?.app_description ?? def.description ?? '',
          cpuCores: 1,
          memoryMB: 512
        };
        this.submitted.emit(payload);
        this.resetForm();
        this.close();
      },
      error: (err) => {
        this.schedulingExisting = false;

        // Handle 409 Conflict - Application already deployed
        if (err?.status === 409 && err?.error?.detail) {
          const detail = err.error.detail;
          const deployedAt = detail.deployed_at ? new Date(detail.deployed_at).toLocaleString() : 'Unknown';

          this.showError(
            `Application '${detail.message?.split("'")[1] || def.name}' is already deployed`,
            {
              deployment_id: detail.deployment_id,
              deployed_at: deployedAt,
              status: detail.status
            }
          );
        } else {
          // Generic error handling
          this.showError(
            err?.error?.message || err?.error?.detail?.message || 'Failed to schedule deployment. Please try again.',
            undefined
          );
        }
      }
    });
  }

  scheduleExistingAtTime(): void {
    const def = this.workloadDefinitions.find(d => String(d.id) === String(this.selectedDefinitionId));
    if (!def || this.schedulingExisting) return;

    this.existingScheduleError = '';
    if (!this.isExistingScheduleTimeValid()) {
      this.existingScheduleError = 'Please pick a valid future date and time.';
      return;
    }

    const scheduledAtIso = this.getExistingScheduledAtIso();
    if (!scheduledAtIso) {
      this.existingScheduleError = 'Please pick a valid future date and time.';
      return;
    }

    this.schedulingExisting = true;
    const body = {
      app_definition_id: def.id,
      estimated_energy_watts: Number(def.estimated_energy_required ?? 0),
      schedule_at: scheduledAtIso
    };
    this.workloadService.createScheduledDeployment(body).subscribe({
      next: (created) => {
        this.schedulingExisting = false;
        const createdId = String(created?.id || '');
        const mappedType = (created?.workload_type as 'Critical' | 'Preferred' | 'Optional') || 'Preferred';
        const payload: Partial<WorkloadItem> = {
          id: createdId || 'w' + Date.now(),
          name: created?.app_name ?? def.name,
          type: mappedType,
          status: 'Scheduled',
          energyRequirement: Number(created?.estimated_energy_watts ?? def.estimated_energy_required ?? 0),
          estimatedDuration: 60,
          submittedAt: new Date(),
          // reflect chosen schedule time in UI if used downstream
          // @ts-ignore
          scheduledAt: new Date(scheduledAtIso),
          description: created?.app_description ?? def.description ?? '',
          cpuCores: 1,
          memoryMB: 512
        };
        this.submitted.emit(payload);
        this.resetForm();
        this.close();
      },
      error: (err) => {
        this.schedulingExisting = false;
        // Handle 409 Conflict - Application already deployed
        if (err?.status === 409 && err?.error?.detail) {
          const detail = err.error.detail;
          const deployedAt = detail.deployed_at ? new Date(detail.deployed_at).toLocaleString() : 'Unknown';
          this.showError(
            `Application '${detail.message?.split("'")[1] || def.name}' is already deployed`,
            {
              deployment_id: detail.deployment_id,
              deployed_at: deployedAt,
              status: detail.status
            }
          );
        } else {
          // Generic error handling
          this.showError(
            err?.error?.message || err?.error?.detail?.message || 'Failed to create deployment request. Please try again.',
            undefined
          );
        }
      }
    });
  }

  showError(message: string, details?: any): void {
    this.errorNotification = {
      show: true,
      message,
      details
    };

    // Auto-hide after 10 seconds
    setTimeout(() => {
      this.errorNotification.show = false;
    }, 10000);
  }

  hideError(): void {
    this.errorNotification.show = false;
  }

  private resetExistingScheduleInputs(): void {
    const today = new Date();
    this.minDate = today.toISOString().split('T')[0];
    this.minDateObj = new Date(this.minDate + 'T00:00:00');
    this.existingScheduleDate = this.minDate;
    this.existingScheduleDateObj = new Date(this.minDate + 'T00:00:00');
    const defaultTime = new Date(today.getTime() + 60 * 60 * 1000);
    this.existingScheduleTime = defaultTime.toTimeString().slice(0, 5);
    this.existingScheduleError = '';
  }

  isExistingScheduleTimeValid(): boolean {
    if ((!this.existingScheduleDate && !this.existingScheduleDateObj) || !this.existingScheduleTime) return false;
    const datePart = this.existingScheduleDateObj
      ? new Date(this.existingScheduleDateObj.getFullYear(), this.existingScheduleDateObj.getMonth(), this.existingScheduleDateObj.getDate())
      : new Date(`${this.existingScheduleDate}T00:00:00`);
    const [hh, mm] = this.existingScheduleTime.split(':').map(Number);
    const dt = new Date(datePart);
    dt.setHours(hh || 0, mm || 0, 0, 0);
    const now = new Date();
    return !isNaN(dt.getTime()) && dt.getTime() > now.getTime();
  }

  private getExistingScheduledAtIso(): string | null {
    if (!this.isExistingScheduleTimeValid()) return null;
    const datePart = this.existingScheduleDateObj
      ? new Date(this.existingScheduleDateObj.getFullYear(), this.existingScheduleDateObj.getMonth(), this.existingScheduleDateObj.getDate())
      : new Date(`${this.existingScheduleDate}T00:00:00`);
    const [hh, mm] = this.existingScheduleTime.split(':').map(Number);
    const dt = new Date(datePart);
    dt.setHours(hh || 0, mm || 0, 0, 0);
    return this.formatLocalDateTime(dt);
  }

  getWorkloadTypeClass(type?: string): string {
    const typeColors: { [key: string]: string } = {
      'Critical': 'text-red-600 bg-red-50',
      'Preferred': 'text-orange-600 bg-orange-50',
      'Optional': 'text-blue-600 bg-blue-50'
    };
    return typeColors[type || ''] || 'text-gray-600 bg-gray-50';
  }

  private formatLocalDateTime(dt: Date): string {
    const y = dt.getFullYear();
    const m = String(dt.getMonth() + 1).padStart(2, '0');
    const d = String(dt.getDate()).padStart(2, '0');
    const hh = String(dt.getHours()).padStart(2, '0');
    const mm = String(dt.getMinutes()).padStart(2, '0');
    const ss = String(dt.getSeconds()).padStart(2, '0');
    return `${y}-${m}-${d}T${hh}:${mm}:${ss}`;
  }

}


