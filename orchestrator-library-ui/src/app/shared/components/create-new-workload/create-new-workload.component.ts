import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';

export interface NewWorkloadData {
  name: string;
  workload_type: string;
  deployment_type: string;
  estimated_energy_watts?: number;
  namespace?: string;
  description?: string;
  file?: File;
}

@Component({
  selector: 'app-create-new-workload',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './create-new-workload.component.html',
  styleUrls: ['./create-new-workload.component.css'],
})
export class CreateNewWorkloadComponent {
  @Input() showFileUpload = true;
  @Input() showNamespaceField = true;
  @Input() showSchedulingRules = true;
  @Input() submitButtonText = 'Create';
  @Input() submitting = false;
  @Output() formSubmit = new EventEmitter<NewWorkloadData>();
  @Output() cancel = new EventEmitter<void>();

  form: any = {
    name: '',
    workload_type: 'Preferred',
    deployment_type: 'kubernetes',
    estimated_energy_watts: undefined,
    namespace: 'default',
    description: '',
  };

  selectedFile: File | null = null;
  isDragOver = false;

  getWorkloadTypeClass(type?: string): string {
    const typeColors: { [key: string]: string } = {
      'Critical': 'text-red-600 bg-red-50',
      'Preferred': 'text-orange-600 bg-orange-50',
      'Optional': 'text-blue-600 bg-blue-50'
    };
    return typeColors[type || ''] || 'text-gray-600 bg-gray-50';
  }

  onFileChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input?.files && input.files.length > 0) {
      this.selectedFile = input.files[0];
    }
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver = true;
  }

  onDragLeave(): void {
    this.isDragOver = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver = false;
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      const file = files[0];
      const name = (file?.name || '').toLowerCase();
      if (name.endsWith('.yml') || name.endsWith('.yaml')) {
        this.selectedFile = file;
      }
    }
  }

  clearFile(): void {
    this.selectedFile = null;
  }

  isFormValid(): boolean {
    const nameValid = typeof this.form?.name === 'string' && this.form.name.trim().length > 0;
    const namespaceValid = !this.showNamespaceField || (typeof this.form?.namespace === 'string' && this.form.namespace.trim().length > 0);
    const typeValid = ['Critical', 'Preferred', 'Optional'].includes(this.form?.workload_type);
    const fileValid = !this.showFileUpload || (!!this.selectedFile && /\.(ya?ml)$/i.test(this.selectedFile.name || ''));
    const energy = this.form?.estimated_energy_watts;
    const energyValid = energy === undefined || energy === null || (typeof energy === 'number' && energy > 0);

    return nameValid && namespaceValid && typeValid && fileValid && energyValid;
  }

  onSubmit(): void {
    if (!this.isFormValid()) return;

    const data: NewWorkloadData = {
      name: this.form.name,
      workload_type: this.form.workload_type,
      deployment_type: this.form.deployment_type,
      estimated_energy_watts: this.form.estimated_energy_watts,
      description: this.form.description,
    };

    if (this.showNamespaceField) {
      data.namespace = this.form.namespace;
    }

    if (this.showFileUpload && this.selectedFile) {
      data.file = this.selectedFile;
    }

    this.formSubmit.emit(data);
  }

  onCancel(): void {
    this.cancel.emit();
  }

  resetForm(): void {
    this.form = {
      name: '',
      workload_type: 'Preferred',
      deployment_type: 'kubernetes',
      estimated_energy_watts: undefined,
      namespace: 'default',
      description: '',
    };
    this.selectedFile = null;
  }

  getDeploymentIcon(): string {
    const icons: { [key: string]: string } = {
      'Critical': '🚀',
      'Preferred': '⏰',
      'Optional': '📅'
    };
    return icons[this.form.workload_type] || '📅';
  }

  getDeploymentTitle(): string {
    const titles: { [key: string]: string } = {
      'Critical': 'Deploy Immediately',
      'Preferred': 'Deploy within 6 hours',
      'Optional': 'Deploy within 24 hours'
    };
    return titles[this.form.workload_type] || 'Deploy when ready';
  }

  getDeploymentDescription(): string {
    const descriptions: { [key: string]: string } = {
      'Critical': 'This workload will be scheduled immediately, regardless of energy availability. Critical workloads have the highest priority in the system.',
      'Preferred': 'This workload will be scheduled within 6 hours based on energy availability. If not deployed within 6 hours, it will be escalated to Critical priority.',
      'Optional': 'This workload will be scheduled within 24 hours when energy is available. If not deployed within 24 hours, it will be escalated to Preferred priority.'
    };
    return descriptions[this.form.workload_type] || 'Workload will be scheduled based on priority and energy availability.';
  }

  getDeploymentInfoClass(): string {
    const classes: { [key: string]: string } = {
      'Critical': 'bg-red-50 border border-red-200 text-red-800',
      'Preferred': 'bg-orange-50 border border-orange-200 text-orange-800',
      'Optional': 'bg-blue-50 border border-blue-200 text-blue-800'
    };
    return classes[this.form.workload_type] || 'bg-gray-50 border border-gray-200 text-gray-800';
  }
}