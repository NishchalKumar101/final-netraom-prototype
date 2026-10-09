import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/Button";
import { buildSecurityPdf } from "@/lib/securityPdf";
import type { AnalyticsModel } from "@/lib/securityAnalytics";

export function PdfPreviewDialog({
  open,
  model,
  onClose,
}: {
  open: boolean;
  model: AnalyticsModel | null;
  onClose: () => void;
}) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const frameRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (!open || !model) return;
    let revoked = false;
    let objectUrl: string | null = null;
    setLoading(true);
    setError(null);
    setUrl(null);
    const handle = window.setTimeout(() => {
      try {
        const blob = buildSecurityPdf(model).output("blob");
        objectUrl = URL.createObjectURL(blob);
        if (revoked) {
          URL.revokeObjectURL(objectUrl);
          return;
        }
        setUrl(objectUrl);
      } catch (err) {
        if (!revoked) setError(err instanceof Error ? err.message : "Couldn't build the PDF.");
      } finally {
        if (!revoked) setLoading(false);
      }
    }, 40);
    return () => {
      revoked = true;
      window.clearTimeout(handle);
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [open, model]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open || !model) return null;

  const download = () => {
    if (!url) return;
    const link = document.createElement("a");
    link.href = url;
    link.download = `netraom-security-${model.generatedAtIso.slice(0, 10)}.pdf`;
    link.click();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--overlay)] p-3" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="pdf-preview-title"
        className="flex h-[min(92vh,860px)] w-full max-w-4xl flex-col rounded-xl border border-[var(--border)] bg-[var(--card)] shadow-[var(--shadow)]"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] px-4 py-3">
          <div>
            <h2 id="pdf-preview-title" className="text-sm font-semibold">
              Security report preview
            </h2>
            <p className="text-xs text-[var(--muted)]">Client-side PDF. Same numbers as the dashboard model.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" disabled={!url} onClick={download}>
              Download
            </Button>
            <Button variant="secondary" disabled={!url} onClick={() => frameRef.current?.contentWindow?.print()}>
              Print
            </Button>
            <Button variant="ghost" onClick={onClose}>
              Close
            </Button>
          </div>
        </header>
        <div className="min-h-0 flex-1 bg-[var(--inset)]">
          {loading ? <p className="p-4 text-sm text-[var(--muted)]">Building the report…</p> : null}
          {error ? <p className="p-4 text-sm text-[var(--danger-fg)]">{error}</p> : null}
          {url ? <iframe ref={frameRef} title="Security report preview" src={url} className="h-full w-full" /> : null}
        </div>
      </div>
    </div>
  );
}
