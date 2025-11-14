import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Output, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { BrnAlertDialogContentDirective } from '@spartan-ng/brain/alert-dialog';
import { HlmAlertDialogComponent, HlmAlertDialogImports } from '@spartan-ng/ui-alertdialog-helm';
import { CreateNewWorkloadComponent, NewWorkloadData } from '../../../../shared/components/create-new-workload/create-new-workload.component';

@Component({
  selector: 'app-register-workload-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, ...HlmAlertDialogImports, BrnAlertDialogContentDirective, CreateNewWorkloadComponent],
  template: `
    <hlm-alert-dialog #dialog="hlmAlertDialog">
      <hlm-alert-dialog-content *brnAlertDialogContent class="max-w-4xl w-full">
        <hlm-alert-dialog-header class="relative">
          <button type="button" (click)="close()" class="absolute top-0 right-0 p-1 text-gray-400 hover:text-gray-600 transition-colors cursor-pointer">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
          <h3 hlmAlertDialogTitle>Register New Workload</h3>
          <p hlmAlertDialogDescription class="mt-1 text-xs text-gray-600">Create and register a new workload definition with YAML manifest.</p>
        </hlm-alert-dialog-header>

        <div class="mt-0">
          <div *ngIf="errorMessage" class="px-3 py-2 rounded text-sm bg-red-50 text-red-800 border border-red-200 mb-3">
            {{ errorMessage }}
          </div>

          <app-create-new-workload
            [showFileUpload]="true"
            [showNamespaceField]="true"
            [submitButtonText]="'Register'"
            [submitting]="submitting"
            (formSubmit)="onWorkloadSubmit($event)"
            (cancel)="close()">
          </app-create-new-workload>
        </div>
      </hlm-alert-dialog-content>
    </hlm-alert-dialog>
  `,
})
export class RegisterWorkloadDialogComponent {
  @ViewChild('dialog', { read: HlmAlertDialogComponent }) dialog?: HlmAlertDialogComponent;
  @Output() workloadRegistered = new EventEmitter<NewWorkloadData>();

  submitting = false;
  errorMessage: string | null = null;

  open(): void {
    this.errorMessage = null; // Clear any previous error messages
    this.dialog?.open();
  }

  close(): void {
    this.errorMessage = null; // Clear error message when closing
    this.dialog?.close();
  }

  setError(message: string): void {
    this.errorMessage = message;
  }

  onWorkloadSubmit(data: NewWorkloadData): void {
    this.submitting = true;
    this.workloadRegistered.emit(data);
    // Note: The parent component will handle the actual submission and set submitting back to false
  }
}
