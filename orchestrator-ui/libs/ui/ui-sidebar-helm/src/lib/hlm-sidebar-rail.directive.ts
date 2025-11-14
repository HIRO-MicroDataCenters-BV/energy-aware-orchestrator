import {
  Directive,
  ElementRef,
  HostListener,
  computed,
  input,
  OnInit,
} from '@angular/core';
import { hlm } from '@spartan-ng/brain/core';

import { HlmSidebarService } from './hlm-sidebar.service';

import type { ClassValue } from 'clsx';

@Directive({
  selector: 'button[hlmSidebarRail]',
  standalone: true,
  host: {
    'data-sidebar': 'rail',
    'data-slot': 'sidebar-rail',
    'aria-label': 'Toggle Sidebar',
    tabindex: '-1',
    '[class]': '_computedClass()',
  },
})
export class HlmSidebarRailDirective implements OnInit {
  public readonly userClass = input<ClassValue>('', { alias: 'class' });
  protected _computedClass = computed(() =>
    hlm(
      'hover:after:bg-sidebar-border absolute inset-y-0 z-20 hidden w-4 -translate-x-1/2 transition-all ease-linear group-data-[side=left]:-right-4 group-data-[side=right]:left-0 after:absolute after:inset-y-0 after:left-1/2 after:w-[2px] sm:flex',
      'in-data-[side=left]:cursor-w-resize in-data-[side=right]:cursor-e-resize',
      '[[data-side=left][data-state=collapsed]_&]:cursor-e-resize [[data-side=right][data-state=collapsed]_&]:cursor-w-resize',
      'hover:group-data-[collapsible=offcanvas]:bg-sidebar group-data-[collapsible=offcanvas]:translate-x-0 group-data-[collapsible=offcanvas]:after:left-full',
      '[[data-side=left][data-collapsible=offcanvas]_&]:-right-2',
      '[[data-side=right][data-collapsible=offcanvas]_&]:-left-2',
      this.userClass(),
    ),
  );

  constructor(
    private element: ElementRef<HTMLButtonElement>,
    private sidebarService: HlmSidebarService,
  ) {}

  ngOnInit() {
    if (this.element.nativeElement.tagName.toLowerCase() !== 'button') {
      console.warn(
        'hlmSidebarRail directive should only be used on <button> elements',
      );
    }
  }

  @HostListener('click')
  onClick(): void {
    this.sidebarService.toggleSidebar();
  }
}
