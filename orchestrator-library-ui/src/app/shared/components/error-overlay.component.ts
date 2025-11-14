import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslocoModule } from '@jsverse/transloco';

@Component({
  selector: 'app-error-overlay',
  standalone: true,
  imports: [CommonModule, TranslocoModule],
  template: `
    <div
      *ngIf="isVisible"
      class="error-overlay"
      [class.with-backdrop]="showBackdrop"
    >
      <div class="error-content">
        <!-- Error Icon -->
        <div class="error-icon">
          <svg
            class="icon"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            ></path>
          </svg>
        </div>

        <!-- Error message -->
        <div class="error-text">
          <p class="error-title" *ngIf="title">
            {{ title | transloco }}
          </p>
          <p class="error-message" *ngIf="message">
            {{ message | transloco }}
          </p>
        </div>

        <!-- Retry button -->
        <button
          *ngIf="showRetry"
          class="retry-button"
          (click)="onRetry()"
          type="button"
        >
          {{ retryText | transloco }}
        </button>

        <!-- Custom content slot -->
        <ng-content></ng-content>
      </div>
    </div>
  `,
  styles: [
    `
      .error-overlay {
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

      .error-overlay.with-backdrop {
        background-color: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(2px);
      }

      .error-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        gap: 1rem;
        padding: 1.5rem;
        max-width: 300px;
      }

      .error-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 3rem;
        height: 3rem;
        color: #ef4444;
      }

      .error-icon .icon {
        width: 100%;
        height: 100%;
      }

      .error-text {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
      }

      .error-title {
        margin: 0;
        font-size: 1rem;
        font-weight: 600;
        color: #1f2937;
      }

      .error-message {
        margin: 0;
        font-size: 0.875rem;
        color: #6b7280;
        line-height: 1.4;
      }

      .retry-button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.5rem 1rem;
        font-size: 0.875rem;
        font-weight: 500;
        color: #ffffff;
        background-color: #3b82f6;
        border: none;
        border-radius: 0.375rem;
        cursor: pointer;
        transition: background-color 0.2s ease-in-out;
      }

      .retry-button:hover {
        background-color: #2563eb;
      }

      .retry-button:focus {
        outline: none;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.5);
      }

      .retry-button:active {
        background-color: #1d4ed8;
      }

      /* Different icon sizes */
      .error-overlay.size-sm .error-icon {
        width: 2rem;
        height: 2rem;
      }

      .error-overlay.size-lg .error-icon {
        width: 4rem;
        height: 4rem;
      }

      /* Different themes */
      .error-overlay.theme-warning .error-icon {
        color: #f59e0b;
      }

      .error-overlay.theme-danger .error-icon {
        color: #ef4444;
      }

      .error-overlay.theme-info .error-icon {
        color: #3b82f6;
      }
    `,
  ],
})
export class ErrorOverlayComponent {
  @Input() isVisible = false;
  @Input() title = 'error.title';
  @Input() message = 'error.generic';
  @Input() showBackdrop = true;
  @Input() showRetry = false;
  @Input() retryText = 'action.retry';
  @Input() size: 'sm' | 'md' | 'lg' = 'md';
  @Input() theme: 'danger' | 'warning' | 'info' = 'danger';

  @Output() retry = new EventEmitter<void>();

  onRetry(): void {
    this.retry.emit();
  }

  get cssClasses(): string {
    const classes = ['error-overlay'];

    if (this.showBackdrop) {
      classes.push('with-backdrop');
    }

    if (this.size !== 'md') {
      classes.push(`size-${this.size}`);
    }

    if (this.theme !== 'danger') {
      classes.push(`theme-${this.theme}`);
    }

    return classes.join(' ');
  }
}
