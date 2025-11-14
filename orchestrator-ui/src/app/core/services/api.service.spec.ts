import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { ApiService } from './api.service';

describe('ApiService', () => {
  let service: ApiService;
  let httpMock: HttpTestingController;
  const baseUrl = 'http://51.44.28.47:30015';

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ApiService],
    });
    service = TestBed.inject(ApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('listPods', () => {
    it('should fetch pods list', () => {
      const mockPods = [
        { name: 'pod1', status: 'Running' },
        { name: 'pod2', status: 'Pending' },
      ];

      service.listPods().subscribe((pods) => {
        expect(pods).toEqual(mockPods);
      });

      const req = httpMock.expectOne(`${baseUrl}/k8s_pod/`);
      expect(req.request.method).toBe('GET');
      req.flush(mockPods);
    });

    it('should handle query parameters', () => {
      const params = { namespace: 'default' };

      service.listPods(params).subscribe();

      const req = httpMock.expectOne(`${baseUrl}/k8s_pod/?namespace=default`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('listNodes', () => {
    it('should fetch nodes list', () => {
      const mockNodes = [
        { name: 'node1', status: 'Ready' },
        { name: 'node2', status: 'NotReady' },
      ];

      service.listNodes().subscribe((nodes) => {
        expect(nodes).toEqual(mockNodes);
      });

      const req = httpMock.expectOne(`${baseUrl}/k8s_node/`);
      expect(req.request.method).toBe('GET');
      req.flush(mockNodes);
    });
  });

  describe('getClusterInfo', () => {
    it('should fetch cluster information', () => {
      const mockClusterInfo = {
        cluster_name: 'test-cluster',
        version: '1.21.0',
      };

      service.getClusterInfo().subscribe((info) => {
        expect(info).toEqual(mockClusterInfo);
      });

      const req = httpMock.expectOne(`${baseUrl}/k8s_cluster_info/`);
      expect(req.request.method).toBe('GET');
      req.flush(mockClusterInfo);
    });
  });

  describe('loading state', () => {
    it('should set loading to true during request', () => {
      const loadingStates: boolean[] = [];

      service.loading$.subscribe((loading) => {
        loadingStates.push(loading);
      });

      service.listPods().subscribe();

      const req = httpMock.expectOne(`${baseUrl}/k8s_pod/`);
      req.flush([]);

      expect(loadingStates).toContain(true);
      expect(loadingStates[loadingStates.length - 1]).toBe(false);
    });
  });

  describe('error handling', () => {
    it('should handle HTTP errors gracefully', () => {
      service.listPods().subscribe({
        next: () => fail('should have failed'),
        error: (error) => {
          expect(error).toBeTruthy();
        },
      });

      const req = httpMock.expectOne(`${baseUrl}/k8s_pod/`);
      req.flush('Error', { status: 500, statusText: 'Internal Server Error' });
    });
  });
});
