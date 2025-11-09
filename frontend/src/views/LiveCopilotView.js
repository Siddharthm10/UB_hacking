import React, { useEffect, useRef, useState } from 'react';
import io from 'socket.io-client';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://127.0.0.1:5000';

const LiveCopilotView = () => {
    const [agents, setAgents] = useState([]);
    const [customers, setCustomers] = useState([]);
    const [selectedAgent, setSelectedAgent] = useState('');
    const [selectedCustomer, setSelectedCustomer] = useState('');
    const [currentSpeaker, setCurrentSpeaker] = useState('agent');
    const [sessionId, setSessionId] = useState('');
    const [transcript, setTranscript] = useState([]);
    const [warnings, setWarnings] = useState([]);
    const [draftText, setDraftText] = useState('');
    const [statusMessage, setStatusMessage] = useState('');
    const [isStreaming, setIsStreaming] = useState(false);
    const [isCallActive, setIsCallActive] = useState(false);
    const [callResult, setCallResult] = useState(null);
    const [callRecordId, setCallRecordId] = useState('');
    const socketRef = useRef(null);
    const mediaRecorderRef = useRef(null);
    const mediaStreamRef = useRef(null);
    const sessionIdRef = useRef('');

    const blobToBase64 = (blob) => {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onloadend = () => {
                const result = reader.result;
                resolve(typeof result === 'string' ? result.split(',')[1] : '');
            };
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    };

    const stopStreaming = () => {
        const recorder = mediaRecorderRef.current;
        if (recorder && recorder.state !== 'inactive') {
            try {
                recorder.stop();
            } catch (err) {
                // ignore
            }
        }
        const stream = mediaStreamRef.current;
        if (stream) {
            stream.getTracks().forEach((track) => track.stop());
        }
        mediaRecorderRef.current = null;
        mediaStreamRef.current = null;
        setIsStreaming(false);
    };

    const startStreaming = async (activeSessionId = sessionId) => {
        if (!socketRef.current || isStreaming || !activeSessionId) return;
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
            mediaRecorderRef.current = recorder;
            mediaStreamRef.current = stream;
            recorder.ondataavailable = async (event) => {
                if (event.data.size <= 0 || !socketRef.current) return;
                const base64Chunk = await blobToBase64(event.data);
                socketRef.current.emit('stream_audio', {
                    session_id: activeSessionId,
                    speaker: currentSpeaker,
                    audio_base64: base64Chunk,
                    mime_type: recorder.mimeType,
                });
            };
            recorder.start(1500);
            setIsStreaming(true);
        } catch (error) {
            console.error('Unable to access microphone', error);
            setStatusMessage('Microphone access denied.');
        }
    };

    const startCall = async () => {
        if (!selectedAgent || !selectedCustomer) {
            setStatusMessage('Select an agent and a customer to begin.');
            return;
        }
        try {
            const response = await axios.post(`${API_BASE}/sessions/start`, {
                agent_id: selectedAgent,
                customer_id: selectedCustomer,
            });
            const newSessionId = response.data.session_id;
            sessionIdRef.current = newSessionId;
            setSessionId(newSessionId);
            setTranscript([]);
            setWarnings([]);
            setCallResult(null);
            setCallRecordId('');
            setStatusMessage('Call in progress. Streaming microphone audio...');
            setIsCallActive(true);
            await startStreaming(newSessionId);
        } catch (error) {
            setStatusMessage('Unable to start session. Check backend logs.');
        }
    };

    const endCall = async () => {
        stopStreaming();
        if (!sessionIdRef.current) return;
        try {
            const response = await axios.post(`${API_BASE}/call/end`, { session_id: sessionIdRef.current });
            setCallRecordId(response.data.call_id);
            setCallResult(response.data.analysis);
            setStatusMessage('Call completed and saved.');
        } catch (error) {
            setStatusMessage('Failed to finalize call.');
        } finally {
            setIsCallActive(false);
        }
    };

    const sendManualStatement = () => {
        const trimmed = draftText.trim();
        if (!trimmed || !socketRef.current || !sessionIdRef.current) return;
        socketRef.current.emit('stream_audio', {
            speaker: currentSpeaker,
            text: trimmed,
            session_id: sessionIdRef.current,
        });
        setDraftText('');
    };

    useEffect(() => {
        axios.get(`${API_BASE}/directory`).then((response) => {
            setAgents(response.data.agents);
            setCustomers(response.data.customers);
            console.log("Loaded agents and customers data!")
        }).catch((e) => {
            console.log(e)
            setStatusMessage('Unable to load directory. Check backend.');
        });
    }, []);

    useEffect(() => {
        const socket = io(API_BASE, { transports: ['websocket'] });
        socketRef.current = socket;

        socket.on('update_transcript', (data) => {
            setTranscript((prev) => [...prev, data]);
        });

        socket.on('new_warning', (data) => {
            const payload = Array.isArray(data) ? data : [data];
            setWarnings((prev) => [...prev, ...payload]);
        });

        socket.on('session_status', (payload) => {
            if (!payload || payload.session_id !== sessionIdRef.current) {
                return;
            }
            if (payload.status === 'abandoned') {
                setStatusMessage('Session timed out due to inactivity.');
                stopStreaming();
                setIsCallActive(false);
            }
            if (payload.status === 'completed') {
                setStatusMessage('Call completed and saved by server.');
                stopStreaming();
                setIsCallActive(false);
                if (payload.call_id) {
                    setCallRecordId(payload.call_id);
                }
            }
        });

        return () => {
            socket.disconnect();
        };
    }, []);

    useEffect(() => {
        sessionIdRef.current = sessionId;
        if (sessionId && socketRef.current) {
            socketRef.current.emit('register_session', { session_id: sessionId });
        }
    }, [sessionId]);

    return (
        <div className="live-copilot-view">
            <header className="copilot-header">
                <div>
                    <h1>EthiCo Live Copilot</h1>
                    <p>Monitor FDCPA compliance in real-time with Gemini and ElevenLabs.</p>
                </div>
                <div className="session-meta">
                    <span className={isCallActive ? 'status-dot active' : 'status-dot'} />
                    <strong>{isCallActive ? 'Live Call' : 'Idle'}</strong>
                    <small>{sessionId || 'No session yet'}</small>
                </div>
            </header>

            <section className="panel layout">
                <div>
                    <label>Agent</label>
                    <select value={selectedAgent} onChange={(e) => setSelectedAgent(e.target.value)}>
                        <option value="">Select agent</option>
                        {agents.map((agent) => (
                            <option key={agent.id} value={agent.id}>
                                {agent.name} · {agent.team}
                            </option>
                        ))}
                    </select>
                </div>
                <div>
                    <label>Customer</label>
                    <select value={selectedCustomer} onChange={(e) => setSelectedCustomer(e.target.value)}>
                        <option value="">Select customer</option>
                        {customers.map((customer) => (
                            <option key={customer.id} value={customer.id}>
                                {customer.name} · {customer.account_number}
                            </option>
                        ))}
                    </select>
                </div>
                <div className="speaker-toggle">
                    <span>Speaker</span>
                    <div className="segmented">
                        <button
                            className={currentSpeaker === 'agent' ? 'active' : ''}
                            onClick={() => setCurrentSpeaker('agent')}
                            type="button"
                        >
                            Agent
                        </button>
                        <button
                            className={currentSpeaker === 'customer' ? 'active' : ''}
                            onClick={() => setCurrentSpeaker('customer')}
                            type="button"
                        >
                            Customer
                        </button>
                    </div>
                </div>
                <div className="controls">
                    <button onClick={startCall} disabled={isCallActive}>Start Call</button>
                    <button onClick={endCall} disabled={!isCallActive}>End Call</button>
                </div>
            </section>

            {statusMessage && <div className="status-banner">{statusMessage}</div>}

            <section className="panel">
                <h3>Manual Note</h3>
                <textarea
                    rows="3"
                    value={draftText}
                    onChange={(e) => setDraftText(e.target.value)}
                    placeholder="Use this when you need to annotate or correct the transcript."
                />
                <button onClick={sendManualStatement} disabled={!sessionId}>Send to Copilot</button>
            </section>

            <section className="grid two-column">
                <div className="panel">
                    <h3>Transcript</h3>
                    <div className="scroller">
                        {transcript.map((item, index) => (
                            <div key={`${item.speaker}-${index}`} className={`transcript-line ${item.speaker}`}>
                                <span>{item.speaker.toUpperCase()}</span>
                                <p>{item.text}</p>
                                <small>{item.at ? new Date(item.at).toLocaleTimeString() : ''}</small>
                            </div>
                        ))}
                        {!transcript.length && <p className="empty-state">No transcript yet.</p>}
                    </div>
                </div>
                <div className="panel">
                    <h3>Warnings</h3>
                    <div className="scroller">
                        {warnings.map((warning, index) => (
                            <div key={`${warning.rule}-${index}`} className={`warning-card ${warning.level || 'WARNING'}`}>
                                <header>
                                    <strong>{warning.level}</strong>
                                    <span>{warning.rule}</span>
                                </header>
                                <p>{warning.text}</p>
                                {warning.suggestion_agent && <small>{warning.suggestion_agent}</small>}
                            </div>
                        ))}
                        {!warnings.length && <p className="empty-state">No warnings triggered.</p>}
                    </div>
                </div>
            </section>

            {callResult && (
                <section className="panel analysis">
                    <div>
                        <h3>Compliance Score</h3>
                        <p className="score">{callResult.compliance_score}</p>
                    </div>
                    <div>
                        <h4>Key Topics</h4>
                        <ul>
                            {(callResult.key_topics || []).map((topic) => (
                                <li key={topic}>{topic}</li>
                            ))}
                        </ul>
                    </div>
                    <div className="analysis-summary">
                        <h4>Summary</h4>
                        <p>{callResult.summary_text}</p>
                    </div>
                    {callRecordId && (
                        <a className="link-button" href={`/call/${callRecordId}`} target="_blank" rel="noreferrer">
                            View saved call report
                        </a>
                    )}
                </section>
            )}
        </div>
    );
};

export default LiveCopilotView;
