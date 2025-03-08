export interface BrowsingTask {
  url: string;
  instruction: string;
}

export interface ChatMessage {
  id: string;
  content: string;
  type: 'user' | 'agent';
  timestamp: number;
}

export interface ScreenshotData {
  imageData: string;
  timestamp: number;
}

export interface StatusUpdate {
  status: string;
  timestamp: number;
}

export interface ActionUpdate {
  action: string;
  details: Record<string, any>;
  timestamp: number;
}

export interface MessageUpdate {
  content: string;
  thinking?: string;
  timestamp: number;
}

export interface ErrorUpdate {
  message: string;
  timestamp: number;
}

export type WebSocketUpdate =
  | { type: 'screenshot'; image_data: string; timestamp: number }
  | { type: 'message'; content: string; thinking?: string; timestamp: number }
  | { type: 'action'; action: string; details: Record<string, any>; timestamp: number }
  | { type: 'status'; status: string; timestamp: number }
  | { type: 'error'; message: string; timestamp: number }
  | { type: 'ping'; timestamp: number }; 