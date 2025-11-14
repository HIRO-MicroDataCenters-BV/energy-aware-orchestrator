import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslocoModule } from '@jsverse/transloco';
import { Subscription } from 'rxjs';
import { DashboardCardModel } from '../../shared/models/dashboard-card.model';
import { TranslocoService } from '@jsverse/transloco';

// App components
import { ApiService } from '../../core/services/api.service';
import { AppDashboardCardComponent } from '../../components/app-dashboard-card/app-dashboard-card.component';
import { ROUTES } from '../../shared/constants/app.constants';

@Component({
  selector: 'app-overview',
  standalone: true,
  imports: [CommonModule, TranslocoModule, AppDashboardCardComponent],
  templateUrl: './overview.component.html',
  styleUrls: ['./overview.component.scss'],
})
export class OverviewComponent implements OnInit, OnDestroy {
  private subscription = new Subscription();

  cards: DashboardCardModel[] = [];

  constructor(
    private apiService: ApiService,
    private translocoService: TranslocoService
  ) {}

  ngOnInit(): void {
    this.cards = [
      {
        key: 'cluster',
        title: 'card.cluster',
        type: 'metrics',
        dataSource: this.apiService.getClusterInfo({ advanced: false }),
        actions: [
          {
            label: 'action.view_details',
            link: ROUTES.K8S,
          },
        ],
      },
      {
        key: 'recent_alerts',
        title: 'card.recent_alerts',
        type: 'table',
        dataSource: this.apiService.getAlerts({ limit: 5 }),
        actions: [
          {
            label: 'action.view_all',
            link: ROUTES.EMDC.ALERTS,
          },
        ],
      },
      {
        key: 'recent_workload_request_decisions',
        title: 'card.recent_workload_request_decisions',
        type: 'table',
        dataSource: this.apiService.getWorkloadDecisions({ limit: 5 }),
        actions: [
          {
            label: 'action.view_all',
            link: ROUTES.EMDC.WORKLOADS.REQUEST_DECISIONS,
          },
        ],
      },
      {
        key: 'recent_served_models',
        title: 'card.recent_served_models',
        type: 'table',
        dataSource: this.apiService.getWorkloadActions(),
        actions: [
          {
            label: 'action.view_all',
            link: ROUTES.EMDC.WORKLOADS.ACTIONS,
          },
        ],
      },
    ];
  }

  ngOnDestroy(): void {
    this.subscription.unsubscribe();
  }
}
