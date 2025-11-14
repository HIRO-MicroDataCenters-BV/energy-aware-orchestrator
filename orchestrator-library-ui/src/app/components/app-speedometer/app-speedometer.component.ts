import {
  Component,
  Input,
  OnChanges,
  Inject,
  PLATFORM_ID,
  OnDestroy,
  ChangeDetectorRef,
} from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';

@Component({
  selector: 'app-speedometer',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './app-speedometer.component.html',
  styleUrls: ['./app-speedometer.component.scss'],
})
export class AppSpeedometerComponent implements OnChanges, OnDestroy {
  @Input() value = 0;
  @Input() min = 0;
  @Input() max = 100;
  @Input() unit = '%';
  @Input() label = '';
  @Input() size = 200;
  @Input() strokeWidth = 14.4;
  @Input() backgroundColor = '#e5e7eb';
  @Input() lowColor = '#22c55e';
  @Input() mediumColor = '#eab308';
  @Input() highColor = '#dc2626';
  @Input() lowThreshold = 30;
  @Input() highThreshold = 60;
  @Input() animate = true;

  Math = Math;
  centerX = 0;
  centerY = 0;
  outerRadius = 0;
  displayValue = 0;
  currentColor = '#22c55e';
  circumference = 0;
  strokeDashoffset = 0;

  startAngle = -Math.PI;
  endAngle = 0;

  private animationId: number | null = null;
  public isBrowser = false;

  constructor(
    @Inject(PLATFORM_ID) private platformId: object,
    private cdr: ChangeDetectorRef
  ) {
    this.isBrowser = isPlatformBrowser(this.platformId);
    if (!this.isBrowser || typeof window === 'undefined') {
      this.animate = false;
    }
  }

  ngOnChanges(): void {
    try {
      this.calculateDimensions();
      const safeValue = this.value || 0;
      const safeMin = this.min || 0;
      const safeMax = this.max || 100;

      if (this.isBrowser) {
        this.updateDisplayValue();
      } else {
        this.displayValue = Math.max(safeMin, Math.min(safeMax, safeValue));
        this.currentColor = this.getValueColorForValue(this.displayValue);
      }
    } catch {
      this.displayValue = this.value || 0;
      this.currentColor = this.lowColor || '#22c55e';
    }
  }

  ngOnDestroy(): void {
    try {
      if (
        this.animationId !== null &&
        this.isBrowser &&
        typeof window !== 'undefined' &&
        window.cancelAnimationFrame
      ) {
        window.cancelAnimationFrame(this.animationId);
      }
    } catch {
      // Ignore cleanup errors
    }
  }

  private calculateDimensions(): void {
    this.centerX = this.size / 2;
    this.centerY = this.size / 2;
    this.outerRadius = (this.size - this.strokeWidth) / 2;
    this.circumference = Math.PI * this.outerRadius;
    if (this.strokeDashoffset === 0) {
      this.strokeDashoffset = this.circumference;
    }
  }

  private updateDisplayValue(): void {
    const targetValue = Math.max(this.min, Math.min(this.max, this.value));

    if (
      this.animationId !== null &&
      typeof window !== 'undefined' &&
      window.cancelAnimationFrame
    ) {
      window.cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }

    if (
      this.animate &&
      this.isBrowser &&
      typeof window !== 'undefined' &&
      typeof document !== 'undefined' &&
      typeof requestAnimationFrame !== 'undefined' &&
      typeof performance !== 'undefined' &&
      window.requestAnimationFrame &&
      window.performance
    ) {
      const startValue = this.displayValue;
      const duration = 800;
      const startTime = performance.now();

      const startOffset =
        this.displayValue === 0 ? this.circumference : this.strokeDashoffset;
      const targetPercentage = (targetValue - this.min) / (this.max - this.min);
      const targetOffset =
        this.circumference - targetPercentage * this.circumference;

      const animate = (currentTime: number) => {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        const easeProgress = this.easeInOutCubic(progress);

        this.displayValue = Math.round(
          startValue + (targetValue - startValue) * easeProgress
        );

        this.strokeDashoffset =
          startOffset + (targetOffset - startOffset) * easeProgress;

        this.currentColor = this.getValueColorForValue(this.displayValue);

        if (progress < 1) {
          this.animationId = requestAnimationFrame(animate);
        } else {
          this.displayValue = targetValue;
          this.strokeDashoffset = targetOffset;
          this.currentColor = this.getValueColorForValue(targetValue);
          this.animationId = null;
        }
      };

      try {
        if (typeof window !== 'undefined' && window.requestAnimationFrame) {
          this.animationId = window.requestAnimationFrame(animate);
        } else {
          this.displayValue = targetValue;
          this.currentColor = this.getValueColorForValue(targetValue);
        }
      } catch {
        this.displayValue = targetValue;
        this.currentColor = this.getValueColorForValue(targetValue);
        this.updateStrokeDashoffset(targetValue);
      }
    } else {
      this.displayValue = targetValue;
      this.currentColor = this.getValueColorForValue(targetValue);
      this.updateStrokeDashoffset(targetValue);
    }
  }

