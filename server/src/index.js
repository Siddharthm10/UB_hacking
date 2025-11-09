import http from 'http';
import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import mongoose from 'mongoose';
import { Server as SocketIOServer } from 'socket.io';

dotenv.config();

const app = express();
const server = http.createServer(app);
const io = new SocketIOServer(server, {
  cors: { origin: '*' },
});

app.use(cors());
app.use(express.json());

// Mongo setup
const MONGODB_URI = process.env.MONGODB_URI;
const PORT = process.env.PORT || 4000;

if (!MONGODB_URI) {
  console.error('Missing MONGODB_URI. Set it in server/.env');
}

// Schemas
const TranscriptLineSchema = new mongoose.Schema(
  {
    speaker: { type: String, enum: ['agent', 'customer'], required: true },
    text: { type: String, required: true },
    at: { type: Date, default: Date.now },
  },
  { _id: false }
);

const CallSchema = new mongoose.Schema(
  {
    callId: { type: String, index: true, unique: true },
    startedAt: { type: Date, default: Date.now },
    durationSeconds: { type: Number, default: 0 },
    status: { type: String, enum: ['active', 'ended'], default: 'active' },
    customer: {
      name: String,
      phone: String,
      accountId: String,
      status: String,
    },
    agent: {
      name: String,
      agentId: String,
    },
    transcript: [TranscriptLineSchema],
  },
  { timestamps: true }
);

const Call = mongoose.model('Call', CallSchema);

// Health
app.get('/health', (_req, res) => res.json({ ok: true }));

// Seed endpoint for quick demo
app.post('/api/calls/seed', async (_req, res) => {
  try {
    const doc = await Call.findOne({ callId: 'CID-8675309' });
    if (doc) return res.json(doc);

    const seeded = await Call.create({
      callId: 'CID-8675309',
      durationSeconds: 0,
      customer: {
        name: 'Jane Doe',
        phone: '+1 (555) 123-4567',
        accountId: 'ACC-98765',
        status: 'Premium',
      },
      agent: { name: 'Alex Smith', agentId: 'AGENT-007' },
      transcript: [
        { speaker: 'customer', text: "Hi, I'm having an issue with my last order." },
        { speaker: 'agent', text: 'Hello Jane, I can certainly help you. Could you confirm your order number?' },
      ],
    });
    res.status(201).json(seeded);
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: 'Failed to seed' });
  }
});

// List calls (limited)
app.get('/api/calls', async (_req, res) => {
  const docs = await Call.find().sort({ createdAt: -1 }).limit(20);
  res.json(docs);
});

// Get by callId
app.get('/api/calls/:id', async (req, res) => {
  const call = await Call.findOne({ callId: req.params.id });
  if (!call) return res.status(404).json({ error: 'Not found' });
  res.json(call);
});

// Append transcript line
app.post('/api/calls/:id/transcript', async (req, res) => {
  const { speaker, text } = req.body || {};
  if (!speaker || !text) return res.status(400).json({ error: 'speaker and text required' });
  const call = await Call.findOne({ callId: req.params.id });
  if (!call) return res.status(404).json({ error: 'Call not found' });
  const line = { speaker, text, at: new Date() };
  call.transcript.push(line);
  await call.save();
  // Emit to a specific room for this call
  io.to(`call:${call.callId}`).emit('transcript', { callId: call.callId, line });
  res.status(201).json(line);
});

// Socket.io basic join room by callId (optional for future)
io.on('connection', (socket) => {
  socket.on('join', (callId) => {
    if (callId) socket.join(`call:${callId}`);
  });
});

// Start
async function start() {
  if (MONGODB_URI) {
    await mongoose.connect(MONGODB_URI, { dbName: 'agent_dashboard' });
    console.log('MongoDB connected');
  }
  server.listen(PORT, () => console.log(`API listening on :${PORT}`));
}

start().catch((e) => {
  console.error('Failed to start server', e);
  process.exit(1);
});
