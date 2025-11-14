import { computed, Component, input, output } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucidePanelLeft } from '@ng-icons/lucide';
import { hlm } from '@spartan-ng/brain/core';
import { buttonVariants } from '@spartan-ng/ui-button-helm';
import { HlmIconDirective } from '@spartan-ng/ui-icon-helm';

import { HlmSidebarService } from './hlm-sidebar.service';

import type { ClassValue } from 'clsx';

@Component({
  selector: 'hlm-sidebar-trigger',
  standalone: true,
  imports: [HlmIconDirective, NgIcon],
  providers: [provideIcons({ lucidePanelLeft })],
  template: `
    <button
      data-sidebar="trigger"
      data-slot="sidebar-trigger"
      [class]="_computedClass()"
      (click)="onClick($event)"
    >
      <ng-icon hlm name="lucidePanelLeft" size="sm"></ng-icon>
    </button>
  `,
})
export class HlmSidebarTriggerComponent {
  public readonly userClass = input<ClassValue>('', { alias: 'class' });
  public readonly userOnClick = output<MouseEvent>({ alias: 'onClick' });

  protected _computedClass = computed(() =>
    hlm(
      buttonVariants({ variant: 'ghost', size: 'icon' }),
      'h-7 w-7',
      this.userClass(),
    ),
  );
  constructor(private sidebarService: HlmSidebarService) {}

  onClick(event: MouseEvent): void {
    this.userOnClick.emit(event);
    this.sidebarService.toggleSidebar();
  }
}
