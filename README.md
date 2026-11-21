# GREENTRACK PRO — CLIMATE INTELLIGENCE PLATFORM
## Hack Fest 2026 | PS-01: Carbon Footprint Tracking and Reduction Platform
### Autonomous Measurement · Explainable AI · IoT Hardware Telemetry · Multi-Sector Optimization

GreenTrack is a production-quality, AI-powered carbon intelligence and reduction platform designed for **Individuals, Colleges, and Organizations**. Built with **React 18 + TypeScript + Vite + Tailwind CSS** on the frontend and **FastAPI + SQLite + PyMuPDF + Scikit-Learn** on the backend.

Core workflow: **Measure → Calculate → Explain → Recommend → Reduce → Verify → Report**

## Machine-learning pipeline

The optional, reproducible ML pipeline is implemented in `backend/ml/`. It provides
Isolation Forest anomaly detection, Gradient Boosting emission prediction, and a
monthly Ridge time-trend forecast. Models train from prepared, real activity data;
the API reports `503` when artifacts are unavailable instead of inventing predictions.
See [ML_DOCUMENTATION.md](./ML_DOCUMENTATION.md), [API_DOCUMENTATION.md](./API_DOCUMENTATION.md),
and [data/README.md](./data/README.md) for dataset sources and commands.

The knowledge assistant supports Gemini or OpenAI through `backend/.env`.
Set `AI_PROVIDER=gemini` with `GEMINI_API_KEY`, or set `AI_PROVIDER=openai`
with `OPENAI_API_KEY`. The key is read only by the backend and must never be
committed or pasted into source files.

## Production preparation

The repository includes a containerized production setup:

```powershell
Copy-Item .env.production.example .env
docker compose -f docker-compose.production.yml up --build -d
```

Set `GREENTRACK_ALLOWED_ORIGINS`, `GREENTRACK_TRUSTED_HOSTS`, and
`GREENTRACK_COOKIE_SECURE=true` for a real HTTPS domain. The backend uses a
persistent SQLite volume in this setup because the current data layer is
implemented directly with `sqlite3` and SQLite-specific schema/queries.
Migrating to PostgreSQL requires a dedicated adapter and schema migration; do
not set a PostgreSQL URL and assume it is supported.

### Production TLS certificates

The production Nginx configuration terminates TLS on port 443 and redirects port
80 to HTTPS. Do not commit certificate private keys.

Place `fullchain.pem` and `privkey.pem` in an external directory, set
`GREENTRACK_TLS_CERT_DIR` to that directory, and keep
`GREENTRACK_COOKIE_SECURE=true`. Example:

```text
GREENTRACK_ALLOWED_ORIGINS=https://your-domain.example
GREENTRACK_TRUSTED_HOSTS=your-domain.example
GREENTRACK_COOKIE_SECURE=true
GREENTRACK_TLS_CERT_DIR=/absolute/path/to/certificates
```

The Compose mount exposes only the certificate directory read-only to Nginx.
Renew certificates outside the repository and remount/restart the frontend
container after certificate replacement.

CI runs Python compilation/tests and the frontend production build. Production
operations still require TLS termination, secret storage, backups, monitoring,
and a tested restore procedure at the hosting provider.

---

## 1. Architecture & Design

### System Architecture Diagram

```mermaid
flowchart TD
    subgraph UI ["Futuristic Digital Climate Intelligence UI (No Green)"]
        IND["Individual Experience\n(Score Dial, GPS Trips, Trees & INR)"]
        ORG["Organization Experience\n(Scope 1-3, Multi-Site, AI Advisor)"]
        COL["Campus Experience\n(Digital Twin, Canteen Waste, Leaderboard)"]
    end

    subgraph API ["FastAPI 0.115 Application Gateway"]
        AUTH["Session & CSRF Security Engine"]
        INGEST["Multi-Modal Ingestion\n(GPS, OCR Bills, ESP32 IoT, Manual)"]
        ENGINE["Traceable Carbon Calculation Engine\n(CEA, IPCC, DEFRA, EPA)"]
        XAI["Explainable AI & ML Analytics\n(Z-Score Anomaly, Trend Forecasting)"]
    end

    subgraph DATA ["Persistence & Knowledge Layer"]
        DB[(SQLite / SQLAlchemy Data Lake)]
        DOCS["Authoritative Emission Factors & Evidence"]
    end

    IND --> INGEST
    ORG --> INGEST
    COL --> INGEST

    INGEST --> AUTH --> ENGINE
    ENGINE --> DB
    ENGINE --> XAI
    XAI --> DB
    XAI --> UI
    DOCS --> ENGINE
```

