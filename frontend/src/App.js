import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import LiveCopilotView from './views/LiveCopilotView';
import CallSummaryView from './views/CallSummaryView';
import ManagerDashboardView from './views/ManagerDashboardView';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<LiveCopilotView />} />
          <Route path="/call/:call_id" element={<CallSummaryView />} />
          <Route path="/dashboard" element={<ManagerDashboardView />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
