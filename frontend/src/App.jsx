import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { io } from "socket.io-client";
import Sidebar from "./components/Sidebar.jsx";
import Transcript from "./components/Transcript.jsx";
import WarningsPanel from "./components/WarningsPanel.jsx";
import { ShieldCheck } from "lucide-react";

const API_BASE = (import.meta?.env?.VITE_API_URL || "http://127.0.0.1:5000").replace(/\/$/, "");
const CALL_STORAGE_KEY = "ethico_call_snapshot";
const SELECTION_STORAGE_KEY = "ethico_call_selection";
const THEME_STORAGE_KEY = "ethico_theme";

const withBase = (path) => {
  if (!path.startsWith("/")) {
    path = `/${path}`;
  }
  if (!API_BASE) {
    return path;
  }
  return `${API_BASE}${path}`;
};

const blobToBase64 = (blob) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = reader.result;
      resolve(typeof result === "string" ? result.split(",")[1] : "");
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });

export default function App() {
  const [call, setCall] = useState(null);
  const [messages, setMessages] = useState([]);
  const [warnings, setWarnings] = useState([]);
  const [agents, setAgents] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState("");
  const [selectedCustomer, setSelectedCustomer] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [isCallActive, setIsCallActive] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [mode, setMode] = useState("live");
  const [uploadFile, setUploadFile] = useState(null);
  const [isProcessingUpload, setIsProcessingUpload] = useState(false);
  const [theme, setTheme] = useState(() => {
    if (typeof window === "undefined") return "dark";
    return window.localStorage.getItem(THEME_STORAGE_KEY) || "dark";
  });

  const socketRef = useRef(null);
  const sessionIdRef = useRef("");
  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);

  useEffect(() => {
    document.title = "EthiCo Live";
  }, []);

  useEffect(() => {
    if (typeof document === "undefined") return;
    const root = document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    if (typeof window !== "undefined") {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    }
  }, [theme]);

  const applySnapshot = useCallback((snapshot) => {
    if (!snapshot) {
      setCall(null);
      setMessages([]);
      setWarnings([]);
      return;
    }
    setCall(snapshot);
    setMessages(snapshot.transcript || []);
    setWarnings(snapshot.warnings || []);
    if (typeof window !== "undefined") {
      try {
        window.localStorage.setItem(CALL_STORAGE_KEY, JSON.stringify(snapshot));
      } catch {
        // ignore storage failures
      }
    }
  }, []);

  const fetchCurrentCall = useCallback(async () => {
    try {
      const res = await fetch(withBase("/api/call/current"));
      if (!res.ok) return;
      const snapshot = await res.json();
      if (snapshot?.callId) {
        applySnapshot(snapshot);
        if (snapshot.status === "in_progress") {
          setSessionId(snapshot.callId);
          sessionIdRef.current = snapshot.callId;
          setIsCallActive(true);
          setSelectedAgent(snapshot.agent?.id || "");
          setSelectedCustomer(snapshot.customer?.id || "");
        } else {
          setIsCallActive(false);
          setSessionId("");
          sessionIdRef.current = "";
        }
      }
    } catch (error) {
      console.warn("Unable to load current call", error);
    }
  }, [applySnapshot]);

  useEffect(() => {
    let cancelled = false;
    async function loadDirectory() {
      try {
        const res = await fetch(withBase("/api/directory"));
        if (!res.ok) return;
        const data = await res.json();
        if (cancelled) return;
        setAgents(data.agents || []);
        setCustomers(data.customers || []);
        if (!selectedAgent && data.agents?.length) {
          setSelectedAgent(data.agents[0].id);
        }
        if (!selectedCustomer && data.customers?.length) {
          setSelectedCustomer(data.customers[0].id);
        }
      } catch (error) {
        console.warn("Unable to load directory", error);
      }
    }
    loadDirectory();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    try {
      const cachedCall = window.localStorage.getItem(CALL_STORAGE_KEY);
      if (cachedCall) {
        const snapshot = JSON.parse(cachedCall);
        if (snapshot?.callId) {
          applySnapshot(snapshot);
        }
      }
    } catch {
      // ignore invalid cache
    }
    try {
      const selectionRaw = window.localStorage.getItem(SELECTION_STORAGE_KEY);
      if (selectionRaw) {
        const parsed = JSON.parse(selectionRaw);
        if (parsed?.agentId) {
          setSelectedAgent(parsed.agentId);
        }
        if (parsed?.customerId) {
          setSelectedCustomer(parsed.customerId);
        }
      }
    } catch {
      // ignore invalid cache
    }
  }, [applySnapshot]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    if (!selectedAgent && !selectedCustomer) {
      window.localStorage.removeItem(SELECTION_STORAGE_KEY);
      return;
    }
    try {
      window.localStorage.setItem(
        SELECTION_STORAGE_KEY,
        JSON.stringify({ agentId: selectedAgent, customerId: selectedCustomer })
      );
    } catch {
      // ignore
    }
  }, [selectedAgent, selectedCustomer]);

  const stopStreaming = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      try {
        recorder.stop();
      } catch {
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
  }, []);

  useEffect(() => {
    const socketTarget = API_BASE || "http://127.0.0.1:5000";
    const socket = io(socketTarget, {
      transports: ["websocket", "polling"],
      withCredentials: false,
    });
    socketRef.current = socket;

    socket.on("update_transcript", (entry) => {
      setMessages((prev) => [...prev, entry]);
      setCall((prev) =>
        prev
          ? { ...prev, transcript: [...(prev.transcript || []), entry] }
          : prev
      );
    });

    socket.on("new_warning", (payload) => {
      const items = Array.isArray(payload) ? payload : [payload];
      setWarnings((prev) => [...prev, ...items]);
    });

    socket.on("session_status", (payload) => {
      if (!payload) return;
      if (payload.status === "abandoned") {
        setStatusMessage("Session timed out due to inactivity.");
        setIsCallActive(false);
        stopStreaming();
        setSessionId("");
        sessionIdRef.current = "";
        fetchCurrentCall();
      }
      if (payload.status === "completed") {
        setStatusMessage("Call completed and saved.");
        setIsCallActive(false);
        stopStreaming();
        setSessionId("");
        sessionIdRef.current = "";
        fetchCurrentCall();
      }
    });

    return () => {
      socket.disconnect();
    };
  }, [fetchCurrentCall, stopStreaming]);

  useEffect(() => {
    if (sessionId && socketRef.current) {
      socketRef.current.emit("register_session", { session_id: sessionId });
    }
  }, [sessionId]);

  useEffect(() => {
    if (!isCallActive || !call?.startedAt) return;
    const updateDuration = () => {
      setCall((prev) => {
        if (!prev?.startedAt) return prev;
        const delta =
          Date.now() - new Date(prev.startedAt).getTime();
        return {
          ...prev,
          durationSeconds: Math.max(0, Math.floor(delta / 1000)),
        };
      });
    };
    updateDuration();
    const id = setInterval(updateDuration, 1000);
    return () => clearInterval(id);
  }, [isCallActive, call?.startedAt]);

  useEffect(() => () => stopStreaming(), [stopStreaming]);

  const startStreaming = useCallback(
    async (activeSessionId) => {
      if (!socketRef.current || isStreaming || !activeSessionId) return;
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
        });
        const recorder = new MediaRecorder(stream, {
          mimeType: "audio/webm;codecs=opus",
        });
        mediaRecorderRef.current = recorder;
        mediaStreamRef.current = stream;
        recorder.ondataavailable = async (event) => {
          if (!event.data.size || !socketRef.current) return;
          const base64Chunk = await blobToBase64(event.data);
          socketRef.current.emit("stream_audio", {
            session_id: activeSessionId,
            speaker: "agent",
            audio_base64: base64Chunk,
            mime_type: recorder.mimeType,
          });
        };
        recorder.start(1500);
        setIsStreaming(true);
      } catch (error) {
        console.error("Unable to access microphone", error);
        setStatusMessage("Microphone access denied.");
      }
    },
    [isStreaming, setStatusMessage]
  );

  const startCall = useCallback(async () => {
    if (mode !== "live") {
      setStatusMessage("Switch to Live mode to start streaming.");
      return;
    }
    if (!selectedAgent || !selectedCustomer) {
      setStatusMessage("Select an agent and a customer to begin.");
      return;
    }
    if (isStarting || isCallActive) return;
    setIsStarting(true);
    setStatusMessage("Starting call session...");
    try {
      const res = await fetch(withBase("/api/call/start"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agentId: selectedAgent,
          customerId: selectedCustomer,
        }),
      });
      const payload = await res.json();
      if (!res.ok) {
        throw new Error(payload.error || "Unable to start call.");
      }
      const snapshot = payload.call;
      if (snapshot) {
        applySnapshot(snapshot);
      }
      if (snapshot?.agent?.id) setSelectedAgent(snapshot.agent.id);
      if (snapshot?.customer?.id) setSelectedCustomer(snapshot.customer.id);
      const newSessionId = payload.sessionId;
      setSessionId(newSessionId);
      sessionIdRef.current = newSessionId;
      setIsCallActive(true);
      setStatusMessage("Call in progress. Streaming audio...");
      await startStreaming(newSessionId);
    } catch (error) {
      console.error(error);
      setStatusMessage(error.message || "Unable to start call.");
      stopStreaming();
      setIsCallActive(false);
      setSessionId("");
      sessionIdRef.current = "";
    } finally {
      setIsStarting(false);
    }
  }, [
    applySnapshot,
    selectedAgent,
    selectedCustomer,
    isStarting,
    isCallActive,
    startStreaming,
    stopStreaming,
    mode,
  ]);

  const stopCall = useCallback(async () => {
    if (mode !== "live") {
      setStatusMessage("Live session not running.");
      return;
    }
    if (!sessionIdRef.current) {
      setStatusMessage("No active session to stop.");
      return;
    }
    if (isStopping) return;
    setIsStopping(true);
    setStatusMessage("Ending call...");
    stopStreaming();
    try {
      const res = await fetch(withBase("/api/call/stop"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sessionId: sessionIdRef.current }),
      });
      const payload = await res.json();
      if (!res.ok) {
        throw new Error(payload.error || "Unable to stop call.");
      }
      if (payload.call) {
        applySnapshot(payload.call);
      }
      setSessionId("");
      sessionIdRef.current = "";
      setIsCallActive(false);
      setStatusMessage("Call completed and saved.");
    } catch (error) {
      console.error(error);
      setStatusMessage(error.message || "Failed to stop call.");
    } finally {
      setIsStopping(false);
    }
  }, [applySnapshot, stopStreaming, isStopping, mode]);

  const resetInterface = useCallback((message) => {
    stopStreaming();
    setSessionId("");
    sessionIdRef.current = "";
    setIsCallActive(false);
    setCall(null);
    setMessages([]);
    setWarnings([]);
    setUploadFile(null);
    setStatusMessage(
      message || "Session reset. Select participants and start a new call."
    );
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(CALL_STORAGE_KEY);
      window.localStorage.removeItem(SELECTION_STORAGE_KEY);
    }
  }, [stopStreaming]);

  const handleModeChange = useCallback(
    (nextMode) => {
      if (nextMode === mode) return;
      if (nextMode === "live") {
        resetInterface("Switched to live mode. Ready to stream audio.");
      } else {
        resetInterface("Switched to upload mode. Select a recording to process.");
      }
      setMode(nextMode);
    },
    [mode, resetInterface]
  );

  const processUpload = useCallback(async () => {
    if (mode !== "upload") {
      setStatusMessage("Switch to Upload mode to process recordings.");
      return;
    }
    if (!selectedAgent || !selectedCustomer) {
      setStatusMessage("Select an agent and customer before uploading.");
      return;
    }
    if (!uploadFile) {
      setStatusMessage("Choose an audio file to process.");
      return;
    }
    setIsProcessingUpload(true);
    setStatusMessage("Processing uploaded recording...");
    try {
      const formData = new FormData();
      formData.append("recording", uploadFile);
      formData.append("agentId", selectedAgent);
      formData.append("customerId", selectedCustomer);
      const res = await fetch(withBase("/api/call/upload"), {
        method: "POST",
        body: formData,
      });
      const payload = await res.json();
      if (!res.ok) {
        throw new Error(payload.error || "Unable to process recording.");
      }
      if (payload.call) {
        applySnapshot(payload.call);
      }
      setSessionId("");
      sessionIdRef.current = "";
      setIsCallActive(false);
      setUploadFile(null);
      setStatusMessage("Recording processed successfully.");
    } catch (error) {
      console.error(error);
      setStatusMessage(error.message || "Failed to process recording.");
    } finally {
      setIsProcessingUpload(false);
    }
  }, [
    mode,
    selectedAgent,
    selectedCustomer,
    uploadFile,
    applySnapshot,
    setStatusMessage,
  ]);
  const callStatus = useMemo(
    () => (isCallActive ? "Live" : call?.status === "completed" ? "Completed" : "Idle"),
    [isCallActive, call?.status]
  );

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  }, []);

  return (
    <div className="flex min-h-screen bg-gray-50 text-gray-900 dark:bg-slate-950 dark:text-slate-100">
      <Sidebar call={call} warnings={warnings} isCallActive={isCallActive} />

      <main className="flex-1 flex flex-col bg-white dark:bg-slate-900">
        <div className="px-10 py-6 border-b border-gray-200 bg-white dark:bg-slate-900 dark:border-slate-800 space-y-6">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <h1 className="text-xl font-semibold text-gray-900 dark:text-slate-100">EthiCo Live Copilot</h1>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Select an agent and customer, then start streaming to monitor FDCPA compliance.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={toggleTheme}
                className="px-3 py-1 rounded-full border border-gray-300 text-xs font-semibold text-gray-600 dark:text-slate-100 dark:border-slate-700 bg-white dark:bg-slate-800"
              >
                {theme === "dark" ? "Dark Mode" : "Light Mode"}
              </button>
              <div className="px-3 py-1 rounded-full border text-xs font-semibold text-gray-600 dark:text-slate-100 border-gray-300 dark:border-slate-700">
                {callStatus}
                {sessionId ? ` • ${sessionId}` : ""}
              </div>
            </div>
          </div>

          <ControlPanel
            agents={agents}
            customers={customers}
            selectedAgent={selectedAgent}
            selectedCustomer={selectedCustomer}
            onAgentChange={setSelectedAgent}
            onCustomerChange={setSelectedCustomer}
            mode={mode}
            onModeChange={handleModeChange}
            onStart={startCall}
            onStop={stopCall}
            onReset={resetInterface}
            isCallActive={isCallActive}
            isStarting={isStarting}
            isStopping={isStopping}
            sessionId={sessionId}
            isStreaming={isStreaming}
            uploadFile={uploadFile}
            onUploadFileChange={setUploadFile}
            onProcessUpload={processUpload}
            isProcessingUpload={isProcessingUpload}
          />
        </div>

        {statusMessage && (
          <StatusBanner message={statusMessage} />
        )}

        <div className="flex-1 px-10 py-6 flex flex-col gap-6 lg:flex-row overflow-hidden min-h-0">
          <div className="flex-1 min-h-0">
            <Transcript messages={messages} mode={mode} />
          </div>

          <div className="w-full lg:w-96 flex flex-col gap-6 min-h-0">
            <WarningsPanel warnings={warnings} />
          </div>
        </div>

        <div className="px-10 pb-4 text-[10px] text-gray-400 dark:text-gray-500 flex items-center gap-2">
          <ShieldCheck size={12} className="text-emerald-500" />
          <span>
            Monitoring language for risk &amp; empathy. Start/Stop controls the live analysis session.
          </span>
        </div>
      </main>
    </div>
  );
}

