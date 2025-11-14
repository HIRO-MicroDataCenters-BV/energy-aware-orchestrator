import { inject, Injectable, isDevMode } from '@angular/core';
import {
  Translation,
  TranslocoLoader,
  TranslocoConfig,
} from '@jsverse/transloco';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class TranslocoHttpLoader implements TranslocoLoader {
  private http = inject(HttpClient);

  getTranslation(lang: string): Observable<Translation> {
    return this.http.get<Translation>(`./assets/i18n/${lang}.json`);
  }
}

export function getTranslocoConfig(): {
  config: Partial<TranslocoConfig>;
  loader: typeof TranslocoHttpLoader;
} {
  return {
    config: {
      availableLangs: ['en'],
      defaultLang: 'en',
      reRenderOnLangChange: true,
      prodMode: !isDevMode(),
    },
    loader: TranslocoHttpLoader,
  };
}
