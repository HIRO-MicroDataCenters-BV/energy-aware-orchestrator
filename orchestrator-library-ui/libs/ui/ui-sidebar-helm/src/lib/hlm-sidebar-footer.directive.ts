import { Directive, ElementRef, computed, input, OnInit } from '@angular/core';
import { hlm } from '@spartan-ng/brain/core';

import type { ClassValue } from 'clsx';

@Directive({
  selector: 'div[hlmSidebarFooter]',
  standalone: true,
  host: {
    'data-sidebar': 'footer',
    '[class]': '_computedClass()',
  },
})
export class HlmSidebarFooterDirective implements OnInit {
  public readonly userClass = input<ClassValue>('', { alias: 'class' });
  protected _computedClass = computed(() =>
    hlm('flex flex-col gap-2 p-2', this.userClass()),
  );

  constructor(private element: ElementRef<HTMLDivElement>) {}

  ngOnInit() {
    if (this.element.nativeElement.tagName.toLowerCase() !== 'div') {
      console.warn(
        'hlmSidebarFooter directive should only be used on <div> elements',
      );
    }
  }
}
