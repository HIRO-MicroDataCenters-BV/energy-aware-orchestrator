export interface EnergyDataPoint {
  timestamp: number;
  actual?: number;
  predicted?: number;
  nodeName: string;
}

export interface NodeEnergyData {
  nodeName: string;
  historical: EnergyDataPoint[];
  predictions: EnergyDataPoint[];
}