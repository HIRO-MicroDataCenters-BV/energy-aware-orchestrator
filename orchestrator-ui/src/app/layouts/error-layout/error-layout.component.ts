import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { TranslocoModule } from '@jsverse/transloco';

@Component({
  selector: 'app-error-layout',
  standalone: true,
  imports: [
    RouterOutlet,
    TranslocoModule
  ],
  templateUrl: './error-layout.component.html'
})
export class ErrorLayoutComponent {}