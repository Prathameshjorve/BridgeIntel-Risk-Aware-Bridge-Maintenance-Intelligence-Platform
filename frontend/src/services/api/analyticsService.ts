import { AnalyticsReport } from '../../types/analytics';
import { MOCK_ANALYTICS_REPORT } from '../../mock/analytics';

export const analyticsService = {
  async getAnalyticsReport(): Promise<AnalyticsReport> {
    await new Promise(resolve => setTimeout(resolve, 150));
    return { ...MOCK_ANALYTICS_REPORT };
  }
};
