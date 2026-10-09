import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";

type DocWithTable = jsPDF & { lastAutoTable?: { finalY?: number } };

import pkg from "../../package.json";
import { categoryLabel, type AnalyticsModel } from "@/lib/securityAnalytics";

function fmt(value: number | null) {
  return value == null ? "Unavailable" : String(value);
}

function stamp(iso: string) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toISOString().replace("T", " ").slice(0, 16) + " UTC";
}

export function buildSecurityPdf(model: AnalyticsModel) {
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const pageWidth = doc.internal.pageSize.getWidth();
  const margin = 40;
  let y = 48;

  const ensure = (needed: number) => {
    if (y + needed > doc.internal.pageSize.getHeight() - 48) {
      doc.addPage();
      y = 48;
    }
  };

  const heading = (label: string, title: string) => {
    ensure(48);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9);
    doc.setTextColor(80, 98, 122);
    doc.text(label, margin, y);
    y += 16;
    doc.setFontSize(14);
    doc.setTextColor(18, 32, 51);
    doc.text(title, margin, y);
    y += 18;
  };

  const paragraph = (text: string) => {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(30, 41, 59);
    const lines = doc.splitTextToSize(text, pageWidth - margin * 2) as string[];
    ensure(lines.length * 13 + 8);
    doc.text(lines, margin, y);
    y += lines.length * 13 + 8;
  };

  doc.setFillColor(11, 20, 36);
  doc.rect(0, 0, pageWidth, 36, "F");
  doc.setTextColor(231, 238, 248);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.text("netraOM  ·  CSPM Trust Graph", margin, 23);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.text(`v${pkg.version}`, pageWidth - margin, 23, { align: "right" });

  y = 64;
  heading("A. Scope", "Security posture snapshot");
  paragraph(
    `Generated ${stamp(model.generatedAtIso)} from the dashboard analytics model (version ${pkg.version}). Data state: ${model.dataState}. This is a prototype report over synthetic fixtures in Postgres and Neo4j. It is not live production telemetry and it does not attest to deployed security controls.`,
  );
  if (model.sampleNote) paragraph(model.sampleNote);

  heading("B. KPI summary", "Counts used on the dashboard");
  autoTable(doc, {
    startY: y,
    margin: { left: margin, right: margin, bottom: 48 },
    head: [["Metric", "Value", "Notes"]],
    body: [
      ["Total findings", fmt(model.kpis.totalFindings), "Facet total when the API responds"],
      ["Critical + high", fmt(model.kpis.criticalHigh), "Sum of critical and high facet counts"],
      ["Attack paths / toxic combinations", fmt(model.kpis.attackPaths), "toxic-combo finding count"],
      ["Vulnerabilities (CSPM)", fmt(model.kpis.vulnerabilities), "cspm finding count"],
      ["Assets", fmt(model.kpis.assets), "Inventory total"],
      ["Mitigated (analyst workflow)", String(model.kpis.mitigated), model.kpis.mitigatedNote],
      ["Resolved (analyst workflow)", String(model.kpis.resolved), "Same browser-local workflow. Not server-verified."],
    ],
    styles: { fontSize: 9, textColor: [30, 41, 59], cellPadding: 5 },
    headStyles: { fillColor: [22, 42, 74], textColor: 255 },
    columnStyles: { 2: { cellWidth: 230 } },
  });
  y = ((doc as DocWithTable).lastAutoTable?.finalY ?? y) + 20;

  heading("C. Severity distribution", "Findings by severity");
  autoTable(doc, {
    startY: y,
    margin: { left: margin, right: margin, bottom: 48 },
    head: [["Severity", "Count"]],
    body: model.severityBars.map((row) => [row.label, String(row.count)]),
    styles: { fontSize: 9, textColor: [30, 41, 59], cellPadding: 5 },
    headStyles: { fillColor: [22, 42, 74], textColor: 255 },
  });
  y = ((doc as DocWithTable).lastAutoTable?.finalY ?? y) + 20;

  heading("D. Category distribution", "CSPM misconfigurations and toxic combinations");
  autoTable(doc, {
    startY: y,
    margin: { left: margin, right: margin, bottom: 48 },
    head: [["Category", "Count"]],
    body: model.categoryDonut.map((row) => [row.label, String(row.count)]),
    styles: { fontSize: 9, textColor: [30, 41, 59], cellPadding: 5 },
    headStyles: { fillColor: [22, 42, 74], textColor: 255 },
  });
  y = ((doc as DocWithTable).lastAutoTable?.finalY ?? y) + 20;

  heading("E. Seven-day trend", "Insufficient history — simulated series");
  paragraph(model.history.note);
  autoTable(doc, {
    startY: y,
    margin: { left: margin, right: margin, bottom: 48 },
    head: [["UTC date", "Findings (simulated)", "Critical + high (simulated)"]],
    body: model.trend.map((row) => [row.date, String(row.findings), String(row.criticalHigh)]),
    styles: { fontSize: 9, textColor: [30, 41, 59], cellPadding: 5 },
    headStyles: { fillColor: [22, 42, 74], textColor: 255 },
  });
  y = ((doc as DocWithTable).lastAutoTable?.finalY ?? y) + 20;

  heading("F. Risk register", "Analyst workflow, not server status");
  paragraph(
    "Status values are New, Investigating, Mitigated, or Resolved as set in this browser. The demo API does not persist them. Impact and mitigation text is derived from the finding record or a short local hint. No external ticketing or control plane is integrated.",
  );
  autoTable(doc, {
    startY: y,
    margin: { left: margin, right: margin, bottom: 48 },
    head: [["Title", "Severity", "Entity", "Time (simulated)", "Status", "Category"]],
    body:
      model.risks.length > 0
        ? model.risks.map((risk) => [
            risk.title,
            risk.severity,
            risk.entity,
            stamp(risk.time),
            `${risk.status} (browser)`,
            categoryLabel(risk.category),
          ])
        : [["No risks in this snapshot", "—", "—", "—", "—", "—"]],
    styles: { fontSize: 8, textColor: [30, 41, 59], cellPadding: 4, overflow: "linebreak" },
    headStyles: { fillColor: [22, 42, 74], textColor: 255 },
    columnStyles: { 0: { cellWidth: 140 }, 2: { cellWidth: 90 } },
  });
  y = ((doc as DocWithTable).lastAutoTable?.finalY ?? y) + 12;
  if (model.risks.length) {
    ensure(20);
    doc.setFontSize(10);
    doc.setTextColor(30, 41, 59);
    doc.text("Impact and mitigation", margin, y);
    y += 14;
    for (const risk of model.risks.slice(0, 12)) {
      paragraph(`${risk.title}: ${risk.impact} Mitigation: ${risk.mitigation}`);
    }
  }

  heading("G. Simulated map events and limits", model.mapUsesFallback ? "Fallback dataset" : "Derived from loaded findings");
  paragraph(
    model.mapUsesFallback
      ? "No loaded findings were available for the map, so these rows are the shared simulated fallback. They are not detections."
      : "Each row is simulated telemetry: title, severity, and asset come from a loaded finding. Region, path, and timestamp are deterministic placements, not observed traffic.",
  );
  autoTable(doc, {
    startY: y,
    margin: { left: margin, right: margin, bottom: 48 },
    head: [["Title", "Severity", "Category", "Source", "Destination", "Asset", "Timestamp"]],
    body: model.mapEvents.map((event) => [
      event.title,
      event.severity,
      categoryLabel(event.category),
      event.sourceSite.name,
      event.destSite.name,
      event.asset,
      stamp(event.timestamp),
    ]),
    styles: { fontSize: 8, textColor: [30, 41, 59], cellPadding: 4, overflow: "linebreak" },
    headStyles: { fillColor: [22, 42, 74], textColor: 255 },
  });
  y = ((doc as DocWithTable).lastAutoTable?.finalY ?? y) + 16;
  paragraph(
    "Limits: synthetic fixtures only; no cloud-provider integration is invoked by this export; BFS is implemented in the engine but is not what finding scoring calls; DFS is not implemented; analyst status is local; trend dates are a simulated distribution of current counts.",
  );

  const pages = doc.getNumberOfPages();
  for (let page = 1; page <= pages; page += 1) {
    doc.setPage(page);
    const height = doc.internal.pageSize.getHeight();
    doc.setDrawColor(212, 223, 236);
    doc.line(margin, height - 32, pageWidth - margin, height - 32);
    doc.setFontSize(8);
    doc.setTextColor(82, 101, 127);
    doc.text("netraOM CSPM Trust Graph · prototype report · not production telemetry", margin, height - 18);
    doc.text(`Page ${page} of ${pages}`, pageWidth - margin, height - 18, { align: "right" });
  }

  return doc;
}
