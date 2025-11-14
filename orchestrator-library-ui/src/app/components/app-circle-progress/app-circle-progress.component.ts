import { Component, Input, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-circle-progress',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div [style.width.px]="size" [style.height.px]="size" class="relative">
      <svg
        [attr.width]="size"
        [attr.height]="size"
        [attr.viewBox]="'0 0 ' + size + ' ' + size"
        class="transform -rotate-90"
      >
        <!-- Background circle -->
        <circle
          [attr.cx]="size / 2"
          [attr.cy]="size / 2"
          [attr.r]="(size - strokeWidth) / 2"
          [attr.stroke-width]="strokeWidth"
          [attr.stroke]="backgroundColor"
          fill="none"
        />
        <!-- Progress circle -->
        <circle
          [attr.cx]="size / 2"
          [attr.cy]="size / 2"
          [attr.r]="(size - strokeWidth) / 2"
          [attr.stroke-width]="strokeWidth"
          stroke="currentColor"
          [attr.stroke-dasharray]="circumference"
          [attr.stroke-dashoffset]="dashOffset"
          fill="none"
        />
      </svg>
      <div class="absolute inset-0 flex items-center justify-center">
        <ng-content></ng-content>
      </div>
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
      }
    `,
  ],
})
export class AppCircleProgressComponent implements OnChanges {
  @Input() progress = 0; // 0-100
  @Input() size = 100; // px
  @Input() strokeWidth = 10; // px
  @Input() backgroundColor = '#e6e6e6';
  @Input() progressColor = '#4caf50';

  circumference = 0;
  dashOffset = 0;
  progressPercentage = 0;

  ngOnChanges(): void {
    this.calculateCircumference();
    this.calculateDashOffset();
  }

  private calculateCircumference(): void {
    const radius = (this.size - this.strokeWidth) / 2;
    this.circumference = 2 * Math.PI * radius;
  }

  private calculateDashOffset(): void {
    this.progressPercentage = Math.min(100, Math.max(0, this.progress));
    this.dashOffset = this.circumference - (this.progressPercentage / 100) * this.circumference;
  }
}
