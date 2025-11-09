import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5000';

const CallSummaryView = () => {
    const { call_id } = useParams();
    const [callData, setCallData] = useState(null);
    const [error, setError] = useState('');

    useEffect(() => {
        axios.get(`${API_BASE}/call/${call_id}`)
            .then((response) => setCallData(response.data))
            .catch(() => setError('Could not load call data.'));
    }, [call_id]);

    const downloadPdf = () => {
        window.open(`${API_BASE}/call/${call_id}/pdf`, '_blank');
    };

    if (error) {
        return <div>{error}</div>;
    }

    if (!callData) {
        return <div>Loading...</div>;
    }

    const agent = callData.agent || {};
    const customer = callData.customer || {};

    return (
        <div className="call-summary-view">
            <div className="panel">
                <h1>Call Summary</h1>
                <div className="call-meta">
                    <div>
                        <h4>Agent</h4>
                        <p>{agent.name || 'Unknown'}</p>
                        <small>{agent.email}</small>
                    </div>
                    <div>
                        <h4>Customer</h4>
                        <p>{customer.name || 'Unknown'}</p>
                        <small>{customer.account_number}</small>
                    </div>
                    <div>
                        <h4>Compliance Score</h4>
                        <p className="score">{callData.compliance_score}</p>
                    </div>
                    <button onClick={downloadPdf}>Download PDF</button>
                </div>
            </div>

            <section className="panel">
                <h2>Key Topics</h2>
                <ul className="chips">
                    {(callData.key_topics || []).map((topic) => (
                        <li key={topic}>{topic}</li>
                    ))}
                </ul>
            </section>

            <section className="panel">
                <h2>Summary</h2>
                <p>{callData.summary}</p>
            </section>

            <section className="panel">
                <h2>Violations & Alerts</h2>
                {(callData.violations || []).length === 0 ? (
                    <p>No violations detected.</p>
                ) : (
                    <ul>
                        {callData.violations.map((violation, index) => (
                            <li key={`${violation.rule}-${index}`}>
                                <strong>{violation.rule}</strong> ({violation.level}) — {violation.text || violation.excerpt}
                            </li>
                        ))}
                    </ul>
                )}
            </section>

            <section className="panel">
                <h2>Transcript</h2>
                <div className="scroller">
                    {(callData.full_transcript || []).map((item, index) => (
                        <div key={`${item.speaker}-${index}`} className={`transcript-line ${item.speaker}`}>
                            <span>{item.speaker.toUpperCase()}</span>
                            <p>{item.text}</p>
                        </div>
                    ))}
                </div>
            </section>
        </div>
    );
};

export default CallSummaryView;
