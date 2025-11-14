import { Directive, ElementRef, computed, input, OnInit } from '@angular/core';
import { hlm } from '@spartan-ng/brain/core';

import type { ClassValue } from 'clsx';

@Directive({
  selector: 'div[hlmSidebarHeader]',
  standalone: true,
  host: {
    'data-sidebar': 'header',
    '[class]': '_computedClass()',
  },
})
export class HlmSidebarHeaderDirective implements OnInit {
  public readonly userClass = input<ClassValue>('', { alias: 'class' });
  protected _computedClass = computed(() =>
    hlm('flex flex-col gap-2 p-2', this.userClass()),
  );
  constructor(private element: ElementRef<HTMLDivElement>) {}

  ngOnInit() {
    if (this.element.nativeElement.tagName.toLowerCase() !== 'div') {
      console.warn(
        'hlmSidebarHeader directive should only be used on <div> elements',
      );
    }
  }
}
