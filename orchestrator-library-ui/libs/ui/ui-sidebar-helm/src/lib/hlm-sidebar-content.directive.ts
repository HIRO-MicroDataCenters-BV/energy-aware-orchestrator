import { Directive, ElementRef, computed, input, OnInit } from '@angular/core';
import { hlm } from '@spartan-ng/brain/core';

import type { ClassValue } from 'clsx';

@Directive({
  selector: 'div[hlmSidebarContent]',
  standalone: true,
  host: {
    'data-sidebar': 'content',
    '[class]': '_computedClass()',
  },
})
export class HlmSidebarContentDirective implements OnInit {
  public readonly userClass = input<ClassValue>('', { alias: 'class' });
  protected _computedClass = computed(() =>
    hlm(
      'flex min-h-0 flex-1 flex-col gap-2 overflow-auto group-data-[collapsible=icon]:overflow-hidden',
      this.userClass(),
    ),
  );

  constructor(private element: ElementRef<HTMLDivElement>) {}
  ngOnInit() {
    if (this.element.nativeElement.tagName.toLowerCase() !== 'div') {
      console.warn(
        'hlmSidebarContent directive should only be used on <div> elements',
      );
    }
  }
}
