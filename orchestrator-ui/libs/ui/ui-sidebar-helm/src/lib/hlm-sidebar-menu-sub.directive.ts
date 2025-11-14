import { Directive, ElementRef, computed, input, OnInit } from '@angular/core';
import { hlm } from '@spartan-ng/brain/core';

import type { ClassValue } from 'clsx';

@Directive({
  selector: 'ul[hlmSidebarMenuSub]',
  standalone: true,
  host: {
    'data-sidebar': 'menu-sub',
    '[class]': '_computedClass()',
  },
})
export class HlmSidebarMenuSubDirective implements OnInit {
  public readonly userClass = input<ClassValue>('', { alias: 'class' });
  protected _computedClass = computed(() =>
    hlm(
      'mx-3.5 flex min-w-0 translate-x-px flex-col gap-1 border-l border-sidebar-border px-2.5 py-0.5',
      'group-data-[collapsible=icon]:hidden',
      this.userClass(),
    ),
  );
  constructor(private element: ElementRef<HTMLUListElement>) {}

  ngOnInit() {
    if (this.element.nativeElement.tagName.toLowerCase() !== 'ul') {
      console.warn(
        'hlmSidebarMenuSub directive should only be used on <ul> elements',
      );
    }
  }
}
