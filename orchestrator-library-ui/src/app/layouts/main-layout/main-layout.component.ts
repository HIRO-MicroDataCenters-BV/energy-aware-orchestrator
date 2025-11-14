import { Component, inject, OnInit } from '@angular/core';
import { PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { TranslocoModule } from '@jsverse/transloco';
import { provideIcons } from '@ng-icons/core';
import { NgIcon } from '@ng-icons/core';
import { MenuItem } from '../../shared/types/common.types';
import {
  lucideHouse,
  lucideLayers,
  lucideMenu,
  lucideUser,
  lucideLogOut,
  lucideSearch,
  lucideHardDrive,
  lucideServer,
  lucideLayoutDashboard,
  lucideSiren,
  lucideCog,
  lucideChartColumnStacked,
  lucideChevronDown,
  lucideChevronRight,
  lucideGrip,
  lucideZap,
  lucideActivity,
} from '@ng-icons/lucide';
import { HlmIconDirective } from '@spartan-ng/ui-icon-helm';
import { HlmSidebarComponent } from '../../../../libs/ui/ui-sidebar-helm/src/lib/hlm-sidebar.component';
import { HlmSidebarContentDirective } from '../../../../libs/ui/ui-sidebar-helm/src/lib/hlm-sidebar-content.directive';
import { HlmSidebarTriggerComponent } from '../../../../libs/ui/ui-sidebar-helm/src/lib/hlm-sidebar-trigger.component';
import { HlmSidebarHeaderDirective } from '../../../../libs/ui/ui-sidebar-helm/src/lib/hlm-sidebar-header.directive';
import { HlmSidebarMenuDirective } from '../../../../libs/ui/ui-sidebar-helm/src/lib/hlm-sidebar-menu.directive';
import { HlmSidebarMenuItemDirective } from '../../../../libs/ui/ui-sidebar-helm/src/lib/hlm-sidebar-menu-item.directive';
import { HlmSidebarFooterDirective } from '../../../../libs/ui/ui-sidebar-helm/src/lib/hlm-sidebar-footer.directive';
import { HlmSidebarService } from '../../../../libs/ui/ui-sidebar-helm/src/lib/hlm-sidebar.service';

import { AppHeaderComponent } from '../../components/app-header/app-header.component';
import { NgIf, NgFor } from '@angular/common';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [
    RouterLink,
    RouterLinkActive,
    RouterOutlet,
    TranslocoModule,
    NgIcon,
    HlmIconDirective,
    HlmSidebarComponent,
    HlmSidebarContentDirective,
    HlmSidebarTriggerComponent,
    HlmSidebarHeaderDirective,
    HlmSidebarMenuDirective,
    HlmSidebarMenuItemDirective,
    HlmSidebarFooterDirective,
    AppHeaderComponent,
    NgIf,
    NgFor,
  ],
  providers: [
    provideIcons({
      lucideHouse,
      lucideLayers,
      lucideMenu,
      lucideUser,
      lucideLogOut,
      lucideSearch,
      lucideHardDrive,
      lucideServer,
      lucideLayoutDashboard,
      lucideSiren,
      lucideCog,
      lucideChartColumnStacked,
      lucideChevronDown,
      lucideChevronRight,
      lucideGrip,
      lucideZap,
      lucideActivity,
    }),
  ],
  templateUrl: './main-layout.component.html',
})
export class MainLayoutComponent implements OnInit {
  private readonly platformId = inject(PLATFORM_ID);
  currentRoute: string | null = null;
  showSubmenuOnHover: MenuItem | null = null;

  menuItems: MenuItem[] = [
    {
      label: null,
      icon: null,
      route: '',
      items: [
        {
          label: 'overview',
          icon: 'lucideGrip',
          route: '/overview',
        },
        { label: 'cog', icon: 'lucideCog', route: '/cog' },
        { label: 'k8s', icon: 'lucideLayoutDashboard', route: '/k8s' },
        { label: 'energy_metrics', icon: 'lucideZap', route: '/energy-metrics' },
      ],
    },
    {
      label: null,
      icon: null,
      route: '/emdc',
      items: [
        {
          label: 'workloads',
          icon: 'lucideLayers',
          route: '/workloads',
          items: [
            {
              label: 'request_decisions',
              icon: null,
              route: '/request_decisions',
            },
            { label: 'actions', icon: null, route: '/actions' },
            { label: 'System Utilization', icon: null, route: '/system-utilization' },
            { label: 'workload_deployment', icon: null, route: '/workload-deployment' },
            { label: 'Register Workload', icon: null, route: '/register-workload' },
          ],
        },
        { label: 'alerts', icon: 'lucideSiren', route: '/alerts' },
        {
          label: 'monitoring',
          icon: 'lucideChartColumnStacked',
          route: '/monitoring',
        },
      ],
    },
  ];

  constructor(
    public sidebarService: HlmSidebarService
  ) {}

  ngOnInit(): void {
    // Removed getClusterInfo() call - it should only be called on the overview page
  }

  toggleSubmenu(item: MenuItem): void {
    item.expanded = !item.expanded;
  }

  onMenuItemHover(item: MenuItem): void {
    if (
      this.sidebarService.state() === 'collapsed' &&
      item.items &&
      item.items.length > 0
    ) {
      this.showSubmenuOnHover = item;
    }
  }

  onMenuItemLeave(): void {
    if (this.sidebarService.state() === 'collapsed') {
      this.showSubmenuOnHover = null;
    }
  }

  resolveRoute(groupRoute: string, itemRoute: string, subItemRoute?: string): string {
    const parts = [groupRoute || '', itemRoute || '', subItemRoute || '']
      .map((p) => String(p));
    let url = parts.join('');
    url = url.replace(/\/{2,}/g, '/');
    if (!url.startsWith('/')) {
      url = '/' + url;
    }
    return url;
  }
}
