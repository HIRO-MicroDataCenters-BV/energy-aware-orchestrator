import { Directive, ElementRef, computed, input, OnInit } from '@angular/core';
import { hlm } from '@spartan-ng/brain/core';

import { HlmSidebarService } from './hlm-sidebar.service';

import type { ClassValue } from 'clsx';

@Directive({
  selector: 'main[hlmSidebarInset]', // Restrict to main elements only
  standalone: true,
  host: {
    'data-slot': 'sidebar-inset',
    '[class]': '_computedClass()',
  },
})
export class HlmSidebarInsetDirective implements OnInit {
  public readonly userClass = input<ClassValue>('', { alias: 'class' });
  protected _computedClass = computed(() =>
    hlm(
      'bg-background relative flex min-h-svh flex-1 flex-col',
      this.sidebarService.variant() === 'inset' &&
        'min-h-[calc(100svh-theme(spacing.4)))] md:m-2  md:rounded-xl md:shadow-sm',
      this.sidebarService.open() ? 'md:ml-0' : 'md:ml-2',
      this.userClass(),
    ),
  );
  constructor(
    private element: ElementRef<HTMLElement>,
    public sidebarService: HlmSidebarService,
  ) {}

  ngOnInit() {
    if (this.element.nativeElement.tagName.toLowerCase() !== 'main') {
      console.warn(
        'hlmSidebarInset directive should only be used on <main> elements',
      );
    }
  }
}
