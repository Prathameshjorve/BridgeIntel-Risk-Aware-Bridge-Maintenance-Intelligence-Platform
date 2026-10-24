import { MOCK_BRIDGES } from './bridges';
import { NetworkGraphData, CriticalFacility, RouteSegment } from '../types/network';

export const MOCK_FACILITIES: CriticalFacility[] = [
  {
    id: "FAC-01",
    name: "Tri-County Regional Trauma Center (Level I)",
    type: "Trauma Center",
    latitude: 36.8520,
    longitude: -83.3100,
    dependentBridgeIds: ["BR-NBI-04821", "BR-NBI-03482"]
  },
  {
    id: "FAC-02",
    name: "Metro District Fire & Emergency HQ",
    type: "Fire & Rescue HQ",
    latitude: 36.9080,
    longitude: -83.2500,
    dependentBridgeIds: ["BR-NBI-01934", "BR-NBI-07823"]
  },
  {
    id: "FAC-03",
    name: "Inland Port Intermodal Container Terminal",
    type: "Port / Logistics Hub",
    latitude: 36.9400,
    longitude: -83.2050,
    dependentBridgeIds: ["BR-NBI-02108", "BR-NBI-08920"]
  },
  {
    id: "FAC-04",
    name: "Highland Community Health Station",
    type: "Trauma Center",
    latitude: 36.7750,
    longitude: -83.4200,
    dependentBridgeIds: ["BR-NBI-07119", "BR-NBI-05512"]
  }
];

export const MOCK_ROUTES: RouteSegment[] = [
  {
    id: "RT-01",
    name: "Interstate 80 Commercial Freight Spine",
    trafficVolumeADT: 78000,
    importance: "Emergency Evacuation Route",
    coordinates: [[36.950, -83.220], [36.945, -83.184], [36.938, -83.150]]
  },
  {
    id: "RT-02",
    name: "Interstate Bypass 205 Urban Loop",
    trafficVolumeADT: 62000,
    importance: "Primary Arterial",
    coordinates: [[36.920, -83.260], [36.912, -83.245], [36.905, -83.230]]
  },
  {
    id: "RT-03",
    name: "State Highway 17 Valley Access",
    trafficVolumeADT: 38500,
    importance: "Primary Arterial",
    coordinates: [[36.870, -83.340], [36.845, -83.321], [36.820, -83.300]]
  },
  {
    id: "RT-04",
    name: "Rural Route 8 Mountain Link",
    trafficVolumeADT: 6200,
    importance: "Secondary Connector",
    coordinates: [[36.790, -83.430], [36.782, -83.415], [36.760, -83.390]]
  }
];

export const MOCK_NETWORK_DATA: NetworkGraphData = {
  bridges: MOCK_BRIDGES,
  routes: MOCK_ROUTES,
  facilities: MOCK_FACILITIES,
  maxDetourKm: 42.5,
  totalDetourVehicleHoursPerDay: MOCK_BRIDGES.reduce((sum, b) => sum + b.dailyDetourDelayVehicleHours, 0)
};
