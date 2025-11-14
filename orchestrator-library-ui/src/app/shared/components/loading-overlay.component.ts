import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslocoModule } from '@jsverse/transloco';

@Component({
  selector: 'app-loading-overlay',
  standalone: true,
  imports: [CommonModule, TranslocoModule],
  template: `
    <div
      *ngIf="isVisible"
      class="loading-overlay"
      [class.with-backdrop]="showBackdrop"
    >
      <div class="loading-content">
        <!-- Spinner -->
        <div class="loading-spinner">
          <div class="spinner"></div>
        </div>

        <!-- Custom content slot -->
        <ng-content></ng-content>
      </div>
    </div>
  `,
  styles: [
    `
      .loading-overlay {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 50;
        border-radius: inherit;
      }

      .loading-overlay.with-backdrop {
        background-color: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(2px);
      }

      .loading-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        gap: 0.75rem;
      }

      .loading-spinner {
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .spinner {
        width: 2rem;
        height: 2rem;
        border: 2px solid #e5e7eb;
        border-top: 2px solid #3b82f6;
        border-radius: 50%;
        animation: spin 1s linear infinite;
      }

      @keyframes spin {
        0% {
          transform: rotate(0deg);
        }
        100% {
          transform: rotate(360deg);
        }
      }

      /* Different spinner sizes */
      .loading-overlay.size-sm .spinner {
        width: 1.5rem;
        height: 1.5rem;
        border-width: 1.5px;
      }

      .loading-overlay.size-lg .spinner {
        width: 3rem;
        height: 3rem;
        border-width: 3px;
      }

      /* Different color themes */
      .loading-overlay.theme-primary .spinner {
        border-top-color: #3b82f6;
      }

      .loading-overlay.theme-success .spinner {
        border-top-color: #10b981;
      }

      .loading-overlay.theme-warning .spinner {
        border-top-color: #f59e0b;
      }

      .loading-overlay.theme-danger .spinner {
        border-top-color: #ef4444;
      }
    `,
  ],
})
export class LoadingOverlayComponent {
  @Input() isVisible = false;
  @Input() showBackdrop = true;
  @Input() size: 'sm' | 'md' | 'lg' = 'md';
  @Input() theme: 'primary' | 'success' | 'warning' | 'danger' = 'primary';

  get cssClasses(): string {
    const classes = ['loading-overlay'];

    if (this.showBackdrop) {
      classes.push('with-backdrop');
    }

    if (this.size !== 'md') {
      classes.push(`size-${this.size}`);
    }

    if (this.theme !== 'primary') {
      classes.push(`theme-${this.theme}`);
    }

    return classes.join(' ');
  }
}
