import { NgFor, NgIf } from '@angular/common';
import { Component } from '@angular/core';
import { Router, NavigationEnd, RouterLink } from '@angular/router';
import { TranslocoModule } from '@jsverse/transloco';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideChevronRight } from '@ng-icons/lucide';
import { HlmIconDirective } from '@spartan-ng/ui-icon-helm';
import { distinctUntilChanged, filter, map, startWith } from 'rxjs';
import { BreadcrumbItem } from '../../shared/models';
import { generateBreadcrumbs } from '../../shared/utils/navigation.utils';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [RouterLink, TranslocoModule, NgIcon, HlmIconDirective, NgFor, NgIf],
  templateUrl: './app-header.component.html',
  providers: [
    provideIcons({
      lucideChevronRight,
    }),
  ],
})
export class AppHeaderComponent {
  currentRoute: string | null = null;
  breadcrumbs: BreadcrumbItem[] = [];

  constructor(private router: Router) {
    this.router.events
      .pipe(
        startWith(this.router.url),
        filter(
          (event) => typeof event === 'string' || event instanceof NavigationEnd
        ),
        map(() => this.router.url),
        distinctUntilChanged()
      )
      .subscribe((url) => {
        this.generateBreadcrumbs(url);
      });
  }

  private generateBreadcrumbs(url: string): void {
    this.breadcrumbs = generateBreadcrumbs(url);
  }
}
