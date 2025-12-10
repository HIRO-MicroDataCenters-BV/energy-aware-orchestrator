import { CommonModule } from '@angular/common';
import { Component, input, effect } from '@angular/core';
import { hlm } from '@spartan-ng/brain/core';
import { BrnSheetContentDirective } from '@spartan-ng/brain/sheet';
import {
  HlmSheetComponent,
  HlmSheetContentComponent,
} from '@spartan-ng/ui-sheet-helm';

import { HlmSidebarService } from './hlm-sidebar.service';

import type { ClassValue } from 'clsx';

@Component({
  selector: 'hlm-sidebar',
  standalone: true,
  imports: [
    CommonModule,
    HlmSheetComponent,
    BrnSheetContentDirective,
    HlmSheetContentComponent,
  ],
  styles: [`
    :host {
      flex-shrink: 0;
    }
    :host(.desktop-mode) {
      display: block;
      width: var(--sidebar-width);
      transition: width 200ms ease-linear;
    }
    :host(.desktop-mode.collapsed) {
      width: var(--sidebar-width-icon);
    }
    :host(.mobile-mode) {
      display: contents;
    }
  `],
  host: {
    '[class.desktop-mode]': '!sidebarService.isMobile()',
    '[class.mobile-mode]': 'sidebarService.isMobile()',
    '[class.collapsed]': 'sidebarService.state() === "collapsed"',
  },
  template: `
    <ng-template #contentContainer>
      <ng-content></ng-content>
    </ng-template>

    @if (collapsible() === 'none') {
      <div
        data-slot="sidebar"
        [class]="
          _cn(
            'bg-sidebar text-sidebar-foreground flex h-full w-[var(--sidebar-width)] flex-col',
            userClass()
          )
        "
      >
        <ng-container [ngTemplateOutlet]="contentContainer"></ng-container>
      </div>
    } @else if (sidebarService.isMobile()) {
      <hlm-sheet
        [closeDelay]="0"
        [state]="sidebarService.openMobile() ? 'open' : 'closed'"
        (stateChanged)="sidebarService.setOpenMobile($event === 'open')"
      >
        <hlm-sheet-content
          *brnSheetContent="let ctx"
          data-slot="sidebar"
          data-sidebar="sidebar"
          data-mobile="true"
          class="bg-sidebar text-sidebar-foreground h-screen w-[var(--sidebar-width-mobile)] p-0 [&>button]:hidden"
        >
          <div class="flex h-full w-full flex-col">
            <ng-container [ngTemplateOutlet]="contentContainer"></ng-container>
          </div>
        </hlm-sheet-content>
      </hlm-sheet>
    } @else {
      <div
        class="group peer text-sidebar-foreground block"
        [attr.data-state]="sidebarService.state()"
        [attr.data-collapsible]="
          sidebarService.state() === 'collapsed' ? collapsible() : ''
        "
        [attr.data-variant]="variant()"
        [attr.data-side]="side()"
        data-slot="sidebar"
      >
        <!-- Sidebar gap on desktop - this div creates space in the flex layout -->
        <div
          class="relative bg-transparent transition-all duration-200 ease-linear h-full"
          [style.width]="sidebarService.state() === 'collapsed' ? 'var(--sidebar-width-icon)' : 'var(--sidebar-width)'"
        ></div>
        <div
          [class]="
            _cn(
              'fixed z-10 flex transition-all duration-200 ease-linear',
              side() === 'left' ? 'left-0 border-r' : 'right-0 border-l',
              userClass()
            )
          "
          [style.top]="'0'"
          [style.bottom]="'0'"
          [style.width]="sidebarService.state() === 'collapsed' ? 'var(--sidebar-width-icon)' : 'var(--sidebar-width)'"
        >
          <div
            data-sidebar="sidebar"
            class="bg-sidebar group-data-[variant=floating]:border-sidebar-border flex h-full w-full flex-col group-data-[variant=floating]:rounded-lg group-data-[variant=floating]:border group-data-[variant=floating]:shadow"
          >
            <ng-container [ngTemplateOutlet]="contentContainer"></ng-container>
          </div>
        </div>
      </div>
    }
  `,
})
export class HlmSidebarComponent {
  public readonly side = input<'left' | 'right'>('left');
  public readonly variant = input<'sidebar' | 'floating' | 'inset'>('sidebar');
  public readonly collapsible = input<'offcanvas' | 'icon' | 'none'>(
    'offcanvas',
  );
  public readonly userClass = input<ClassValue>('', { alias: 'class' });

  constructor(public sidebarService: HlmSidebarService) {
    // Sync variant input with service
    effect(() => {
      this.sidebarService.setVariant(this.variant());
    });
  }

  protected _cn(...args: ClassValue[]): string {
    return hlm(...args);
  }
}
