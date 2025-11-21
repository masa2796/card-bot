"use client";

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { ChatMessage } from "@/components/ChatMessage";
import { ChatMessagePayload, sendChatMessage } from "@/lib/api";

type Message = ChatMessagePayload & { id: string };

const initialMessage: Message = {
  id: "welcome",
  role: "assistant",
  content: "ゲーム攻略アシスタントへようこそ！カードに関する質問をどうぞ。",
};

export default function HomePage() {
  const [messages, setMessages] = useState<Message[]>([initialMessage]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (event?: FormEvent) => {
    event?.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
    };

    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setInput("");
    setIsLoading(true);

    try {
      const historyPayload = nextMessages.map(({ role, content }) => ({ role, content }));
      const response = await sendChatMessage(trimmed, historyPayload);
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.answer || "回答を生成できませんでした。",
      };
      setMessages((prev: Message[]) => [...prev, assistantMessage]);
    } catch (error) {
      const fallback: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "現在回答を生成できません。時間をおいて再度お試しください。",
      };
      setMessages((prev: Message[]) => [...prev, fallback]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSubmit();
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col px-4 py-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">gamechat-ai</h1>
        <p className="text-sm text-slate-500">ゲームカード攻略のためのシンプルな RAG チャット</p>
      </header>

      <section className="flex-1 overflow-y-auto rounded-2xl bg-slate-100 p-4">
        <div className="flex flex-col gap-4">
          {messages.map((message: Message) => (
            <ChatMessage key={message.id} role={message.role} content={message.content} />
          ))}
          {isLoading && (
            <div className="text-center text-xs text-slate-500">回答生成中…</div>
          )}
          <div ref={bottomRef} />
        </div>
      </section>

      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
        <label className="text-sm font-medium text-slate-600" htmlFor="chat-input">
          質問を入力
        </label>
        <textarea
          id="chat-input"
          className="min-h-[120px] resize-y rounded-2xl border border-slate-200 bg-white p-4 text-sm shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          placeholder="例: 水タイプで序盤に強いカードを教えて"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
        />
        <div className="flex items-center justify-end gap-3">
          {isLoading && <span className="text-xs text-slate-500">回答生成中…</span>}
          <button
            type="submit"
            className="rounded-full bg-sky-600 px-6 py-2 text-sm font-semibold text-white shadow transition hover:bg-sky-500 disabled:cursor-not-allowed disabled:bg-slate-400"
            disabled={!input.trim() || isLoading}
          >
            送信
          </button>
        </div>
      </form>
    </main>
  );
}
