const express = require('express');
const { MongoClient } = require('mongodb');
const os = require('os');
const path = require('path');

// ---- Configuration (environment variables only) ----
const MONGO_URL = process.env.MONGO_URL;
const DB_NAME = process.env.DB_NAME || 'emiapp';
const PORT = process.env.PORT || 3000;
const POD_NAME = process.env.HOSTNAME || os.hostname();

if (!MONGO_URL) {
  console.error('MONGO_URL environment variable is required');
  process.exit(1);
}

function getPodIp() {
  for (const addrs of Object.values(os.networkInterfaces())) {
    for (const a of addrs || []) {
      if (a.family === 'IPv4' && !a.internal) return a.address;
    }
  }
  return '127.0.0.1';
}
const POD_IP = getPodIp();

// The driver connects lazily and reconnects on its own, so the app can start
// before MongoDB is ready; /health reports the real state.
const client = new MongoClient(MONGO_URL, { serverSelectionTimeoutMS: 3000 });
const calculations = client.db(DB_NAME).collection('calculations');

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

const round2 = (x) => Math.round(x * 100) / 100;

// Positive finite number check; also accepts numeric strings.
function toPositive(v) {
  if (v === '' || v === null || v === undefined || typeof v === 'boolean') return NaN;
  const num = Number(v);
  return Number.isFinite(num) && num > 0 ? num : NaN;
}

// ---- POST /api/emi ----
app.post('/api/emi', async (req, res) => {
  const principal = toPositive(req.body.P);
  const rate = toPositive(req.body.rate);
  const months = toPositive(req.body.n);

  const errors = {};
  if (Number.isNaN(principal)) errors.P = 'Loan amount must be a positive number';
  if (Number.isNaN(rate)) errors.rate = 'Interest rate must be a positive number';
  if (Number.isNaN(months) || !Number.isInteger(months)) errors.n = 'Tenure must be a positive whole number of months';
  if (Object.keys(errors).length) return res.status(400).json({ error: 'Invalid input', errors });

  const r = rate / 12 / 100;
  const pow = Math.pow(1 + r, months);
  const emi = (principal * r * pow) / (pow - 1);
  if (!Number.isFinite(emi)) {
    return res.status(400).json({ error: 'Values are too large to calculate' });
  }

  const result = {
    emi: round2(emi),
    totalPayment: round2(emi * months),
    totalInterest: round2(emi * months - principal),
    servedBy: { pod: POD_NAME, ip: POD_IP },
  };

  try {
    await calculations.insertOne({
      principal,
      rate,
      months,
      emi: result.emi,
      servedBy: POD_NAME,
      createdAt: new Date(),
    });
  } catch (err) {
    console.error('Mongo insert failed:', err.message);
    return res.status(503).json({ error: 'Database unavailable, calculation not saved' });
  }
  res.json(result);
});

// ---- GET /api/history ----
app.get('/api/history', async (req, res) => {
  try {
    const rows = await calculations
      .find({}, { projection: { _id: 0 } })
      .sort({ createdAt: -1 })
      .limit(10)
      .toArray();
    res.json(rows);
  } catch (err) {
    console.error('Mongo query failed:', err.message);
    res.status(503).json({ error: 'Database unavailable' });
  }
});

// ---- GET /health (readiness probe: 200 only if MongoDB is reachable) ----
app.get('/health', async (req, res) => {
  try {
    await client.db('admin').command({ ping: 1 });
    res.status(200).json({ status: 'ok' });
  } catch (err) {
    res.status(503).json({ status: 'mongo unreachable' });
  }
});

const server = app.listen(PORT, () => console.log(`EMI app on :${PORT} (pod ${POD_NAME})`));

// Graceful shutdown (Kubernetes sends SIGTERM)
process.on('SIGTERM', async () => {
  server.close();
  await client.close();
  process.exit(0);
});