  private easeInOutCubic(t: number): number {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  private updateStrokeDashoffset(value: number): void {
    const percentage = (value - this.min) / (this.max - this.min);
    this.strokeDashoffset =
      this.circumference - percentage * this.circumference;
  }

  getValueColor(): string {
    return this.currentColor;
  }

  getValueColorForValue(value: number): string {
    try {
      if (value == null || !isFinite(value)) {
        return this.lowColor;
      }

      const range = this.max - this.min;
      if (range <= 0 || !isFinite(range)) {
        return this.lowColor;
      }

      const percentage = ((value - this.min) / range) * 100;

      if (!isFinite(percentage) || percentage <= this.lowThreshold) {
        return this.lowColor;
      } else if (percentage <= this.highThreshold) {
        const ratio =
          (percentage - this.lowThreshold) /
          (this.highThreshold - this.lowThreshold);
        const exponentialRatio = Math.pow(ratio, 0.7);
        return this.interpolateColor(
          this.lowColor,
          this.mediumColor,
          exponentialRatio
        );
      } else {
        const ratio = Math.min(
          1,
          (percentage - this.highThreshold) / (100 - this.highThreshold)
        );
        const exponentialRatio = Math.pow(ratio, 0.5);
        return this.interpolateColor(
          this.mediumColor,
          this.highColor,
          exponentialRatio
        );
      }
    } catch {
      return this.lowColor;
    }
  }

  private interpolateColor(
    color1: string,
    color2: string,
    ratio: number
  ): string {
    try {
      if (!color1 || !color2 || !isFinite(ratio)) {
        return color1 || this.lowColor;
      }

      const hex1 = color1.replace('#', '');
      const hex2 = color2.replace('#', '');

      if (hex1.length !== 6 || hex2.length !== 6) {
        return color1;
      }

      const r1 = parseInt(hex1.substring(0, 2), 16);
      const g1 = parseInt(hex1.substring(2, 4), 16);
      const b1 = parseInt(hex1.substring(4, 6), 16);

      const r2 = parseInt(hex2.substring(0, 2), 16);
      const g2 = parseInt(hex2.substring(2, 4), 16);
      const b2 = parseInt(hex2.substring(4, 6), 16);

      if (
        isNaN(r1) ||
        isNaN(g1) ||
        isNaN(b1) ||
        isNaN(r2) ||
        isNaN(g2) ||
        isNaN(b2)
      ) {
        return color1;
      }

      const r = Math.round(r1 + (r2 - r1) * ratio);
      const g = Math.round(g1 + (g2 - g1) * ratio);
      const b = Math.round(b1 + (b2 - b1) * ratio);

      return `#${r.toString(16).padStart(2, '0')}${g
        .toString(16)
        .padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
    } catch {
      return color1 || this.lowColor;
    }
  }

  getShortLabel(): string {
    const lowerLabel = this.label.toLowerCase();
    if (lowerLabel.includes('cpu')) {
      return 'CPU';
    } else if (lowerLabel.includes('memory') || lowerLabel.includes('mem')) {
      return 'MEM';
    } else if (lowerLabel.includes('disk') || lowerLabel.includes('storage')) {
      return 'DISK';
    } else if (lowerLabel.includes('network') || lowerLabel.includes('net')) {
      return 'NET';
    }
    const words = this.label.split(' ');
    if (words.length > 0 && words[0].length <= 4) {
      return words[0].toUpperCase();
    }
    return this.label.substring(0, 4).toUpperCase();
  }

  getStrokeDasharray(): string {
    return `${this.circumference} ${this.circumference}`;
  }

  getStrokeDashoffset(): number {
    return this.strokeDashoffset;
  }

  getArcPath(
    startAngle: number,
    endAngle: number,
    outerRadius: number
  ): string {
    const largeArcFlag = Math.abs(endAngle - startAngle) > Math.PI ? 1 : 0;

    const x1 = this.centerX + outerRadius * Math.cos(startAngle);
    const y1 = this.centerY + outerRadius * Math.sin(startAngle);
    const x2 = this.centerX + outerRadius * Math.cos(endAngle);
    const y2 = this.centerY + outerRadius * Math.sin(endAngle);

    return `M ${x1} ${y1} A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${x2} ${y2}`;
  }

  getProgressArcPath(): string {
    if (this.displayValue <= this.min) {
      return '';
    }

    const percentage = (this.displayValue - this.min) / (this.max - this.min);
    const progressEndAngle = this.startAngle + percentage * Math.PI;

    const largeArcFlag =
      Math.abs(progressEndAngle - this.startAngle) > Math.PI ? 1 : 0;

    const x1 = this.centerX + this.outerRadius * Math.cos(this.startAngle);
    const y1 = this.centerY + this.outerRadius * Math.sin(this.startAngle);
    const x2 = this.centerX + this.outerRadius * Math.cos(progressEndAngle);
    const y2 = this.centerY + this.outerRadius * Math.sin(progressEndAngle);

    return `M ${x1} ${y1} A ${this.outerRadius} ${this.outerRadius} 0 ${largeArcFlag} 1 ${x2} ${y2}`;
  }

  getStartCapX(): number {
    const x = this.centerX + this.outerRadius * Math.cos(this.startAngle);
    return x - this.strokeWidth / 2;
  }

  getStartCapY(): number {
    const y = this.centerY + this.outerRadius * Math.sin(this.startAngle);
    return y - this.strokeWidth / 2;
  }

  getStartCapTransform(): string {
    const centerX = this.centerX + this.outerRadius * Math.cos(this.startAngle);
    const centerY = this.centerY + this.outerRadius * Math.sin(this.startAngle);
    const angle = (this.startAngle * 180) / Math.PI + 90;
    return `rotate(${angle} ${centerX} ${centerY})`;
  }

  getEndCapX(): number {
    const x = this.centerX + this.outerRadius * Math.cos(this.endAngle);
    return x - this.strokeWidth / 2;
  }

  getEndCapY(): number {
    const y = this.centerY + this.outerRadius * Math.sin(this.endAngle);
    return y - this.strokeWidth / 2;
  }

  getEndCapTransform(): string {
    const centerX = this.centerX + this.outerRadius * Math.cos(this.endAngle);
    const centerY = this.centerY + this.outerRadius * Math.sin(this.endAngle);
    const angle = (this.endAngle * 180) / Math.PI + 90;
    return `rotate(${angle} ${centerX} ${centerY})`;
  }

  getProgressEndCapX(): number {
    const angle = this.getProgressEndAngle();
    const x = this.centerX + this.outerRadius * Math.cos(angle);
    return x - this.strokeWidth / 2;
  }

  getProgressEndCapY(): number {
    const angle = this.getProgressEndAngle();
    const y = this.centerY + this.outerRadius * Math.sin(angle);
    return y - this.strokeWidth / 2;
  }

  getProgressEndCapTransform(): string {
    const angle = this.getProgressEndAngle();
    const centerX = this.centerX + this.outerRadius * Math.cos(angle);
    const centerY = this.centerY + this.outerRadius * Math.sin(angle);
    const rotationAngle = (angle * 180) / Math.PI + 90;
    return `rotate(${rotationAngle} ${centerX} ${centerY})`;
  }

  getProgressEndAngle(): number {
    const percentage = (this.displayValue - this.min) / (this.max - this.min);
    return this.startAngle + percentage * Math.PI;
  }

  formatValue(value: number): string {
    return value.toFixed(2);
  }
}
