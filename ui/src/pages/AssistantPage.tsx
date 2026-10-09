import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/Button";
import { Panel } from "@/components/Panel";
import { FAQ, matchFaq, SUGGESTED_QUESTIONS } from "@/lib/faq";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  suggestions?: string[];
};

const GREETING: ChatMessage = {
  id: "greeting",
  role: "assistant",
  text: "Rule-based assistant for this prototype. I match your question against a fixed FAQ. I am not an LLM and I do not call an AI API.",
  suggestions: SUGGESTED_QUESTIONS,
};

export function AssistantPage() {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([GREETING]);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  const ask = (raw: string) => {
    const text = raw.trim();
    if (!text) return;
    const match = matchFaq(text);
    const reply: ChatMessage = match.entry
      ? {
          id: `a-${messages.length}`,
          role: "assistant",
          text: match.entry.answer,
        }
      : {
          id: `a-${messages.length}`,
          role: "assistant",
          text: "I don't have a confident match for that. Try one of the related questions, or rephrase with words like findings, risk score, Postgres, or attack path.",
          suggestions: (match.suggestions.length ? match.suggestions : FAQ.slice(0, 3)).map((entry) => entry.question),
        };
    setMessages((current) => [
      ...current,
      { id: `u-${current.length}`, role: "user", text },
      reply,
    ]);
    setDraft("");
  };

  return (
    <div className="space-y-4">
      <p className="max-w-3xl text-sm leading-relaxed text-[var(--muted)]">
        Security Assistant answers from a local FAQ about this demo: synthetic fixtures, Postgres and Neo4j, CSPM and toxic combinations, risk scoring, Learn labs, and the limits of the simulated map. It does not reach an external model.
      </p>
      <Panel title="Chat" eyebrow="Rule-based FAQ" bodyClassName="flex h-[min(70vh,640px)] flex-col gap-3">
        <div className="min-h-0 flex-1 space-y-3 overflow-auto pr-1" role="log" aria-live="polite" aria-relevant="additions">
          {messages.map((message) => (
            <div key={message.id} className={message.role === "user" ? "flex justify-end" : "flex justify-start"}>
              <div
                className={
                  message.role === "user"
                    ? "max-w-[85%] rounded-2xl bg-[var(--accent)] px-3 py-2 text-sm text-[var(--on-accent)]"
                    : "max-w-[85%] rounded-2xl border border-[var(--border)] bg-[var(--inset)] px-3 py-2 text-sm text-[var(--foreground)]"
                }
              >
                <p>{message.text}</p>
                {message.suggestions?.length ? (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {message.suggestions.map((question) => (
                      <button
                        key={question}
                        type="button"
                        className="rounded-full border border-[var(--border)] bg-[var(--card)] px-2.5 py-1 text-left text-xs text-[var(--foreground)] hover:bg-[var(--hover)]"
                        onClick={() => ask(question)}
                      >
                        {question}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
          ))}
          <div ref={endRef} />
        </div>
        <form
          className="flex flex-col gap-2 sm:flex-row"
          onSubmit={(event) => {
            event.preventDefault();
            ask(draft);
          }}
        >
          <input
            ref={inputRef}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                ask(draft);
              }
            }}
            aria-label="Ask the rule-based assistant"
            placeholder="Ask about findings, risk score, or the labs"
            className="min-w-0 flex-1 rounded-lg border border-[var(--border)] bg-[var(--inset)] px-3 py-2 text-sm text-[var(--foreground)] outline-none placeholder:text-[var(--muted)] focus:border-[var(--accent)]"
          />
          <div className="flex gap-2">
            <Button type="submit">Send</Button>
            <Button
              variant="secondary"
              onClick={() => {
                setMessages([GREETING]);
                setDraft("");
                inputRef.current?.focus();
              }}
            >
              Clear chat
            </Button>
          </div>
        </form>
      </Panel>
    </div>
  );
}
