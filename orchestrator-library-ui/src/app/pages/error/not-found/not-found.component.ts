import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TranslocoModule } from '@jsverse/transloco';
import { HlmButtonDirective } from '@spartan-ng/ui-button-helm';

@Component({
  selector: 'app-not-found',
  standalone: true,
  imports: [
    RouterLink,
    TranslocoModule,
    HlmButtonDirective
  ],
  templateUrl: './not-found.component.html'
})
export class NotFoundComponent {}