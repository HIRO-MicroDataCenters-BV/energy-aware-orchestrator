import { Directive, ElementRef, computed, input } from '@angular/core';
import { hlm } from '@spartan-ng/brain/core';

import type { ClassValue } from 'clsx';

@Directive({
  selector: 'div[hlmSidebarWrapper]', // Restrict to main elements only
  standalone: true,
  host: {
    'data-slot': 'sidebar-wrapper',
    '[class]': '_computedClass()',
  },
})
export class HlmSidebarWrapperDirective {
  public readonly userClass = input<ClassValue>('', { alias: 'class' });
  protected _computedClass = computed(() =>
    hlm(
      'group/sidebar-wrapper has-data-[variant=inset]:bg-sidebar flex min-h-svh w-full',
      this.userClass(),
    ),
  );

  constructor(private element: ElementRef<HTMLElement>) {
    if (this.element.nativeElement.tagName.toLowerCase() !== 'div') {
      console.warn(
        'hlmSidebarWrapper directive should only be used on <div> elements',
      );
    }
  }
}
