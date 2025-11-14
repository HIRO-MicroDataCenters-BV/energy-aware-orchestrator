import {
  Injectable,
  Signal,
  computed,
  signal,
  DestroyRef,
  inject,
} from '@angular/core';

@Injectable({ providedIn: 'root' })
export class HlmSidebarService {
  private readonly SIDEBAR_COOKIE_NAME = 'sidebar_state';
  private readonly SIDEBAR_COOKIE_MAX_AGE = 60 * 60 * 24 * 7; // 7 days in seconds
  private readonly SIDEBAR_KEYBOARD_SHORTCUT = 'b';
  private readonly MOBILE_BREAKPOINT = '768px';

  private _open = signal<boolean>(true);
  private _openMobile = signal<boolean>(false);
  private _isMobile = signal<boolean>(false);
  private _variant = signal<'sidebar' | 'floating' | 'inset'>('sidebar');
  private mediaQuery: MediaQueryList | null = null;

  readonly open: Signal<boolean> = this._open.asReadonly();
  readonly openMobile: Signal<boolean> = this._openMobile.asReadonly();
  readonly isMobile: Signal<boolean> = this._isMobile.asReadonly();
  readonly variant: Signal<'sidebar' | 'floating' | 'inset'> =
    this._variant.asReadonly();

  readonly state = computed<'expanded' | 'collapsed'>(() =>
    this._open() ? 'expanded' : 'collapsed',
  );

  constructor() {
    const destroyRef = inject(DestroyRef);

    if (typeof window === 'undefined' || typeof document === 'undefined')
      return;

    // Initialize from cookie
    const cookie = document.cookie
      .split('; ')
      .find((row) => row.startsWith(`${this.SIDEBAR_COOKIE_NAME}=`));

    if (cookie) {
      const value = cookie.split('=')[1];
      this._open.set(value === 'true');
    }

    // Initialize MediaQueryList
    this.mediaQuery = window.matchMedia(
      `(max-width: ${this.MOBILE_BREAKPOINT})`,
    );
    this._isMobile.set(this.mediaQuery.matches);

    // Add media query listener
    const mediaQueryHandler = (e: MediaQueryListEvent) => {
      this._isMobile.set(e.matches);
      // If switching from mobile to desktop, close mobile sidebar
      if (!e.matches) this._openMobile.set(false);
    };
    this.mediaQuery.addEventListener('change', mediaQueryHandler);

    // Add keyboard shortcut listener
    const keydownHandler = (event: KeyboardEvent) => {
      if (
        event.key === this.SIDEBAR_KEYBOARD_SHORTCUT &&
        (event.ctrlKey || event.metaKey)
      ) {
        event.preventDefault();
        this.toggleSidebar();
      }
    };
    window.addEventListener('keydown', keydownHandler);

    // Add resize listener with debounce
    let resizeTimeout: number;
    const resizeHandler = () => {
      if (resizeTimeout) window.clearTimeout(resizeTimeout);
      resizeTimeout = window.setTimeout(() => {
        if (this.mediaQuery) this._isMobile.set(this.mediaQuery.matches);
      }, 100);
    };
    window.addEventListener('resize', resizeHandler);

    // Cleanup listeners on destroy
    destroyRef.onDestroy(() => {
      if (this.mediaQuery)
        this.mediaQuery.removeEventListener('change', mediaQueryHandler);
      window.removeEventListener('keydown', keydownHandler);
      window.removeEventListener('resize', resizeHandler);
      if (resizeTimeout) window.clearTimeout(resizeTimeout);
    });
  }

  setOpen(open: boolean): void {
    this._open.set(open);
    document.cookie = `${this.SIDEBAR_COOKIE_NAME}=${open}; path=/; max-age=${this.SIDEBAR_COOKIE_MAX_AGE}`;
  }

  setOpenMobile(open: boolean): void {
    if (this._isMobile()) this._openMobile.set(open);
  }

  setVariant(variant: 'sidebar' | 'floating' | 'inset'): void {
    this._variant.set(variant);
  }

  toggleSidebar(): void {
    if (this._isMobile()) this._openMobile.update((value) => !value);
    else this.setOpen(!this._open());
  }
}
