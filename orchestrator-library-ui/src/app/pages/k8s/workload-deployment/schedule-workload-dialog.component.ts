import { Component, EventEmitter, Output, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HlmAlertDialogComponent, HlmAlertDialogImports } from '@spartan-ng/ui-alertdialog-helm';
import { BrnAlertDialogContentDirective } from '@spartan-ng/brain/alert-dialog';

@Component({
  selector: 'app-schedule-workload-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, ...HlmAlertDialogImports, BrnAlertDialogContentDirective],
  template: `
    <hlm-alert-dialog #dialog>
      <hlm-alert-dialog-content *brnAlertDialogContent="let ctx" class="sm:max-w-[500px]">
        <hlm-alert-dialog-header>
          <h3 hlmAlertDialogTitle>Schedule Workload</h3>
          <p hlmAlertDialogDescription>
            Set the date and time when this workload should be scheduled for deployment.
          </p>
        </hlm-alert-dialog-header>

        <div class="space-y-4 py-4">
          <!-- Workload Info -->
          <div class="bg-gray-50 rounded-lg p-3 border">
            <div class="text-sm font-semibold text-gray-700">{{workloadName}}</div>
            <div class="text-xs text-gray-500 mt-1">{{workloadDescription}}</div>
          </div>

          <!-- Date Input -->
          <div class="space-y-2">
            <label class="text-sm font-medium text-gray-700">
              Schedule Date
              <span class="text-red-500">*</span>
            </label>
            <input
              type="date"
              [(ngModel)]="scheduledDate"
              [min]="minDate"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              required
            />
            <p class="text-xs text-gray-500">Select the date for deployment</p>
          </div>

          <!-- Time Input -->
          <div class="space-y-2">
            <label class="text-sm font-medium text-gray-700">
              Schedule Time
              <span class="text-red-500">*</span>
            </label>
            <input
              type="time"
              [(ngModel)]="scheduledTime"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              required
            />
            <p class="text-xs text-gray-500">Select the time for deployment</p>
          </div>

          <!-- Preview -->
          <div class="bg-blue-50 border border-blue-200 rounded-lg p-3" *ngIf="scheduledDate && scheduledTime">
            <div class="text-xs font-semibold text-blue-900 mb-1">Scheduled For:</div>
            <div class="text-sm text-blue-800">
              {{getFormattedDateTime()}}
            </div>
          </div>

          <!-- Error Message -->
          <div class="bg-red-50 border border-red-200 rounded-lg p-3" *ngIf="errorMessage">
            <div class="flex items-start gap-2">
              <span class="text-red-600">⚠</span>
              <div class="text-sm text-red-700">{{errorMessage}}</div>
            </div>
          </div>
        </div>

        <hlm-alert-dialog-footer>
          <button
            hlmAlertDialogCancel
            (click)="ctx.close(); resetForm()"
            class="cursor-pointer"
            type="button"
          >
            Cancel
          </button>
          <button
            hlmAlertDialogAction
            (click)="onSchedule(ctx)"
            [disabled]="!isFormValid()"
            class="cursor-pointer"
            [class.opacity-50]="!isFormValid()"
            [class.cursor-not-allowed]="!isFormValid()"
            type="button"
          >
            Schedule
          </button>
        </hlm-alert-dialog-footer>
      </hlm-alert-dialog-content>
    </hlm-alert-dialog>
  `,
})
export class ScheduleWorkloadDialogComponent {
  @ViewChild('dialog') dialog!: HlmAlertDialogComponent;
  @Output() scheduled = new EventEmitter<{ scheduledAt: string }>();

  workloadId: string = '';
  workloadName: string = '';
  workloadDescription: string = '';
  scheduledDate: string = '';
  scheduledTime: string = '';
  minDate: string = '';
  errorMessage: string = '';

  constructor() {
    // Set minimum date to today
    const today = new Date();
    this.minDate = today.toISOString().split('T')[0];

    // Set default date to today
    this.scheduledDate = this.minDate;

    // Set default time to current time + 1 hour
    const defaultTime = new Date(today.getTime() + 60 * 60 * 1000);
    this.scheduledTime = defaultTime.toTimeString().slice(0, 5);
  }

  open(workload: any): void {
    this.workloadId = workload.id;
    this.workloadName = workload.app_name || 'Unnamed Workload';
    this.workloadDescription = workload.app_description || workload.description || '';
    this.errorMessage = '';

    // Reset to defaults
    const today = new Date();
    this.scheduledDate = today.toISOString().split('T')[0];
    const defaultTime = new Date(today.getTime() + 60 * 60 * 1000);
    this.scheduledTime = defaultTime.toTimeString().slice(0, 5);

    this.dialog.open();
  }

  onSchedule(ctx: any): void {
    if (!this.isFormValid()) {
      this.errorMessage = 'Please select both date and time';
      return;
    }

    // Validate that the scheduled time is not in the past
    const scheduledDateTime = new Date(`${this.scheduledDate}T${this.scheduledTime}`);
    const now = new Date();

    if (scheduledDateTime < now) {
      this.errorMessage = 'Scheduled time cannot be in the past';
      return;
    }

    // Create ISO string for the scheduled time
    const scheduledAt = scheduledDateTime.toISOString();

    // Emit the scheduled event
    this.scheduled.emit({ scheduledAt });

    // Close dialog and reset
    ctx.close();
    this.resetForm();
  }

  isFormValid(): boolean {
    return !!this.scheduledDate && !!this.scheduledTime;
  }

  getFormattedDateTime(): string {
    if (!this.scheduledDate || !this.scheduledTime) return '';

    const dateTime = new Date(`${this.scheduledDate}T${this.scheduledTime}`);
    return dateTime.toLocaleString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  }

  resetForm(): void {
    this.workloadId = '';
    this.workloadName = '';
    this.workloadDescription = '';
    this.errorMessage = '';

    // Reset to defaults
    const today = new Date();
    this.scheduledDate = today.toISOString().split('T')[0];
    const defaultTime = new Date(today.getTime() + 60 * 60 * 1000);
    this.scheduledTime = defaultTime.toTimeString().slice(0, 5);
  }
}
