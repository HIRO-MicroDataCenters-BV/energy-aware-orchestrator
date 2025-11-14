import { Directive, computed, input } from '@angular/core';
import { hlm } from '@spartan-ng/brain/core';
import type { ClassValue } from 'clsx';

@Directive({
  selector: '[hlmSheetClose],[brnSheetClose][hlm]',
  host: {
    '[class]': '_computedClass()',
  },
})
export class HlmSheetCloseDirective {
  public readonly userClass = input<ClassValue>('', { alias: 'class' });
  protected readonly _computedClass = computed(() =>
    hlm('h-8 w-8 absolute top-4 right-2 !outline-0', this.userClass())
  );
}
