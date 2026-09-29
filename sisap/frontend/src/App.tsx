import { Route, Routes } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import DashboardPage from "./pages/DashboardPage";
import AnalyzePage from "./pages/AnalyzePage";
import RecommendationsPage from "./pages/RecommendationsPage";
import StandardsExplorerPage from "./pages/StandardsExplorerPage";
import StandardDetailPage from "./pages/StandardDetailPage";
import HistoryPage from "./pages/HistoryPage";
import ReportsPage from "./pages/ReportsPage";
import NotFoundPage from "./pages/NotFoundPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="analyze" element={<AnalyzePage />} />
        <Route path="analyze/:documentId/recommendations" element={<RecommendationsPage />} />
        <Route path="standards" element={<StandardsExplorerPage />} />
        <Route path="standards/:standardId" element={<StandardDetailPage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
