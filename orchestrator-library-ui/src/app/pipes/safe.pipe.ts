import { Pipe, PipeTransform } from '@angular/core';
import {
  DomSanitizer,
  SafeHtml,
  SafeResourceUrl,
  SafeScript,
  SafeStyle,
  SafeUrl,
} from '@angular/platform-browser';

@Pipe({
  name: 'safe',
  standalone: true,
})
export class SafePipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) {}

  transform(
    value: unknown,
    type: string
  ): SafeHtml | SafeStyle | SafeScript | SafeUrl | SafeResourceUrl {
    const stringValue = String(value);
    switch (type) {
      case 'html':
        return this.sanitizer.bypassSecurityTrustHtml(stringValue);
      case 'style':
        return this.sanitizer.bypassSecurityTrustStyle(stringValue);
      case 'script':
        return this.sanitizer.bypassSecurityTrustScript(stringValue);
      case 'url':
        return this.sanitizer.bypassSecurityTrustUrl(stringValue);
      case 'resourceUrl':
        return this.sanitizer.bypassSecurityTrustResourceUrl(stringValue);
      default:
        return this.sanitizer.bypassSecurityTrustResourceUrl(stringValue);
    }
  }
}