### Activity Ingestion & Calculation Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Sensor / GPS
    participant API as FastAPI Ingestion Endpoint
    participant Filter as Data Validation & Haversine Filter
    participant Engine as Traceable Calculation Engine
    participant DB as SQLite Activities Ledger
    participant XAI as Explainable AI & Anomaly Engine
    participant UI as Dashboard Real-Time View

    User->>API: Submit Reading / Bill / GPS Track / Activity
    alt GPS Ingestion
        API->>Filter: Filter Points (Accuracy <= 50m, Speed < 300 km/h)
        Filter->>Engine: Validated Distance (km) + Transport Mode
    else Utility Bill OCR
        API->>Filter: PyMuPDF / Tesseract Text Parsing
        Filter->>Engine: Extracted kWh & Billing Period (YYYY-MM)
    else Hardware Telemetry
        API->>Filter: Consecutive Interval Delta Calculation
        Filter->>Engine: Net Interval Consumption (kWh)
    end
    Engine->>Engine: Quantity × Traceable Emission Factor
    Engine->>DB: Store Verified Activity Record + Scope Classification
    DB->>XAI: Historical Consumption Time-Series
    XAI->>XAI: Statistical Z-Score Outlier Flagging & Trend Regression
    XAI->>UI: Personal Score, Reduction Opportunities, Formula Proofs
```

---

## 2. Three Distinct Connected Experiences

### 1. Individual Dashboard (Personal Carbon Management)
- **Personal Carbon Score Dial (0–100)**: Evaluated dynamically against India’s per-capita monthly baseline (~158 kg CO₂e).
- **Opt-In GPS Haversine Trip Tracker**:
  - Distance filtering with $\le 50\text{m}$ accuracy thresholding and speed outlier rejection ($< 300\text{ km/h}$).
  - Multi-modal transport emissions: Passenger Car ($0.170$), 2-Wheeler ($0.045$), Transit Bus ($0.089$), Active Walking/Cycling ($0.000\text{ kg CO}_2\text{e/km}$).
  - Automatically logs verified trips into the central activity ledger with `data_origin="gps"`.
- **Environmental & Financial Equivalents**: Real-time tree absorption requirements ($22\text{ kg CO}_2\text{/tree/year}$ per IPCC guidelines) and domestic utility bill savings ($\text{₹}$).
- **AI Anomaly Detection**: Statistical Z-score outlier alerts ($Z > 1.8$) flagging unexpected consumption spikes.
- **ESP32 IoT Telemetry**: Household smart meter monitor tracking Power (W), Line Voltage (V), Current (A), Energy (kWh), and DHT11/22 Temperature and Humidity.

### 2. Organization Dashboard (Enterprise Control Room)
- **Multi-Site Facility Registry**: Centralized asset tracking across Headquarters, Manufacturing Plants, Logistics Warehouses, and Regional Branches with square footage and occupancy data.
- **GHG Protocol Scope Classification**: Automatic categorization into **Scope 1** (direct fuel combustion, on-site generators, fleet), **Scope 2** (purchased grid electricity), and **Scope 3** (supply water, employee travel, municipal waste).
- **AI Operations Advisor**: Algorithmic ranking of operational decarbonization initiatives displaying estimated avoided emissions ($\text{kg CO}_2\text{e}$), required Capex ($\text{₹}$), payback period (months), and feasibility scoring.
- **Bulk Utility Import**: Ingests multi-meter utility data via batch JSON / CSV formats.

### 3. College / Campus Dashboard (Smart Campus Digital Twin)
- **Campus Digital Twin Building Telemetry**: Real-time sub-metering across campus facilities (Sir CV Raman Academic Complex, Aryabhatta & Kalpana Chawla Student Hostels, Central Food Court, APJ Abdul Kalam Research Labs) tracking electricity ($\text{kWh}$) and water draw ($\text{kL}$).
- **Daily Canteen Food Waste & Composting Tracker**: Logs dining mess food waste and quantifies avoided landfill methane from on-site composting ($0.625\text{ kg CO}_2\text{e/kg}$ organic waste avoided).
- **Campus Transit Bus Tracker**: Schedules, passenger capacity, and route emission monitoring.
- **Event Carbon Calculator**: Evaluates college symposiums, hackathons, and cultural fests across attendance, duration, diesel generator usage, and attendee travel.
- **Student Green Challenges & Hostel Leaderboard**: Gamified climate action platform where hostels and departments join verified initiatives to earn climate impact points.

---

## 3. Futuristic Design System (Strictly No Green)

The entire platform adheres to a high-contrast **Digital Climate Intelligence** aesthetic:

| Color Role | Name | Hex Code | UI Application |
|---|---|---|---|
| Background Canvas | Midnight Navy | `#080D1B` | Deep atmospheric workspace background |
| Surface Panels | Deep Violet | `#17102B` | Glassmorphic card surfaces and sidebars |
| Accent Primary | Electric Cyan | `#00E5FF` | Metric counters, chart strokes, active states |
| Accent Secondary | Neon Violet | `#A855F7` | Scope 1 tags, AI badges, challenges |
| Accent Tertiary | Holographic Blue | `#397BFF` | Scope 2 tags, transport routes, rankings |
| Warning / Alerts | Amber Alerts | `#FFB547` | Anomaly spikes, fuel consumption, limits |
| Supplementary | Soft Magenta | `#F472D0` | Water consumption, festival events |

