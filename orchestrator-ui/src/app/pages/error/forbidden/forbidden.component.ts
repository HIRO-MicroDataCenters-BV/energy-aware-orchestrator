import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TranslocoModule } from '@jsverse/transloco';
import { HlmButtonDirective } from '@spartan-ng/ui-button-helm';

@Component({
  selector: 'app-forbidden',
  standalone: true,
  imports: [
    RouterLink,
    TranslocoModule,
    HlmButtonDirective
  ],
  template: `
    <div class="flex flex-col items-center justify-center min-h-screen p-4 text-center">
      <h1 class="text-9xl font-extrabold text-primary">403</h1>
      <h2 class="text-2xl font-semibold mt-4">{{ 'error.forbidden.title' | transloco }}</h2>
      <p class="mt-2 text-muted-foreground max-w-md">
        {{ 'error.forbidden.message' | transloco }}
      </p>
      <div class="mt-8">
        <a routerLink="/" hlmBtn>
          {{ 'error.forbidden.back_home' | transloco }}
        </a>
      </div>
    </div>
  `
})
export class ForbiddenComponent {}