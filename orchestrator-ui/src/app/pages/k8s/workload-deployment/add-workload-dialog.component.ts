import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Output, ViewChild, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { BrnAlertDialogContentDirective } from '@spartan-ng/brain/alert-dialog';
import { HlmAlertDialogComponent, HlmAlertDialogImports } from '@spartan-ng/ui-alertdialog-helm';
import type { WorkloadItem } from './workload-deployment.component';
import { WorkloadService } from '../../../shared/services/workload.service';
import type { WorkloadDefinitionResponse } from '../../../shared/interfaces/workload.interface';
import { CreateNewWorkloadComponent, NewWorkloadData } from '../../../shared/components/create-new-workload/create-new-workload.component';

@Component({
  selector: 'app-add-workload-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, ...HlmAlertDialogImports, BrnAlertDialogContentDirective, CreateNewWorkloadComponent],
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
          <p hlmAlertDialogDescription class="mt-1 text-xs text-gray-600">Choose one: schedule an existing workload definition or create a new one.</p>
        </hlm-alert-dialog-header>

        <div class="max-h-[calc(100vh-200px)] overflow-y-auto pr-2">
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
              <button type="button" (click)="scheduleExisting()" [disabled]="!selectedDefinitionId || schedulingExisting" class="px-2 py-1 text-xs bg-blue-600 text-white rounded cursor-pointer hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed">{{ schedulingExisting ? 'Scheduling...' : 'Schedule selected' }}</button>
            </div>
            <select 
              [(ngModel)]="selectedDefinitionId"
              name="definition"
              class="mt-2 w-full px-2 py-1 border border-blue-200 rounded text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white">
              <option [ngValue]="''">-- None --</option>
              <option *ngFor="let d of workloadDefinitions" [ngValue]="d.id">
                {{ d.name }} ({{ d.namespace }}) — {{ d.workload_type }}
              </option>
            </select>
            <div *ngIf="!workloadDefinitions || workloadDefinitions.length === 0" class="mt-2 text-[11px] text-blue-800">
              No saved workloads found. Use section 2 below to create one.
            </div>
            <div *ngIf="selectedDefinitionId" class="mt-2 text-[11px] text-gray-600">
              <ng-container *ngIf="selectedDefinition as sel">
                <div>
                  Type:
                  <span class="px-1 py-0.5 rounded text-xs font-medium" [class]="getWorkloadTypeClass(sel.workload_type)">
                    {{ sel.workload_type }}
                  </span>
                </div>
                <div>Estimated Energy: <span class="font-medium">{{ sel.estimated_energy_required || '-' }} W</span></div>
                <div>Description: <span class="font-medium">{{ sel.description || '-' }}</span></div>
              </ng-container>
            </div>
          </div>

          <!-- Divider -->
          <div class="flex items-center my-1">
            <div class="flex-1 h-px bg-gray-200"></div>
            <div class="px-2 text-[10px] uppercase tracking-wide text-gray-400">or</div>
            <div class="flex-1 h-px bg-gray-200"></div>
          </div>

          <!-- Section 2: Create new workload to schedule -->
          <div class="border rounded p-3 bg-green-50">
            <div class="text-sm font-semibold text-green-900 mb-2">2) Create new workload</div>
            <app-create-new-workload
              [showFileUpload]="true"
              [showNamespaceField]="true"
              [showSchedulingRules]="false"
              [submitButtonText]="'Schedule new'"
              [submitting]="submitting"
              (formSubmit)="onNewWorkloadSubmit($event)"
              (cancel)="onCancel()">
            </app-create-new-workload>
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
  submitting = false;
  errorNotification: { show: boolean; message: string; details?: any } = {
    show: false,
    message: '',
    details: undefined
  };
  get selectedDefinition(): WorkloadDefinitionResponse | undefined {
    return this.workloadDefinitions.find(d => String(d.id) === String(this.selectedDefinitionId));
  }

  constructor(private readonly workloadService: WorkloadService) {}

  ngOnInit(): void {
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

  onNewWorkloadSubmit(data: NewWorkloadData): void {
    if (data.file) {
      // If file is provided, register the workload definition first
      this.submitting = true;
      this.workloadService
        .uploadWorkloadYaml({
          file: data.file,
          name: data.name,
          namespace: data.namespace || 'default',
          workload_type: data.workload_type,
          description: data.description || '',
          estimated_energy_required: data.estimated_energy_watts,
        })
        .subscribe({
          next: () => {
            this.submitting = false;
            // After successful registration, emit for scheduling
            const workloadPayload: Partial<WorkloadItem> = {
              name: data.name,
              type: data.workload_type as 'Critical' | 'Preferred' | 'Optional',
              energyRequirement: data.estimated_energy_watts || 1000,
              estimatedDuration: 30,
              description: data.description || '',
              cpuCores: 1,
              memoryMB: 512,
            };
            this.submitted.emit(workloadPayload);
            this.resetForm();
            this.close();
          },
          error: (err) => {
            this.submitting = false;
            console.error('Failed to register workload:', err);

            // Handle 409 Conflict - Application already deployed
            if (err?.status === 409 && err?.error?.detail) {
              const detail = err.error.detail;
              const deployedAt = detail.deployed_at ? new Date(detail.deployed_at).toLocaleString() : 'Unknown';

              this.showError(
                `Application '${detail.message?.split("'")[1] || data.name}' is already deployed`,
                {
                  deployment_id: detail.deployment_id,
                  deployed_at: deployedAt,
                  status: detail.status
                }
              );
            } else {
              // Generic error handling
              this.showError(
                err?.error?.message || err?.error?.detail?.message || 'Failed to register workload. Please try again.',
                undefined
              );
            }
          }
        });
    } else {
      // If no file, just schedule the workload directly
      const workloadPayload: Partial<WorkloadItem> = {
        name: data.name,
        type: data.workload_type as 'Critical' | 'Preferred' | 'Optional',
        energyRequirement: data.estimated_energy_watts || 1000,
        estimatedDuration: 30,
        description: data.description || '',
        cpuCores: 1,
        memoryMB: 512,
      };

      this.submitted.emit(workloadPayload);
      this.resetForm();
      this.close();
    }
  }

  onCancel(): void {
    this.resetForm();
    this.close();
  }

  private resetForm(): void {
    this.selectedDefinitionId = '';
    this.hideError();
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

  getWorkloadTypeClass(type?: string): string {
    const typeColors: { [key: string]: string } = {
      'Critical': 'text-red-600 bg-red-50',
      'Preferred': 'text-orange-600 bg-orange-50',
      'Optional': 'text-blue-600 bg-blue-50'
    };
    return typeColors[type || ''] || 'text-gray-600 bg-gray-50';
  }

}