function ControlPanel({
  agents,
  customers,
  selectedAgent,
  selectedCustomer,
  onAgentChange,
  onCustomerChange,
  mode,
  onModeChange,
  onStart,
  onStop,
  onReset,
  isCallActive,
  isStarting,
  isStopping,
  sessionId,
  isStreaming,
  uploadFile,
  onUploadFileChange,
  onProcessUpload,
  isProcessingUpload,
}) {
  const canStart = Boolean(
    selectedAgent && selectedCustomer && !isCallActive && !isStarting
  );
  const canStop = Boolean(isCallActive && !isStopping);

  return (
    <div className="flex flex-col gap-4 lg:gap-6">
      <div className="flex flex-wrap items-center gap-3">
        <FormField label="Mode">
          <div className="inline-flex rounded-full border border-gray-200 bg-white dark:bg-slate-900 dark:border-slate-700 p-1 text-xs font-semibold">
            {["live", "upload"].map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => onModeChange(option)}
                className={`px-3 py-1 rounded-full transition ${
                  mode === option
                    ? "bg-gray-900 text-white shadow"
                    : "text-gray-600 dark:text-gray-300"
                }`}
              >
                {option === "live" ? "Live Microphone" : "Upload Recording"}
              </button>
            ))}
          </div>
        </FormField>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <FormField label="Agent">
          <select
            value={selectedAgent}
            onChange={(e) => onAgentChange(e.target.value)}
            className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            <option value="">Select agent</option>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name} • {agent.team}
              </option>
            ))}
          </select>
        </FormField>

        <FormField label="Customer">
          <select
            value={selectedCustomer}
            onChange={(e) => onCustomerChange(e.target.value)}
            className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            <option value="">Select customer</option>
            {customers.map((customer) => (
              <option key={customer.id} value={customer.id}>
                {customer.name} • {customer.account_number}
              </option>
            ))}
          </select>
        </FormField>

        <FormField label="Session">
          <div className="h-full flex items-center justify-center text-sm text-gray-600">
            {sessionId || "Not started"}
          </div>
        </FormField>
      </div>


      {mode === "live" ? (
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={onStart}
            disabled={!canStart}
            className={`px-4 py-2 rounded-full text-xs font-semibold transition ${
              canStart
                ? "bg-emerald-500 text-white shadow-sm shadow-emerald-200"
                : "bg-emerald-100 text-emerald-500 cursor-not-allowed"
            }`}
          >
            {isStarting ? "Starting..." : isStreaming ? "Streaming..." : "Start"}
          </button>

          <button
            onClick={onStop}
            disabled={!canStop}
            className={`px-4 py-2 rounded-full text-xs font-semibold transition ${
              canStop
                ? "bg-red-500 text-white shadow-sm shadow-red-200"
                : "bg-red-100 text-red-500 cursor-not-allowed"
            }`}
          >
            {isStopping ? "Stopping..." : "Stop"}
          </button>

          <button
            type="button"
            onClick={() => onReset()}
            className="px-4 py-2 rounded-full text-xs font-semibold border border-gray-300 text-gray-600 bg-white hover:bg-gray-50 transition"
          >
            Reset
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          <FormField label="Recording File">
            <label className="inline-flex items-center gap-3 cursor-pointer">
              <span className="px-4 py-2 rounded-full bg-gray-900 text-white text-xs font-semibold">
                Choose File
              </span>
              <input
                type="file"
                accept="audio/*"
                onChange={(e) => onUploadFileChange(e.target.files?.[0] || null)}
                className="sr-only"
              />
              <span className="text-xs text-gray-500">
                {uploadFile ? uploadFile.name : "No file selected"}
              </span>
            </label>
          </FormField>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={onProcessUpload}
              disabled={
                !uploadFile ||
                !selectedAgent ||
                !selectedCustomer ||
                isProcessingUpload
              }
              className={`px-4 py-2 rounded-full text-xs font-semibold transition ${
                uploadFile && selectedAgent && selectedCustomer && !isProcessingUpload
                  ? "bg-indigo-600 text-white shadow-sm shadow-indigo-200"
                  : "bg-indigo-100 text-indigo-400 cursor-not-allowed"
              }`}
            >
              {isProcessingUpload ? "Processing..." : "Process Recording"}
            </button>
            <button
              type="button"
              onClick={() => onReset()}
              className="px-4 py-2 rounded-full text-xs font-semibold border border-gray-300 text-gray-600 bg-white hover:bg-gray-50 transition"
            >
              Reset
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function FormField({ label, children }) {
  return (
    <label className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
      <span className="block">{label}</span>
      {children}
    </label>
  );
}

function StatusBanner({ message }) {
  return (
    <div className="px-10">
      <div className="bg-amber-50 border border-amber-200 text-amber-800 dark:bg-amber-500/10 dark:border-amber-500/40 dark:text-amber-200 rounded-xl px-4 py-2 text-xs font-medium">
        {message}
      </div>
    </div>
  );
}
