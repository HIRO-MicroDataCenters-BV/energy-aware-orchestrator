import { NgModule } from '@angular/core';

import { HlmSidebarContentDirective } from './lib/hlm-sidebar-content.directive';
import { HlmSidebarFooterDirective } from './lib/hlm-sidebar-footer.directive';
import { HlmSidebarGroupActionDirective } from './lib/hlm-sidebar-group-action.directive';
import { HlmSidebarGroupContentDirective } from './lib/hlm-sidebar-group-content.directive';
import { HlmSidebarGroupLabelDirective } from './lib/hlm-sidebar-group-label.directive';
import { HlmSidebarGroupDirective } from './lib/hlm-sidebar-group.directive';
import { HlmSidebarHeaderDirective } from './lib/hlm-sidebar-header.directive';
import { HlmSidebarInputDirective } from './lib/hlm-sidebar-input.directive';
import { HlmSidebarInsetDirective } from './lib/hlm-sidebar-inset.directive';
import { HlmSidebarMenuActionDirective } from './lib/hlm-sidebar-menu-action.directive';
import { HlmSidebarMenuBadgeDirective } from './lib/hlm-sidebar-menu-badge.directive';
import { HlmSidebarMenuButtonDirective } from './lib/hlm-sidebar-menu-button.directive';
import { HlmSidebarMenuItemDirective } from './lib/hlm-sidebar-menu-item.directive';
import { HlmSidebarMenuSubButtonDirective } from './lib/hlm-sidebar-menu-sub-button.directive';
import { HlmSidebarMenuSubDirective } from './lib/hlm-sidebar-menu-sub.directive';
import { HlmSidebarMenuDirective } from './lib/hlm-sidebar-menu.directive';
import { HlmSidebarRailDirective } from './lib/hlm-sidebar-rail.directive';
import { HlmSidebarSeparatorDirective } from './lib/hlm-sidebar-separator.directive';
import { HlmSidebarTriggerComponent } from './lib/hlm-sidebar-trigger.component';
import { HlmSidebarWrapperDirective } from './lib/hlm-sidebar-wrapper.directive';
import { HlmSidebarComponent } from './lib/hlm-sidebar.component';

export * from './lib/hlm-sidebar.component';
export * from './lib/hlm-sidebar-content.directive';
export * from './lib/hlm-sidebar-footer.directive';
export * from './lib/hlm-sidebar-group.directive';
export * from './lib/hlm-sidebar-group-action.directive';
export * from './lib/hlm-sidebar-group-content.directive';
export * from './lib/hlm-sidebar-group-label.directive';
export * from './lib/hlm-sidebar-header.directive';
export * from './lib/hlm-sidebar-input.directive';
export * from './lib/hlm-sidebar-inset.directive';
export * from './lib/hlm-sidebar-menu.directive';
export * from './lib/hlm-sidebar-menu-action.directive';
export * from './lib/hlm-sidebar-menu-badge.directive';
export * from './lib/hlm-sidebar-menu-button.directive';
export * from './lib/hlm-sidebar-menu-item.directive';
export * from './lib/hlm-sidebar-menu-sub.directive';
export * from './lib/hlm-sidebar-menu-sub-button.directive';
export * from './lib/hlm-sidebar-rail.directive';
export * from './lib/hlm-sidebar-separator.directive';
export * from './lib/hlm-sidebar-trigger.component';
export * from './lib/hlm-sidebar.service';
export * from './lib/hlm-sidebar-wrapper.directive';

export const HlmSidebarImports = [
  HlmSidebarComponent,
  HlmSidebarContentDirective,
  HlmSidebarFooterDirective,
  HlmSidebarGroupDirective,
  HlmSidebarGroupActionDirective,
  HlmSidebarGroupContentDirective,
  HlmSidebarGroupLabelDirective,
  HlmSidebarHeaderDirective,
  HlmSidebarInputDirective,
  HlmSidebarInsetDirective,
  HlmSidebarMenuDirective,
  HlmSidebarMenuActionDirective,
  HlmSidebarMenuBadgeDirective,
  HlmSidebarMenuButtonDirective,
  HlmSidebarMenuItemDirective,
  HlmSidebarMenuSubDirective,
  HlmSidebarMenuSubButtonDirective,
  HlmSidebarRailDirective,
  HlmSidebarSeparatorDirective,
  HlmSidebarTriggerComponent,
  HlmSidebarWrapperDirective,
] as const;

@NgModule({
  imports: [...HlmSidebarImports],
  exports: [...HlmSidebarImports],
})
export class HlmSidebarModule {}
