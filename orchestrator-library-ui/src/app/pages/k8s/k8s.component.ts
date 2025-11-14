import { Component } from '@angular/core';
import { SafePipe } from '../../pipes/safe.pipe';

import { environment } from '../../../environments/environment';
import { ApiService } from '../../core/services/api.service';
import { K8S_CONSTANTS, STORAGE_KEYS } from '../../shared/constants';
import { setStorageItem, TokenStorage } from '../../shared/utils';

@Component({
  selector: 'app-k8s',
  standalone: true,
  imports: [SafePipe],
  template: `<div class="container">
    <iframe
      [src]="url | safe : 'resourceUrl'"
      frameborder="0"
      allowfullscreen
    ></iframe>
  </div>`,
  styleUrls: ['./k8s.component.scss'],
})
export class K8sComponent {
  url = environment.dashboardUrl;
  constructor(private apiService: ApiService) {
    // Get token from safe storage if available
    this.apiService
      .getK8sToken({
        namespace: K8S_CONSTANTS.DEFAULT_VALUES.NAMESPACE,
        service_account_name: K8S_CONSTANTS.DEFAULT_VALUES.SERVICE_ACCOUNT_NAME,
      })
      .subscribe((res) => {
        setStorageItem(STORAGE_KEYS.ACCESS_TOKEN, res.token);
        const token = TokenStorage.getAccessToken(STORAGE_KEYS.ACCESS_TOKEN);
        if (token) {
          this.url += '?token=' + token;
        }
      });
  }
}
