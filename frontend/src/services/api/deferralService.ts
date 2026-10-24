import { DeferralPortfolioReport } from '../../types/deferral';
import { MOCK_DEFERRAL_REPORT } from '../../mock/deferral';

export const deferralService = {
  async getDeferralReport(): Promise<DeferralPortfolioReport> {
    await new Promise(resolve => setTimeout(resolve, 150));
    return { ...MOCK_DEFERRAL_REPORT };
  }
};
