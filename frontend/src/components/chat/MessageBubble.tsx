import { Fragment, type ReactNode } from "react";
import { motion } from "motion/react";
import { Sparkles, Link2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Source, Suggestion } from "@/lib/types";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  suggestion?: Suggestion;
  onSuggestionClick?: (s: Suggestion) => void;
  onNodeClick?: (label: string) => void;
}

function splitNodeClicks(text: string, onNodeClick?: (label: string) => void): ReactNode {
  if (!onNodeClick) return text;
  const tokens = text.split(/(\b[A-Z][a-zA-Z]{2,}\b)/g);
  return tokens.map((t, i) => {
    if (/^[A-Z][a-zA-Z]{2,}$/.test(t)) {
      return (
        <button
          key={i}
          onClick={() => onNodeClick(t)}
          className="rounded px-1 text-primary transition-colors hover:bg-primary/15"
        >
          {t}
        </button>
      );
    }
    return <Fragment key={i}>{t}</Fragment>;
  });
}

function processChildren(children: ReactNode, onNodeClick?: (label: string) => void): ReactNode {
  if (children == null || typeof children === "boolean") return children;
  if (typeof children === "string" || typeof children === "number") {
    return splitNodeClicks(String(children), onNodeClick);
  }
  if (Array.isArray(children)) {
    return children.map((child, i) => (
      <Fragment key={i}>{processChildren(child, onNodeClick)}</Fragment>
    ));
  }
  return children;
}

function makeMarkdownComponents(onNodeClick?: (label: string) => void) {
  return {
    p: ({ children, ...props }: any) => (
      <p className="my-1.5 text-sm leading-relaxed" {...props}>
        {processChildren(children, onNodeClick)}
      </p>
    ),
    h1: ({ children, ...props }: any) => (
      <h1 className="mt-3 text-lg font-semibold tracking-tight" {...props}>
        {processChildren(children, onNodeClick)}
      </h1>
    ),
    h2: ({ children, ...props }: any) => (
      <h2 className="mt-3 text-base font-semibold tracking-tight" {...props}>
        {processChildren(children, onNodeClick)}
      </h2>
    ),
    h3: ({ children, ...props }: any) => (
      <h3 className="mt-3 text-sm font-semibold tracking-tight" {...props}>
        {processChildren(children, onNodeClick)}
      </h3>
    ),
    h4: ({ children, ...props }: any) => (
      <h4 className="mt-2 text-sm font-semibold tracking-tight" {...props}>
        {processChildren(children, onNodeClick)}
      </h4>
    ),
    ul: ({ children, ...props }: any) => (
      <ul className="my-2 ml-4 list-disc space-y-1 text-sm leading-relaxed" {...props}>
        {children}
      </ul>
    ),
    ol: ({ children, ...props }: any) => (
      <ol className="my-2 ml-4 list-decimal space-y-1 text-sm leading-relaxed" {...props}>
        {children}
      </ol>
    ),
    li: ({ children, ...props }: any) => (
      <li {...props}>{processChildren(children, onNodeClick)}</li>
    ),
    code: ({ className, children, ...props }: any) => {
      const isBlock = /language-/.test(className || "");
      if (!isBlock) {
        return (
          <code
            className="rounded bg-background/60 px-1 py-0.5 font-mono text-xs"
            {...props}
          >
            {children}
          </code>
        );
      }
      return (
        <code className={className} {...props}>
          {children}
        </code>
      );
    },
    pre: ({ children, ...props }: any) => (
      <pre
        className="my-2 overflow-x-auto rounded-lg border border-border/50 bg-background/60 p-3 text-xs"
        {...props}
      >
        {children}
      </pre>
    ),
    blockquote: ({ children, ...props }: any) => (
      <blockquote
        className="my-2 border-l-2 border-border/60 pl-3 text-sm italic text-muted-foreground"
        {...props}
      >
        {children}
      </blockquote>
    ),
    a: ({ children, ...props }: any) => (
      <a
        className="text-primary underline decoration-primary/40 underline-offset-2 hover:decoration-primary"
        target="_blank"
        rel="noopener noreferrer"
        {...props}
      >
        {children}
      </a>
    ),
    hr: (props: any) => <hr className="my-3 border-border/40" {...props} />,
    table: ({ children, ...props }: any) => (
      <div className="my-2 overflow-x-auto">
        <table className="w-full text-sm" {...props}>
          {children}
        </table>
      </div>
    ),
    th: ({ children, ...props }: any) => (
      <th
        className="border-b border-border/40 px-2 py-1 text-left font-semibold"
        {...props}
      >
        {children}
      </th>
    ),
    td: ({ children, ...props }: any) => (
      <td className="border-b border-border/20 px-2 py-1" {...props}>
        {children}
      </td>
    ),
    del: ({ children, ...props }: any) => (
      <del className="text-muted-foreground line-through" {...props}>
        {children}
      </del>
    ),
    input: ({ type, checked, disabled, ...props }: any) => {
      if (type === "checkbox") {
        return (
          <input
            type="checkbox"
            checked={checked}
            disabled
            className="mr-1.5 align-middle accent-primary"
            {...props}
          />
        );
      }
      return <input type={type} {...props} />;
    },
  };
}

export function MessageBubble({
  role,
  content,
  sources,
  suggestion,
  onSuggestionClick,
  onNodeClick,
}: MessageBubbleProps) {
  const isUser = role === "user";
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}
    >
      <div
        className={`max-w-[78%] rounded-2xl px-4 py-2.5 text-sm ${
          isUser
            ? "bg-primary/15 text-foreground border border-primary/20"
            : "border border-border/60 bg-surface/70 text-foreground backdrop-blur"
        }`}
      >
        {isUser ? (
          <div className="whitespace-pre-wrap">{content}</div>
        ) : (
          <div className="markdown-body">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={makeMarkdownComponents(onNodeClick)}
            >
              {content}
            </ReactMarkdown>
          </div>
        )}

        {!isUser && sources && sources.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-border/40 pt-2.5">
            <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Sources
            </span>
            {sources.map((s, idx) => (
              <a
                key={idx}
                href={s.url || "#"}
                target="_blank"
                rel="noopener noreferrer"
                className={`inline-flex max-w-[220px] items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] transition-colors ${
                  s.type === "youtube"
                    ? "border-red-500/30 bg-red-500/10 text-red-300 hover:border-red-500/60"
                    : "border-border bg-surface/60 text-muted-foreground hover:border-accent-teal/40"
                }`}
                title={s.title}
              >
                {s.type === "youtube" ? (
                  <span className="text-[9px]">▶</span>
                ) : (
                  <Link2 className="size-2.5" />
                )}
                <span className="truncate">{s.title}</span>
              </a>
            ))}
          </div>
        )}

        {!isUser && suggestion && (
          <button
            onClick={() => onSuggestionClick?.(suggestion)}
            className="mt-3 flex w-full items-start gap-2 rounded-lg border border-primary/30 bg-primary/5 px-3 py-2 text-left text-xs text-muted-foreground transition-colors hover:border-primary/60 hover:text-foreground"
          >
            <Sparkles className="mt-0.5 size-3 shrink-0 text-primary" />
            <span>{suggestion.text}</span>
          </button>
        )}
      </div>
    </motion.div>
  );
}
