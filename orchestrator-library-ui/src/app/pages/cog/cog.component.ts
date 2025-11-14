import { Component, OnInit, inject } from '@angular/core';
import { SafePipe } from '../../pipes/safe.pipe';
import { AuthService } from '../../core/services/auth/auth.service';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-cog',
  standalone: true,
  imports: [SafePipe],
  template: `<iframe
    [src]="cogUrl | safe : 'resourceUrl'"
    frameborder="0"
    allowfullscreen
  ></iframe>`,
  styleUrls: ['./cog.component.scss'],
})
export class CogComponent implements OnInit {
  private readonly authService = inject(AuthService);

  cogUrl = '';

  ngOnInit(): void {
    const token = this.authService.getAccessToken();
    const baseUrl = environment.cogUrl;

    if (token) {
      const separator = baseUrl.includes('?') ? '&' : '?';
      this.cogUrl = `${baseUrl}${separator}access_token=${encodeURIComponent(
        token
      )}`;
    } else {
      this.cogUrl = baseUrl;
    }
  }
}
