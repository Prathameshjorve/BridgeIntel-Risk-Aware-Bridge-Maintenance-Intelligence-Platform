import { BridgeAsset } from './bridge';

export interface RouteSegment {
  id: string;
  name: string;
  trafficVolumeADT: number;
  importance: 'Primary Arterial' | 'Secondary Connector' | 'Emergency Evacuation Route';
  coordinates: [number, number][]; // [lat, lng]
}

export interface CriticalFacility {
  id: string;
  name: string;
  type: 'Trauma Center' | 'Fire & Rescue HQ' | 'Port / Logistics Hub' | 'Power Substation';
  latitude: number;
  longitude: number;
  dependentBridgeIds: string[];
}

export interface NetworkGraphData {
  bridges: BridgeAsset[];
  routes: RouteSegment[];
  facilities: CriticalFacility[];
  maxDetourKm: number;
  totalDetourVehicleHoursPerDay: number;
}
