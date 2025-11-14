import { Directive, ElementRef, computed, input, OnInit } from '@angular/core';
import { hlm } from '@spartan-ng/brain/core';

import type { ClassValue } from 'clsx';

@Directive({
  selector: 'ul[hlmSidebarMenu]',
  standalone: true,
  host: {
    'data-sidebar': 'menu',
    '[class]': '_computedClass()',
  },
})
export class HlmSidebarMenuDirective implements OnInit {
  public readonly userClass = input<ClassValue>('', { alias: 'class' });
  protected _computedClass = computed(() =>
    hlm('flex w-full min-w-0 flex-col gap-1', this.userClass()),
  );
  constructor(private element: ElementRef) {}

  ngOnInit() {
    if (this.element.nativeElement.tagName.toLowerCase() !== 'ul') {
      console.warn(
        'hlm-sidebar-menu directive should be used on a <ul> element',
      );
    }
  }
}
