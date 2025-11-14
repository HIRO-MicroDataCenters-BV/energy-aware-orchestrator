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
        class="group peer text-sidebar-foreground hidden md:block"
        [attr.data-state]="sidebarService.state()"
        [attr.data-collapsible]="
          sidebarService.state() === 'collapsed' ? collapsible() : ''
        "
        [attr.data-variant]="variant()"
        [attr.data-side]="side()"
        data-slot="sidebar"
      >
        <!-- Sidebar gap on desktop -->
        <div
          [class]="
            _cn(
              'relative h-svh w-[var(--sidebar-width)] bg-transparent transition-[width] duration-200 ease-linear',
              'group-data-[collapsible=offcanvas]:w-0',
              'group-data-[side=right]:rotate-180',
              variant() === 'floating' || variant() === 'inset'
                ? 'group-data-[collapsible=icon]:w-[calc(var(--sidebar-width-icon)_+_theme(spacing.4))]'
                : 'group-data-[collapsible=icon]:w-[var(--sidebar-width-icon)]'
            )
          "
        ></div>
        <div
          [class]="
            _cn(
              'fixed inset-y-0 z-10 hidden h-svh w-[var(--sidebar-width)] transition-[left,right,width] duration-200 ease-linear md:flex',
              side() === 'left'
                ? 'left-0 group-data-[collapsible=offcanvas]:left-[calc(var(--sidebar-width)*-1)]'
                : 'right-0 group-data-[collapsible=offcanvas]:right-[calc(var(--sidebar-width)*-1)]',
              variant() === 'floating' || variant() === 'inset'
                ? 'p-2 group-data-[collapsible=icon]:w-[calc(var(--sidebar-width-icon)_+_theme(spacing.4)_+2px)]'
                : 'group-data-[collapsible=icon]:w-[var(--sidebar-width-icon)] group-data-[side=left]:border-r group-data-[side=right]:border-l',
              userClass()
            )
          "
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
