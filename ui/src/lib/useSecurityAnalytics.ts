import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { getAssets, getFindingFacets, getFindings } from "@/lib/api";
import { useAnalystWorkflow } from "@/lib/analystWorkflow";
import { plainError } from "@/lib/errors";
import { buildSecurityAnalytics, type AnalyticsModel } from "@/lib/securityAnalytics";

export function useSecurityAnalytics() {
  const { workflow } = useAnalystWorkflow();
  const assets = useQuery({ queryKey: ["assets", "summary"], queryFn: () => getAssets({ limit: 1, offset: 0 }) });
  const findings = useQuery({
    queryKey: ["findings", "analytics-feed"],
    queryFn: () => getFindings({ limit: 200, offset: 0, sort: "severity", order: "asc" }),
  });
  const facets = useQuery({
    queryKey: ["finding-facets", "dashboard"],
    queryFn: () => getFindingFacets(),
  });
  const cspm = useQuery({
    queryKey: ["findings-count-cspm"],
    queryFn: () => getFindings({ source: "cspm", limit: 1, offset: 0 }),
  });
  const combo = useQuery({
    queryKey: ["findings-count-combo"],
    queryFn: () => getFindings({ source: "toxic-combo", limit: 1, offset: 0 }),
  });

  const pending = assets.isPending || findings.isPending || facets.isPending || cspm.isPending || combo.isPending;
  const unavailable = findings.isError && facets.isError;

  const model: AnalyticsModel | null = useMemo(() => {
    if (pending) return null;
    if (unavailable) {
      return buildSecurityAnalytics({
        dataState: "unavailable",
        findings: [],
        findingsTotal: 0,
        facets: null,
        cspmTotal: null,
        comboTotal: null,
        assetTotal: null,
        workflow,
      });
    }
    const total = facets.data?.total ?? findings.data?.total ?? 0;
    return buildSecurityAnalytics({
      dataState: total === 0 ? "empty" : "ready",
      findings: findings.data?.items ?? [],
      findingsTotal: findings.data?.total ?? total,
      facets: facets.data ?? null,
      cspmTotal: cspm.data?.total ?? null,
      comboTotal: combo.data?.total ?? null,
      assetTotal: assets.data?.total ?? null,
      workflow,
    });
  }, [
    pending,
    unavailable,
    findings.data,
    facets.data,
    cspm.data,
    combo.data,
    assets.data,
    workflow,
  ]);

  const errorMessage = unavailable
    ? plainError(findings.error ?? facets.error, "The demo API isn't responding.")
    : findings.isError
      ? plainError(findings.error, "Couldn't load findings for the risk list.")
      : facets.isError
        ? plainError(facets.error, "Couldn't load finding totals.")
        : null;

  return {
    model,
    pending,
    unavailable,
    errorMessage,
    assets,
    findings,
    facets,
    cspm,
    combo,
  };
}
