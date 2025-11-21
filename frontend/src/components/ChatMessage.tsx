type ChatMessageProps = {
  role: "user" | "assistant";
  content: string;
};

export function ChatMessage({ role, content }: ChatMessageProps) {
  const isUser = role === "user";
  const bubbleColors = isUser
    ? "bg-sky-600 text-white"
    : "bg-white text-slate-900 border border-slate-200";
  const alignment = isUser ? "justify-end" : "justify-start";

  return (
    <div className={`flex ${alignment}`}>
      <div
        className={`max-w-xl rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap shadow ${bubbleColors}`}
      >
        {content}
      </div>
    </div>
  );
}
