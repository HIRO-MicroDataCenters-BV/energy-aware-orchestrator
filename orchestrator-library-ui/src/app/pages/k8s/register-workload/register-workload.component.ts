import { CommonModule } from '@angular/common';
import { Component, OnInit, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideTrash2 } from '@ng-icons/lucide';
import { HlmIconDirective } from '@spartan-ng/ui-icon-helm';
import { WorkloadService } from '../../../shared/services/workload.service';
import { NewWorkloadData } from '../../../shared/components/create-new-workload/create-new-workload.component';
import { RegisterWorkloadDialogComponent } from './register-workload-dialog/register-workload-dialog.component';
import { DeleteConfirmationDialogComponent } from './delete-confirmation-dialog/delete-confirmation-dialog.component';
import { WorkloadDetailsDialogComponent } from './workload-details-dialog/workload-details-dialog.component';

@Component({
  selector: 'app-register-workload',
  standalone: true,
  imports: [CommonModule, FormsModule, RegisterWorkloadDialogComponent, DeleteConfirmationDialogComponent, WorkloadDetailsDialogComponent, NgIcon, HlmIconDirective],
  providers: [provideIcons({ lucideTrash2 })],
  templateUrl: './register-workload.component.html',
  styleUrls: ['./register-workload.component.css'],
})
export class RegisterWorkloadComponent implements OnInit {
  @ViewChild('registerDialog') registerDialog!: RegisterWorkloadDialogComponent;
  @ViewChild('deleteDialog') deleteDialog!: DeleteConfirmationDialogComponent;
  @ViewChild('detailsDialog') detailsDialog!: WorkloadDetailsDialogComponent;

  submitting = false;
  successMessage: string | null = null;
  workloads: any[] = [];
  selectedWorkloadId: string | null = null;

  constructor(private readonly workloadService: WorkloadService, private readonly router: Router) {}

  ngOnInit(): void {
    this.loadWorkloadDefinitions();
  }

  private loadWorkloadDefinitions(): void {
    this.workloadService.getWorkloadDefinitions(100, 0).subscribe({
      next: (items) => {
        this.workloads = items || [];
        console.log('📋 Workloads array:', this.workloads);
        console.log('📋 First workload deployment_type:', this.workloads[0]?.deployment_type);
      },
      error: (err) => {
        console.error('❌ Error loading workload definitions:', err);
        this.workloads = [];
      }
    });
  }

  getWorkloadTypeClass(type?: string): string {
    const typeColors: { [key: string]: string } = {
      'Critical': 'text-red-600 bg-red-50',
      'Preferred': 'text-orange-600 bg-orange-50',
      'Optional': 'text-blue-600 bg-blue-50'
    };
    return typeColors[type || ''] || 'text-gray-600 bg-gray-50';
  }

  getDeploymentTypeClass(type?: string | null): string {
    try {
      const deploymentColors: { [key: string]: string } = {
        'kubernetes': 'text-blue-700 bg-blue-100',
        'helm': 'text-purple-700 bg-purple-100',
        'custom': 'text-green-700 bg-green-100'
      };
      const normalizedType = (type || 'kubernetes').toLowerCase();
      return deploymentColors[normalizedType] || 'text-gray-700 bg-gray-100';
    } catch (error) {
      console.error('Error in getDeploymentTypeClass:', error);
      return 'text-gray-700 bg-gray-100';
    }
  }

  openRegisterDialog(): void {
    this.registerDialog.open();
  }

  onWorkloadRegistered(data: NewWorkloadData): void {
    if (!data.name || !data.file) return;
    this.registerDialog.submitting = true;
    this.successMessage = null;

    this.workloadService
      .uploadWorkloadYaml({
        file: data.file,
        name: data.name,
        namespace: data.namespace || 'default',
        workload_type: data.workload_type,
        deployment_type: data.deployment_type,
        description: data.description || '',
        estimated_energy_required: data.estimated_energy_watts,
      })
      .subscribe({
        next: () => {
          this.registerDialog.submitting = false;
          this.successMessage = 'Workload registered successfully.';
          this.registerDialog.close();
          this.loadWorkloadDefinitions();
        },
        error: (err) => {
          this.registerDialog.submitting = false;
          // Show error in dialog only, not on main page
          this.registerDialog.setError(err?.userMessage || 'Failed to register workload. Please try again.');
        }
      });
  }

  deleteWorkload(id: string): void {
    if (!id) return;
    this.selectedWorkloadId = id;
    this.deleteDialog.open();
  }

  onDeleteConfirmed(): void {
    if (!this.selectedWorkloadId) return;

    this.workloadService.deleteWorkloadDefinition(this.selectedWorkloadId).subscribe({
      next: () => {
        this.successMessage = 'Workload definition deleted successfully.';
        this.loadWorkloadDefinitions();
        this.deleteDialog.close();
        this.selectedWorkloadId = null;
      },
      error: (err) => {
        console.error('Failed to delete workload definition:', err);
        this.deleteDialog.setError(err?.error?.detail || err?.detail || 'Failed to delete workload definition. Please try again.');
      }
    });
  }

  onDeleteCancelled(): void {
    this.selectedWorkloadId = null;
  }

  showWorkloadDetails(workload: any): void {
    if (!workload.id) return;

    this.detailsDialog.setLoading(true);
    this.detailsDialog.open(workload);

    this.workloadService.getWorkloadDefinition(workload.id).subscribe({
      next: (details) => {
        this.detailsDialog.setWorkloadDetails(details);
      },
      error: (err) => {
        console.error('Failed to fetch workload details:', err);
        this.detailsDialog.setError('Failed to load workload details. Please try again.');
      }
    });
  }
}


