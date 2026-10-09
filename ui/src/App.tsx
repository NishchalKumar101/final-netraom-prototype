import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/AppShell";
import { NotificationToasts } from "@/components/soc/NotificationCenter";
import { AssetDetailPage } from "@/pages/AssetDetailPage";
import { AssetsPage } from "@/pages/AssetsPage";
import { AssistantPage } from "@/pages/AssistantPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { FindingsPage } from "@/pages/FindingsPage";
import { AttackPathPage } from "@/pages/learn/AttackPathPage";
import { CookbookPage } from "@/pages/learn/CookbookPage";
import { GraphLabPage } from "@/pages/learn/GraphLabPage";
import { OverviewPage } from "@/pages/learn/OverviewPage";
import { InventoryPipelinePage } from "@/pages/learn/InventoryPipelinePage";
import { PostgresLabPage } from "@/pages/learn/PostgresLabPage";
import { ThemeProvider } from "@/theme/ThemeProvider";

const qc = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, retryDelay: 400 },
  },
});

export function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={qc}>
        <BrowserRouter>
          <NotificationToasts />
          <Routes>
            <Route element={<AppShell />}>
              <Route index element={<DashboardPage />} />
              <Route path="assets" element={<AssetsPage />} />
              <Route path="assets/:assetId" element={<AssetDetailPage />} />
              <Route path="findings" element={<FindingsPage />} />
              <Route path="assistant" element={<AssistantPage />} />
              <Route path="learn" element={<OverviewPage />} />
              <Route path="learn/inventory" element={<InventoryPipelinePage />} />
              <Route path="learn/postgres" element={<PostgresLabPage />} />
              <Route path="learn/graph" element={<GraphLabPage />} />
              <Route path="learn/cookbook" element={<CookbookPage />} />
              <Route path="learn/attack-path" element={<AttackPathPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
