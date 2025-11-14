import { Component, OnInit, OnDestroy } from '@angular/core';
import { AppTableComponent } from '../../../components/app-table/app-table.component';
import { TranslocoModule } from '@jsverse/transloco';
import { ApiService } from '../../../core/services';
import { Observable, Subscription } from 'rxjs';
import { NgIf } from '@angular/common';
import { filter } from 'rxjs/operators';
import {
  Router,
  ActivatedRoute,
  NavigationEnd,
  RouterOutlet,
} from '@angular/router';

import alertsData from '../../../mock/alerts_response.json';

@Component({
  selector: 'app-alerts',
  standalone: true,
  imports: [AppTableComponent, TranslocoModule, NgIf, RouterOutlet],
  templateUrl: './alerts.component.html',
})
export class AlertsComponent implements OnInit, OnDestroy {
  showParentContent = true;
  private routerSubscription: Subscription | null = null;
  clusters = [];
  columns = ['id', 'alert_description', 'alert_type', 'alert_model', 'time'];
  actions = [];

  tabs = [];

  dataSource: Observable<unknown[]> | null = null;
  staticData: unknown[] | null = null;

  detailsStruct: any[] = [];

  constructor(
    apiService: ApiService,
    private router: Router,
    private activatedRoute: ActivatedRoute
  ) {
    this.staticData = alertsData;
    this.dataSource = apiService.getAlerts();
    this.detailsStruct = [
      {
        title: 'alert_details',
        items: [
          {
            icon: 'circle_dot',
            prop: 'alert_type',
          },
          {
            icon: 'calendar',
            prop: 'date',
          },
          {
            icon: 'time',
            prop: 'time',
          },
          {
            icon: 'hard_drive',
            prop: 'node_id',
            condition: {
              prop: 'alert_type',
              if: 'neq',
              value: 'network-attack',
            },
          },
          {
            icon: 'package',
            prop: 'pod_id',
            condition: {
              prop: 'alert_type',
              if: 'neq',
              value: 'network-attack',
            },
          },
          {
            icon: 'text',
            prop: 'source_ip',
            condition: {
              prop: 'alert_type',
              if: 'eq',
              value: 'network-attack',
            },
          },
          {
            icon: 'text',
            prop: 'source_port',
            condition: {
              prop: 'alert_type',
              if: 'eq',
              value: 'network-attack',
            },
          },
          {
            icon: 'text',
            prop: 'destination_ip',
            condition: {
              prop: 'alert_type',
              if: 'eq',
              value: 'network-attack',
            },
          },
          {
            icon: 'text',
            prop: 'destination_port',
            condition: {
              prop: 'alert_type',
              if: 'eq',
              value: 'network-attack',
            },
          },
        ],
      },
      {
        title: 'ai_summary',
        items: [
          {
            icon: 'bot',
            prop: 'alert_model',
          },
          {
            icon: 'text',
            prop: 'alert_description',
          },
        ],
      },
    ];
  }
  ngOnInit(): void {
    this.checkCurrentRoute();
    this.routerSubscription = this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe(() => {
        this.checkCurrentRoute();
      });
  }

  ngOnDestroy(): void {
    this.routerSubscription?.unsubscribe();
  }

  checkCurrentRoute() {
    this.showParentContent = !this.activatedRoute.firstChild;
  }
}
