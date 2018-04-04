from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily, REGISTRY
from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

import yaml
import time, httplib2, os


METRIC_PREFIX = 'ga_reporting'
LABELS = ['view_id', 'service_email']


class GarCollector(object):
  def __init__(account={},
               metrics=[],
               start_date='',
               scopes=[],
               discovery=(),
               bind_port=port):
    self.account = account
    self._metrics = metrics
    self.start_date = start_date
    self.scopes = scopes
    self.discovery = discovery

  def collect(self):
    analytics = self._initialize_analyticsreporting()
    response = self._get_report(analytics)
    self._get_metrics(response)

    for metric in self._gauges:
      yield self._gauges[metric]

  def _initialize_analyticsreporting(self):
    credentials = ServiceAccountCredentials.from_p12_keyfile(
      self.account['email'], self.account['key_file'], scopes=self.scopes)

    http = credentials.authorize(httplib2.Http())
    analytics = build('analytics', 'v4', http=http, discoveryServiceUrl=self.discovery)

    return analytics

  @property
  def date_ranges(self):
    return [{'startDate': str(self.start_date), 'endDate': 'today'}]

  @property
  def metrics(self):
    return [{'expression': metric} for metric in self._metrics]

  def _get_report(self, analytics):
    return analytics.reports().batchGet(
        body={
          'reportRequests': [
          {
            'viewId': self.view_id,
            'dateRanges': self.date_ranges,
            'metrics': self.metrics
          }]
        }
    ).execute()

  def _get_metrics(self, response):
    self._gauges = {}

    for report in response.get('reports', []):
      columnHeader = report.get('columnHeader', {})
      dimensionHeaders = columnHeader.get('dimensions', [])
      metricHeaders = columnHeader.get('metricHeader', {}).get('metricHeaderEntries', [])
      rows = report.get('data', {}).get('rows', [])

      for row in rows:
        dimensions = row.get('dimensions', [])
        dateRangeValues = row.get('metrics', [])

        for header, dimension in zip(dimensionHeaders, dimensions):
          print(header + ': ' + dimension)

        for i, values in enumerate(dateRangeValues):
          print('Date range (' + str(i) + ')')

          for metricHeader, returnValue in zip(metricHeaders, values.get('values')):
            metric = metricHeader.get('name')[3:]
            print(metric + ': ' + returnValue)
            self._gauges[metric] = GaugeMetricFamily('%s_%s' % (METRIC_PREFIX, metric), '%s' % metric, value=None, labels=LABELS)
            self._gauges[metric].add_metric([self.account['view_id'], self.account['email']], value=float(returnValue))


if __name__ == '__main__':
  with open(os.getenv('CONFIG', './default.config.yml'), 'r') as config_file:
    config = yaml.load(config_file)
    start_http_server(int(config.get('bind_port', 9173)))
    REGISTRY.register(GarCollector(**config))

    while True: time.sleep(1)
