import { Component, OnInit, Input } from '@angular/core';
import { NgFor, NgIf, DatePipe } from '@angular/common';
import { TranslocoModule } from '@jsverse/transloco';
import { getDuration } from '../../shared';
import { HlmScrollAreaDirective } from '@spartan-ng/ui-scrollarea-helm';

import {
  lucideArrowUpDown,
  lucideChevronDown,
  lucideCog,
  lucideDownload,
  lucideEllipsisVertical,
  lucideInfo,
  lucidePause,
  lucidePlus,
  lucideTerminal,
  lucideTrash2,
  lucideCircleCheck,
  lucideTriangleAlert,
  lucideCircleX,
  lucideCircle,
  lucideCalendarClock,
  lucideTimer,
  lucidePackage,
  lucideText,
  lucideLayers,
  lucideCalendar,
  lucideClock,
  lucideHardDrive,
  lucideBot,
  lucideMemoryStick,
  lucideCpu,
  lucideListTree,
} from '@ng-icons/lucide';
import { NgIcon, provideIcons } from '@ng-icons/core';

interface Condition {
  prop: string;
  if: 'eq' | 'neq';
  value: string;
}

interface StructItem {
  icon: string;
  prop: string;
  condition?: Condition;
}

interface Struct {
  title: string | null;
  items: StructItem[];
}

interface Data {
  [keys: string]: any;
}

@Component({
  selector: 'app-details',
  standalone: true,
  imports: [TranslocoModule, NgFor, NgIf, DatePipe, NgIcon],
  providers: [
    provideIcons({
      lucideChevronDown,
      lucideEllipsisVertical,
      lucideArrowUpDown,
      lucideInfo,
      lucideDownload,
      lucideTerminal,
      lucidePlus,
      lucideCog,
      lucidePause,
      lucideTrash2,
      lucideCircleCheck,
      lucideTriangleAlert,
      lucideCircleX,
      lucideCircle,
      lucideCalendarClock,
      lucideTimer,
      lucidePackage,
      lucideText,
      lucideLayers,
      lucideCalendar,
      lucideClock,
      lucideHardDrive,
      lucideBot,
      lucideMemoryStick,
      lucideCpu,
      lucideListTree,
    }),
  ],
  styleUrls: ['./app-details.component.css'],
  templateUrl: './app-details.component.html',
})
export class AppDetailsComponent {
  @Input('struct') struct: Struct[] = [];
  @Input('data') data: Data | null = null;

  testCondition(prop: string, data: any, condition: Condition | undefined) {
    if (condition === undefined) {
      return true;
    }
    const value =
      typeof data[condition.prop] == 'string'
        ? data[condition.prop].toLowerCase()
        : data[prop];

    const condValue = condition.value;

    const condIf = condition.if;

    switch (condIf) {
      case 'eq':
        if (condValue == value) {
          return true;
        }
        break;
      case 'neq':
        if (condValue != value) {
          return true;
        }
        break;
      default:
        return false;
    }
    return false;
  }

  getIcon(name: string) {
    return {
      circle_dot: lucideCircle,
      circle_check: lucideCircleCheck,
      calendar_clock: lucideCalendarClock,
      timer: lucideTimer,
      layers: lucideLayers,
      text: lucideText,
      package: lucidePackage,
      hard_drive: lucideHardDrive,
      bot: lucideBot,
      time: lucideClock,
      calendar: lucideCalendar,
      memory_stick: lucideMemoryStick,
      cpu: lucideCpu,
      list_tree: lucideListTree,
    }[name];
  }

  getDuration(start: string, end: string) {
    return getDuration(start, end);
  }

  getValueType(value: unknown): string {
    if (typeof value === 'boolean') {
      return 'boolean';
    } else if (typeof value === 'number') {
      return 'number';
    } else if (this.isDate(value)) {
      return 'date';
    } else {
      return 'string';
    }
  }

  isDate(value: unknown): boolean {
    if (typeof value !== 'string') return false;

    // Test ISO date
    const isoDateRegex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z?$/;
    if (isoDateRegex.test(value)) {
      const date = new Date(value);
      return !isNaN(date.getTime());
    }

    // Test other date formats
    if (value.includes('-') || value.includes('/')) {
      const date = new Date(value);
      return !isNaN(date.getTime()) && date.getFullYear() > 1900;
    }

    return false;
  }
}
