import { Directive, ElementRef, computed, input, OnInit } from '@angular/core';
import { hlm } from '@spartan-ng/brain/core';

import type { ClassValue } from 'clsx';

@Directive({
  selector: 'li[hlmSidebarMenuItem]',
  standalone: true,
  host: {
    'data-sidebar': 'menu-item',
    '[class]': '_computedClass()',
  },
})
export class HlmSidebarMenuItemDirective implements OnInit {
  public readonly userClass = input<ClassValue>('', { alias: 'class' });
  protected _computedClass = computed(() =>
    hlm('group/menu-item relative', this.userClass()),
  );
  constructor(private element: ElementRef<HTMLLIElement>) {}

  ngOnInit() {
    if (this.element.nativeElement.tagName.toLowerCase() !== 'li') {
      console.warn(
        'hlmSidebarMenuItem directive should only be used on <li> elements',
      );
    }
  }
}
