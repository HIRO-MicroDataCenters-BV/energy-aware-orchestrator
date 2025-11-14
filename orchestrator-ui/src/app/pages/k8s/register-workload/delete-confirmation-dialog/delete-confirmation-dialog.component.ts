import { Component, EventEmitter, Output, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BrnAlertDialogContentDirective } from '@spartan-ng/brain/alert-dialog';
import { HlmAlertDialogComponent, HlmAlertDialogImports } from '@spartan-ng/ui-alertdialog-helm';
import { HlmButtonDirective } from '@spartan-ng/ui-button-helm';

@Component({
  selector: 'app-delete-confirmation-dialog',
  standalone: true,
  imports: [CommonModule, ...HlmAlertDialogImports, BrnAlertDialogContentDirective, HlmButtonDirective],
  template: `
    <hlm-alert-dialog #dialog="hlmAlertDialog">
      <hlm-alert-dialog-content *brnAlertDialogContent class="max-w-md">
        <hlm-alert-dialog-header>
          <h3 hlmAlertDialogTitle>Delete Workload</h3>
          <p hlmAlertDialogDescription class="mt-1 text-sm text-gray-600">
            Are you sure you want to delete this workload definition? This action cannot be undone.
          </p>
        </hlm-alert-dialog-header>

        <div *ngIf="errorMessage" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <p class="text-sm text-red-800">{{ errorMessage }}</p>
        </div>

        <hlm-alert-dialog-footer class="flex gap-2 justify-end">
          <button hlmBtn variant="outline" (click)="cancel()" class="cursor-pointer">Cancel</button>
          <button hlmBtn variant="destructive" (click)="confirm()" [disabled]="deleting" class="cursor-pointer">
            {{ deleting ? 'Deleting...' : 'Delete' }}
          </button>
        </hlm-alert-dialog-footer>
      </hlm-alert-dialog-content>
    </hlm-alert-dialog>
  `,
})
export class DeleteConfirmationDialogComponent {
  @ViewChild('dialog', { read: HlmAlertDialogComponent }) dialog?: HlmAlertDialogComponent;
  @Output() confirmed = new EventEmitter<void>();
  @Output() cancelled = new EventEmitter<void>();

  deleting = false;
  errorMessage: string | null = null;

  open(): void {
    this.deleting = false;
    this.errorMessage = null;
    this.dialog?.open();
  }

  close(): void {
    this.dialog?.close();
  }

  confirm(): void {
    this.deleting = true;
    this.confirmed.emit();
  }

  cancel(): void {
    this.cancelled.emit();
    this.close();
  }

  setDeleting(deleting: boolean): void {
    this.deleting = deleting;
  }

  setError(errorMessage: string): void {
    this.errorMessage = errorMessage;
    this.deleting = false;
  }
}