- **Zero Green Compliance**: Confirmed 0 instances of `#42E695`, `#20D6C7`, `emerald`, `green`, `ecogreen`, or `leaf` tokens across the frontend.
- **5-Layer Ambient Background**: Dynamic holographic grid, shifting aurora gradients, ambient glow orbs, and role-specific particle motion (Individual auroras, Organization transit grids, Campus constellation networks).

---

## 4. Accurate Carbon Calculation Engine

Core calculation formula:
$$\text{Emissions (kg)} = \text{Activity Quantity} \times \text{Traceable Emission Factor} \times \text{Unit Conversion}$$

Every factor records whether its gas basis is **CO2** or **CO2e**, along with
its region, applicable period, publication/version, methodology, and
classification. Electricity uses the CEA Version 22.0 fiscal-year records;
FY 2026-27 uses the latest published factor only as an explicitly labelled
proxy until a new CEA record is available.

### Traceable Reference Emission Factors

| Category | Sub-type | Factor | Unit | Authority / Source |
|---|---|---|---|---|
| Electricity | India National Grid FY 2024-25 | `0.7100` | $\text{kg CO}_2\text{/kWh}$ | CEA Baseline Database v22.0, Table S |
| Electricity | India National Grid FY 2025-26 | `0.6750` | $\text{kg CO}_2\text{/kWh}$ | CEA Baseline Database v22.0, Table S |
| Transport | Passenger Car (Petrol) | `0.1700` | $\text{kg CO}_2\text{e/vehicle-km}$ | DEFRA 2024; exact applicability requires verification |
| Transport | 2-Wheeler Motorcycle | `0.0450` | $\text{kg CO}_2\text{e/vehicle-km}$ | ARAI / DEFRA; exact applicability requires verification |
| Transport | Transit Bus | `0.0890` | $\text{kg CO}_2\text{e/passenger-km}$ | UK DEFRA / BEIS Conversion Factors 2024 |
| Transport | Metro Rail | `0.0350` | $\text{kg CO}_2\text{e/passenger-km}$ | UK DEFRA / BEIS Conversion Factors 2024 |
| Transport | Active Travel (Walk/Bike)| `0.0000` | $\text{kg CO}_2\text{e/km}$ | Zero direct emissions |
| Fuel | Petrol (Gasoline) | `2.3100` | $\text{kg CO}_2\text{e/L}$ | US EPA Emission Factors for GHG Inventories |
| Fuel | Diesel Fuel | `2.6800` | $\text{kg CO}_2\text{e/L}$ | US EPA Emission Factors for GHG Inventories |
| Fuel | Compressed Natural Gas | `2.7500` | $\text{kg CO}_2\text{e/kg}$ | US EPA Emission Factors for GHG Inventories |
| Fuel | Liquefied Petroleum Gas | `2.9800` | $\text{kg CO}_2\text{e/kg}$ | US EPA Emission Factors for GHG Inventories |
| Waste | Organic Food Waste | `0.6250` | $\text{kg CO}_2\text{e/kg}$ | EPA WARM & IPCC Methane Avoidance Model |
| Waste | E-Waste | `18.5000` | $\text{kg CO}_2\text{e/kg}$ | Global E-waste Monitor (ITU / UNITAR) |
| Water | Municipal Water Supply | `0.000344`| $\text{kg CO}_2\text{e/L}$ | UK DEFRA Water Supply & Treatment Factors |

### GPS Haversine Distance Equation
$$d = 2R \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)}\right)$$
Filtered with GPS accuracy threshold $\le 50\text{ m}$ and speed sanity bound $< 300\text{ km/h}$.

---

## 5. API Endpoints Catalog

### Authentication & Workspace
- `POST /api/auth/register` — Create account (`individual`, `college`, `organization`).
- `POST /api/auth/login` — Authenticate and issue secure session.
- `GET /api/auth/session` — Retrieve active principal and workspace onboarding status.
- `PUT /api/workspace` — Configure workspace profile, monthly targets, and onboarding.

