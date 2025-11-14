import { Directive, ElementRef, computed, input, OnInit } from '@angular/core';
import { hlm } from '@spartan-ng/brain/core';

import type { ClassValue } from 'clsx';

@Directive({
  selector: 'div[hlmSidebarGroup]',
  standalone: true,
  host: {
    'data-sidebar': 'group',
    '[class]': '_computedClass()',
  },
})
export class HlmSidebarGroupDirective implements OnInit {
  public readonly userClass = input<ClassValue>('', { alias: 'class' });
  protected _computedClass = computed(() =>
    hlm('relative flex w-full min-w-0 flex-col p-2', this.userClass()),
  );
  constructor(private element: ElementRef<HTMLDivElement>) {}

  ngOnInit() {
    if (this.element.nativeElement.tagName.toLowerCase() !== 'div') {
      console.warn(
        'hlmSidebarGroup directive should only be used on <div> elements',
      );
    }
  }
}
