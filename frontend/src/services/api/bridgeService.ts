import { BridgeAsset, PortfolioSummary } from '../../types/bridge';
import { MOCK_BRIDGES } from '../../mock/bridges';
import { MOCK_SUMMARY } from '../../mock/summary';

export const bridgeService = {
  async getPortfolioSummary(): Promise<PortfolioSummary> {
    await new Promise(resolve => setTimeout(resolve, 150));
    return { ...MOCK_SUMMARY };
  },

  async getAllBridges(): Promise<BridgeAsset[]> {
    await new Promise(resolve => setTimeout(resolve, 150));
    return [...MOCK_BRIDGES];
  },

  async getBridgeById(id: string): Promise<BridgeAsset | null> {
    await new Promise(resolve => setTimeout(resolve, 150));
    const bridge = MOCK_BRIDGES.find(b => b.id.toLowerCase() === id.toLowerCase());
    return bridge ? { ...bridge } : null;
  },

  async getTopPriorityBridges(limit: number = 5): Promise<BridgeAsset[]> {
    await new Promise(resolve => setTimeout(resolve, 150));
    return [...MOCK_BRIDGES]
      .sort((a, b) => b.priorityScore - a.priorityScore)
      .slice(0, limit);
  }
};