### Verified Activities & Carbon Footprint
- `GET /api/dashboard?period=YYYY-MM` — Core dashboard metrics, category mix, and time-series trends.
- `GET /api/activities?period=YYYY-MM` — List verified activities with formula traces.
- `POST /api/activities` — Calculate and log verified activity.
- `DELETE /api/activities/{id}` — Remove activity record.
- `GET /api/reports.csv?period=YYYY-MM` — Export full carbon ledger to CSV.

### GPS Assisted Trips
- `POST /api/trips/start` — Initiate opt-in trip session with chosen mode.
- `POST /api/trips/{id}/points` — Batch stream GPS sample coordinates with accuracy filtering.
- `POST /api/trips/{id}/stop` — Conclude trip, compute Haversine distance, and auto-log to activity ledger.
- `GET /api/trips` — Fetch historical GPS trips.

### Organization & Multi-Site Operations
- `GET /api/facilities` — List organization facilities and buildings.
- `POST /api/facilities` — Register new building, plant, or warehouse.
- `GET /api/organization/scopes?period=YYYY-MM` — Scope 1, 2, 3 GHG Protocol breakdown.
- `GET /api/organization/advisor?period=YYYY-MM` — Algorithmic decarbonization ranking.
- `POST /api/organization/bulk-import` — Batch ingest utility records.

### College / Campus Sustainability
- `GET /api/college/food-waste` — Fetch canteen food waste records.
- `POST /api/college/food-waste` — Log food waste and compute composting methane avoidance.
- `GET /api/college/buses` — Campus shuttle routes, schedules, and capacity.
- `GET /api/college/events` — Past campus event carbon evaluations.
- `POST /api/college/events` — Evaluate fest/symposium carbon footprint.
- `GET /api/college/challenges` — Active campus green challenges.
- `POST /api/college/challenges/{id}/join` — Student participation and point award.
- `GET /api/college/leaderboard` — Hostel and department impact standings.

### Explainable AI & Intelligence
- `GET /api/explainable-ai?period=YYYY-MM` — Complete XAI synthesis: narrative briefing, dominant contributor, period trend, scenario-based recommendations, and calculation traces.

### Utility Bill OCR
- `POST /api/electricity/analyze-bill` — Extract units (kWh) and billing period ($YYYY-MM$) from PDF / image bills.
- `POST /api/electricity/calculate` — Confirm extraction and commit to activity ledger.

### IoT Hardware Telemetry
- `POST /api/iot/readings` — Live ESP32 telemetry ingestion endpoint.
- `GET /api/iot/latest` — Real-time telemetry, voltage, power, and device health status.
- `POST /api/iot/simulate` — Demo simulation of active microcontroller telemetry.

---

## 6. Implementation Status: Real vs. Simulated

| Platform Capability | Implemented Status | Verification Method |
|---|---|---|
| **Carbon Calculation Engine** | **100% Production** | Automated pytest suite (49/49 passed), traceable factor citations |
| **Explainable AI (XAI)** | **100% Production** | Deterministic mathematical proofs, formula verification |
| **GPS Distance Filtering** | **100% Production** | Haversine algorithm, accuracy filtering ($\le 50\text{m}$), outlier rejection |
| **Scope 1, 2, 3 GHG Classification** | **100% Production** | Automated category-to-scope rule mapping |
| **Canteen Food Waste & Composting** | **100% Production** | Real-time calculation with IPCC methane avoidance factors |
| **Campus Event Carbon Evaluator** | **100% Production** | Mathematical multi-vector emissions evaluation |
| **Green Challenges & Leaderboard** | **100% Production** | Multi-table relational tracking and impact point allocation |
| **Utility Bill OCR** | **Production Hybrid** | PyMuPDF text stream extraction + portable Tesseract OCR fallback |
| **ESP32 IoT Ingestion** | **Production Hybrid** | Live `POST /api/iot/readings` accepts physical hardware; interactive simulation button provided for hackathon demonstration without live sensors |

---

## 7. Running the Platform Locally

### Prerequisites
- Python 3.10+ (tested on Python 3.11.9)
- Node.js 20+ and npm

### 1. Backend Server Setup
From the `nexsafetech-t3-15/backend` directory:
```powershell
# Install requirements
python -m pip install -r requirements.txt

# Start FastAPI backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
API documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
Health check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health).

### 2. Frontend Application Setup
From the `nexsafetech-t3-15/frontend` directory:
```powershell
# Install dependencies
npm install

# Start Vite development server
npm run dev
```
Open browser at [http://localhost:5173](http://localhost:5173).

### 3. Automated Test Verification
Run the backend test suite:
```powershell
cd nexsafetech-t3-15
python -m pytest backend/tests -v
```
Result: **49 passed in 46.62s**.

Run the frontend production build:
```powershell
cd nexsafetech-t3-15/frontend
npm run build
```
Result: **0 errors, built in 1m 11s**.
