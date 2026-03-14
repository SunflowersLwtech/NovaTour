export interface VoiceEvent {
  type:
    | "audio"
    | "transcript"
    | "tool_call"
    | "itinerary"
    | "interruption"
    | "error"
    | "lod_change"
    | "booking_progress"
    | "voice_state";
  data?: string;
  text?: string;
  role?: "user" | "assistant";
  is_final?: boolean;
  name?: string;
  input?: Record<string, unknown>;
  status?: string;
  result?: string;
  message?: string;
  level?: number;
  step?: string;
  screenshot?: string;
  state?: string;
}

export interface BookingProgress {
  step: string;
  screenshot?: string;
  status: "searching" | "found" | "booking" | "complete" | "error";
}

export interface TranscriptMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: number;
  is_final: boolean;
}

export interface ToolCallInfo {
  name: string;
  status: "calling" | "complete";
  input?: Record<string, unknown>;
  result?: string;
  timestamp: number;
}

export interface ItineraryData {
  destination: string;
  days: number;
  itinerary: DayPlan[];
  budget_estimate?: Record<string, string>;
  mock?: boolean;
}

export interface DayPlan {
  day: number;
  theme: string;
  activities: Activity[];
}

export interface Activity {
  time: string;
  activity: string;
  location: string;
  duration: string;
  latitude?: number;
  longitude?: number;
  photo_url?: string;
}
