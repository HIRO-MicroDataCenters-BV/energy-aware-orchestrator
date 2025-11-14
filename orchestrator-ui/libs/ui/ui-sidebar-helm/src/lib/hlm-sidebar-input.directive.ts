import { Directive, ElementRef, computed, OnInit } from '@angular/core';
import { hlm } from '@spartan-ng/brain/core';
import { HlmInputDirective, inputVariants } from '@spartan-ng/ui-input-helm';

@Directive({
  selector: 'input[hlmSidebarInput]',
  standalone: true,
  host: {
    'data-sidebar': 'input',
    '[class]': '_computedClass()',
  },
})
export class HlmSidebarInputDirective
  extends HlmInputDirective
  implements OnInit
{
  override readonly _computedClass = computed(() =>
    hlm(
      inputVariants({ size: this.size(), error: this.state().error() }),
      'h-8 w-full bg-background shadow-none focus-visible:ring-2 focus-visible:ring-sidebar-ring',
      this.userClass(),
    ),
  );

  constructor(private element: ElementRef<HTMLInputElement>) {
    super();
  }

  ngOnInit() {
    if (this.element.nativeElement.tagName.toLowerCase() !== 'input') {
      console.warn(
        'hlmSidebarInput directive should only be used on <input> elements',
      );
    }
  }
}
