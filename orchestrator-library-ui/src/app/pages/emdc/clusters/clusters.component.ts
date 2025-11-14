import { Component } from '@angular/core';
import { AppTableComponent } from '../../../components/app-table/app-table.component';
import { TranslocoModule } from '@jsverse/transloco';

@Component({
  selector: 'app-clusters',
  standalone: true,
  imports: [AppTableComponent, TranslocoModule],
  templateUrl: './clusters.component.html',
})
export class ClustersComponent {
  clusters = [];
  columns = [
    'cluster_name',
    'status',
    'workloads',
    'nodes',
    'cpu_usage',
    'memory_usage',
  ];
  actions = [
    'view_details',
    'view_logs',
    'scale_cluster',
    'add_nodes',
    'cordon_cluster',
    'drain_cluster',
    'delete_cluster',
  ];
}
