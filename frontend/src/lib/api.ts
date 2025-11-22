export type ChatRole = "user" | "assistant";

export type ChatMessagePayload = {
  role: ChatRole;
  content: string;
  cards?: CardSummary[];
};

export type CardSummary = {
  card_id: string;
  name: string;
  class: string;
  rarity: string;
  cost: number;
  attack: number;
  hp: number;
  effect: string;
  keywords: string[];
  image_before: string;
  image_after: string;
};

export type ChatResponse = {
  answer: string;
  meta: {
    used_context_count: number;
    cards?: CardSummary[];
  };
};

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

export async function sendChatMessage(
  message: string,
  history: ChatMessagePayload[]
): Promise<ChatResponse> {
  const endpoint = `${API_BASE_URL}/api/v1/chat`;
  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message, history }),
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const errorBody = await response.json();
      detail = errorBody?.detail || detail;
    } catch (error) {
      // ignore JSON parse issues and fall back to status text
    }
    throw new Error(`API error: ${detail}`);
  }

  return response.json();
}
