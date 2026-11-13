# AstroGuard

**Spacecraft Telemetry Intelligence & Anomaly Detection Platform**

AstroGuard is an independent research and portfolio prototype for processing historical spacecraft telemetry, detecting unusual sensor behaviour, and supporting anomaly investigation.

It is not a NASA operational system and must not be used for flight-safety decisions.

## Current capabilities

- Historical telemetry acquisition and preprocessing.
- SMAP and MSL telemetry dataset integration.
- Multi-channel telemetry handling and temporal feature engineering.
- Statistical and supervised/unsupervised anomaly-detection components.
- Experiment tracking, evaluation and model-artifact registry foundations.
- FastAPI backend and inference interfaces.
- SQLAlchemy and Alembic database foundation.
- Versioned streaming event contracts, topic management, producer and consumer abstractions.
- Native C++20 telemetry-processing core and unit tests.

These capabilities represent a research and engineering prototype. Their presence does not establish production readiness, operational reliability, or validated spacecraft anomaly-detection performance.

## Technology

| Area | Technology |
|---|---|
| Backend API | Python 3.12, FastAPI, Uvicorn |
| Data processing | NumPy |
| ML | scikit-learn, SciPy, joblib |
| Validation and contracts | Pydantic |
| Database foundation | SQLAlchemy, Alembic |
| Streaming foundation | Python asynchronous interfaces and bounded in-memory broker |
| Native processing | C++20, CMake |
| Testing | pytest, httpx, CTest |

PostgreSQL, distributed streaming infrastructure, frontend application development, and cloud deployment are future integration areas rather than capabilities verified by this repository snapshot.

## Repository structure

```text
AstroGuard/
├── backend/
│   ├── astroguard_api/
│   │   ├── database/
│   │   ├── mission_data/
│   │   ├── mission_sources/
│   │   ├── ml_engine/
│   │   ├── streaming/
│   │   └── telemetry/
│   └── tests/
├── native/
│   ├── include/
│   ├── src/
│   └── tests/
├── docs/
│   ├── architecture/
│   ├── decisions/
│   └── testing/
├── data/
├── artifacts/
├── README.md
└── pyproject.toml
```

Local datasets, generated artifacts, databases, credentials, virtual environments, and build outputs are excluded from version control according to `.gitignore`.

## Requirements

- Windows, Linux, or macOS.
- Python 3.12.
- CMake 3.20 or newer for the native component.
- A C++20-compatible compiler.
- Git.

## Backend setup

From the repository root:

```powershell
py -3.12 -m venv .venv

.\.venv\Scripts\python.exe -m pip install --upgrade pip

.\.venv\Scripts\python.exe -m pip install -e ".[dev,database,ml]"
```

The extras install:

- `dev`: pytest and HTTP client testing dependencies.
- `database`: SQLAlchemy and Alembic.
- `ml`: scikit-learn, SciPy and joblib.

NumPy and Pydantic are declared as core dependencies.

## Backend tests

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
```

## Run the API

```powershell
$env:PYTHONPATH = "backend"

.\.venv\Scripts\python.exe -m uvicorn astroguard_api.main:app --app-dir backend --reload
```

## Native C++ build and tests

```powershell
cmake -S native -B build/native -DCMAKE_BUILD_TYPE=Release

cmake --build build/native --config Release --parallel 2

ctest --test-dir build/native -C Release --output-on-failure
```

## Streaming status

The current streaming implementation provides application-level contracts, topic definitions, topic administration abstractions, producer and consumer interfaces, and an in-memory development broker.

The in-memory broker is not Kafka or Redpanda. It does not provide persistent storage, replication, distributed consumer groups, durable offsets, or cross-process delivery.

A successful producer publish result means the configured broker's publish operation returned successfully. It does not establish external broker persistence or replication.

Consumer acknowledgement is currently an in-memory operation. Failed handlers are not acknowledged, but this does not establish durable redelivery or retry guarantees. Retry and dead-letter lifecycle improvements remain separate engineering work.

## Engineering policies

- No notebooks.
- Never commit secrets or local environment files.
- Never modify raw datasets during processing.
- Keep training and test telemetry separate.
- Never use test labels for training or calibration.
- All ML performance claims require reproducible evaluation.
- Historical telemetry replay is not live NASA telemetry.
- No flight-safety or operational-safety claims.
- Every engineering phase requires tests and acceptance evidence.
- Database migrations must be explicitly reviewed and validated.

## Safety and research disclaimer

AstroGuard is an independent research and portfolio project. It is not affiliated with, endorsed by, or operated by NASA. It must not be used for spacecraft control, mission-critical decisions, or flight-safety applications.