import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';

import { TranslocoModule } from '@jsverse/transloco';

@Component({
  selector: 'app-auth-layout',
  standalone: true,
  imports: [CommonModule, RouterOutlet, TranslocoModule],
  template: `
    <div
      class="min-h-screen bg-white dark:bg-slate-950 relative overflow-hidden"
    >
      <!-- Animated Background -->
      <div class="absolute inset-0 overflow-hidden">
        <!-- Primary gradient orb -->
        <div
          class="absolute top-1/4 -left-1/4 w-[500px] h-[500px] bg-gradient-to-br from-blue-400/20 via-violet-400/20 to-purple-400/20 dark:from-blue-600/30 dark:via-violet-600/30 dark:to-purple-600/30 rounded-full blur-3xl animate-pulse"
          style="animation-duration: 4s; animation-delay: 0s;"
        ></div>

        <!-- Secondary gradient orb -->
        <div
          class="absolute bottom-1/4 -right-1/4 w-[600px] h-[600px] bg-gradient-to-br from-emerald-400/20 via-teal-400/20 to-cyan-400/20 dark:from-emerald-600/30 dark:via-teal-600/30 dark:to-cyan-600/30 rounded-full blur-3xl animate-pulse"
          style="animation-duration: 6s; animation-delay: 2s;"
        ></div>

        <!-- Tertiary accent orb -->
        <div
          class="absolute top-3/4 left-1/3 w-[400px] h-[400px] bg-gradient-to-br from-pink-400/15 via-rose-400/15 to-orange-400/15 dark:from-pink-600/25 dark:via-rose-600/25 dark:to-orange-600/25 rounded-full blur-3xl animate-pulse"
          style="animation-duration: 8s; animation-delay: 4s;"
        ></div>

        <!-- Subtle grid overlay -->
        <div
          class="absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(0,0,0,0.15)_1px,transparent_0)] dark:bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.05)_1px,transparent_0)]"
          style="background-size: 20px 20px;"
        ></div>
      </div>

      <!-- Noise texture overlay -->
      <div
        class="absolute inset-0 opacity-[0.015] dark:opacity-[0.025]"
        style='background-image: url(&apos;data:image/svg+xml,%3Csvg viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg"%3E%3Cfilter id="noiseFilter"%3E%3CfeTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="4" stitchTiles="stitch"/%3E%3C/filter%3E%3Crect width="100%25" height="100%25" filter="url(%23noiseFilter)"/%3E%3C/svg%3E&apos;);'
      ></div>

      <!-- Main content -->
      <div class="relative z-10 min-h-screen">
        <router-outlet></router-outlet>
      </div>

      <!-- Bottom gradient fade -->
      <div
        class="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-white/50 to-transparent dark:from-slate-950/50 pointer-events-none"
      ></div>
    </div>
  `,
  styles: [
    `
      @keyframes float {
        0%,
        100% {
          transform: translateY(0px) rotate(0deg);
        }
        33% {
          transform: translateY(-10px) rotate(1deg);
        }
        66% {
          transform: translateY(5px) rotate(-1deg);
        }
      }

      .animate-float {
        animation: float 6s ease-in-out infinite;
      }
    `,
  ],
})
export class AuthLayoutComponent {}
