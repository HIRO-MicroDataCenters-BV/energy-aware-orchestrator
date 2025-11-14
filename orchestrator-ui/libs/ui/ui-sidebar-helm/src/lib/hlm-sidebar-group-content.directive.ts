import { Directive, ElementRef, computed, input, OnInit } from '@angular/core';
import { hlm } from '@spartan-ng/brain/core';

import type { ClassValue } from 'clsx';

@Directive({
  selector: 'div[hlmSidebarGroupContent]',
  standalone: true,
  host: {
    'data-sidebar': 'group-content',
    '[class]': '_computedClass()',
  },
})
export class HlmSidebarGroupContentDirective implements OnInit {
  public readonly userClass = input<ClassValue>('', { alias: 'class' });
  protected _computedClass = computed(() =>
    hlm('w-full text-sm', this.userClass()),
  );

  constructor(private element: ElementRef<HTMLDivElement>) {}

  ngOnInit() {
    if (this.element.nativeElement.tagName.toLowerCase() !== 'div') {
      console.warn(
        'hlmSidebarGroupContent directive should only be used on <div> elements',
      );
    }
  }
}
