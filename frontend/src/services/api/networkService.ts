import { NetworkGraphData } from '../../types/network';
import { MOCK_NETWORK_DATA } from '../../mock/network';

export const networkService = {
  async getNetworkData(): Promise<NetworkGraphData> {
    await new Promise(resolve => setTimeout(resolve, 150));
    return { ...MOCK_NETWORK_DATA };
  }
};
