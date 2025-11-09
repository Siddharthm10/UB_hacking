import React, { useEffect, useState } from 'react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5000';

const ManagerDashboardView = () => {
    const [summaryData, setSummaryData] = useState([]);

    useEffect(() => {
        axios.get(`${API_BASE}/dashboard/summary`)
            .then(response => setSummaryData(response.data.summary))
            .catch(() => setSummaryData([]));
    }, [API_BASE]);

    const downloadPdf = () => {
        window.open(`${API_BASE}/dashboard/pdf`);
    };

    return (
        <div className="call-summary-view">
            <div className="panel">
                <h1>Manager Dashboard</h1>
                <button onClick={downloadPdf}>Download Agent Report</button>
                <table>
                    <thead>
                        <tr>
                            <th>Agent Name</th>
                            <th>Total Calls</th>
                            <th>Total Violations</th>
                        </tr>
                    </thead>
                    <tbody>
                        {summaryData.map((agent, index) => (
                            <tr key={index}>
                                <td>{agent.agent_name}</td>
                                <td>{agent.total_calls}</td>
                                <td>{agent.total_violations}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default ManagerDashboardView;
