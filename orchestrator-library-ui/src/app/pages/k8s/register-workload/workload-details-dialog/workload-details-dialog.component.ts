import { CommonModule } from '@angular/common';
import { Component, ViewChild } from '@angular/core';
import { BrnAlertDialogContentDirective } from '@spartan-ng/brain/alert-dialog';
import { HlmAlertDialogComponent, HlmAlertDialogImports } from '@spartan-ng/ui-alertdialog-helm';
import { HlmButtonDirective } from '@spartan-ng/ui-button-helm';
import { WorkloadDefinitionResponse } from '../../../../shared/interfaces/workload.interface';

@Component({
  selector: 'app-workload-details-dialog',
  standalone: true,
  imports: [CommonModule, ...HlmAlertDialogImports, BrnAlertDialogContentDirective, HlmButtonDirective],
  template: `
    <hlm-alert-dialog #dialog="hlmAlertDialog">
      <hlm-alert-dialog-content *brnAlertDialogContent class="max-w-4xl w-full max-h-[80vh] overflow-auto">
        <hlm-alert-dialog-header class="relative">
          <button type="button" (click)="close()" class="absolute top-0 right-0 p-1 text-gray-400 hover:text-gray-600 transition-colors cursor-pointer">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
          <h3 hlmAlertDialogTitle>Workload Definition Details</h3>
          <p hlmAlertDialogDescription class="mt-1 text-sm text-gray-600">
            Detailed information about the selected workload definition.
          </p>
        </hlm-alert-dialog-header>

        <div class="mt-4 space-y-4" *ngIf="workloadDetails">
          <!-- Basic Information -->
          <div class="bg-gray-50 rounded-lg p-4">
            <h4 class="text-sm font-semibold text-gray-900 mb-3">Basic Information</h4>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              <div>
                <span class="font-medium text-gray-700">Name:</span>
                <span class="ml-2 text-gray-900">{{ workloadDetails.name }}</span>
              </div>
              <div>
                <span class="font-medium text-gray-700">Namespace:</span>
                <span class="ml-2 text-gray-900">{{ workloadDetails.namespace }}</span>
              </div>
              <div>
                <span class="font-medium text-gray-700">Type:</span>
                <span class="ml-2 px-2 py-1 rounded text-xs font-medium" [class]="getWorkloadTypeClass(workloadDetails.workload_type)">
                  {{ workloadDetails.workload_type }}
                </span>
              </div>
              <div>
                <span class="font-medium text-gray-700">Energy Required:</span>
                <span class="ml-2 text-gray-900">{{ workloadDetails.estimated_energy_required || 'N/A' }} W</span>
              </div>
              <div *ngIf="workloadDetails.id">
                <span class="font-medium text-gray-700">ID:</span>
                <span class="ml-2 text-gray-900 font-mono text-xs">{{ workloadDetails.id }}</span>
              </div>
            </div>
          </div>

          <!-- Description -->
          <div *ngIf="workloadDetails.description" class="bg-blue-50 rounded-lg p-4">
            <h4 class="text-sm font-semibold text-gray-900 mb-2">Description</h4>
            <p class="text-sm text-gray-700">{{ workloadDetails.description }}</p>
          </div>

          <!-- YAML Manifest -->
          <div *ngIf="workloadDetails.manifest" class="bg-gray-50 rounded-lg p-4">
            <h4 class="text-sm font-semibold text-gray-900 mb-3">YAML Manifest</h4>
            <div class="bg-gray-900 text-gray-100 rounded p-3 overflow-x-auto">
              <pre class="text-xs whitespace-pre-wrap">{{ workloadDetails.manifest }}</pre>
            </div>
          </div>
        </div>

        <!-- Loading State -->
        <div *ngIf="loading" class="flex items-center justify-center py-8">
          <div class="text-sm text-gray-500">Loading workload details...</div>
        </div>

        <!-- Error State -->
        <div *ngIf="error" class="bg-red-50 border border-red-200 rounded-lg p-4 mt-4">
          <div class="text-sm text-red-800">
            <strong>Error loading workload details:</strong>
            <p class="mt-1">{{ error }}</p>
          </div>
        </div>

        <hlm-alert-dialog-footer class="flex justify-end mt-6">
          <button hlmBtn variant="outline" (click)="close()" class="cursor-pointer">Close</button>
        </hlm-alert-dialog-footer>
      </hlm-alert-dialog-content>
    </hlm-alert-dialog>
  `,
})
export class WorkloadDetailsDialogComponent {
  @ViewChild('dialog', { read: HlmAlertDialogComponent }) dialog?: HlmAlertDialogComponent;

  workloadDetails: WorkloadDefinitionResponse | null = null;
  loading = false;
  error: string | null = null;

  open(workloadDetails: WorkloadDefinitionResponse): void {
    this.workloadDetails = workloadDetails;
    this.loading = false;
    this.error = null;
    this.dialog?.open();
  }

  close(): void {
    this.dialog?.close();
    this.workloadDetails = null;
    this.loading = false;
    this.error = null;
  }

  setLoading(loading: boolean): void {
    this.loading = loading;
  }

  setError(error: string): void {
    this.error = error;
    this.loading = false;
  }

  setWorkloadDetails(details: WorkloadDefinitionResponse): void {
    this.workloadDetails = details;
    this.loading = false;
    this.error = null;
  }

  getWorkloadTypeClass(type?: string): string {
    const typeColors: { [key: string]: string } = {
      'Critical': 'text-red-600 bg-red-50',
      'Preferred': 'text-orange-600 bg-orange-50',
      'Optional': 'text-blue-600 bg-blue-50'
    };
    return typeColors[type || ''] || 'text-gray-600 bg-gray-50';
  }

  formatDate(dateString: string): string {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  }
}