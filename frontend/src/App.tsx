import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { Dashboard } from './pages/Dashboard';
import { TendersPage } from './pages/TendersPage';
import { VendorBidsPage } from './pages/VendorBidsPage';
import { EvaluationWorkspace } from './pages/EvaluationWorkspace';
import { ScorecardPage } from './pages/ScorecardPage';
import { ReportsPage } from './pages/ReportsPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
        <Navbar />
        <div className="flex flex-1">
          <Sidebar />
          <main className="flex-1 p-8 max-w-7xl mx-auto w-full">
            <ErrorBoundary>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/tenders" element={<TendersPage />} />
                <Route path="/vendors" element={<VendorBidsPage />} />
                <Route path="/evaluations" element={<EvaluationWorkspace />} />
                <Route path="/scorecard" element={<ScorecardPage />} />
                <Route path="/reports" element={<ReportsPage />} />
              </Routes>
            </ErrorBoundary>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
};

export default App;

