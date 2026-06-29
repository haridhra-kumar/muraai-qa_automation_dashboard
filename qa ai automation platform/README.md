# QA AI Automation Platform

A production-quality QA analytics and AI assistant platform built with Streamlit, Pandas, Plotly, and Groq (Llama 3). Designed to automate weekly QA reporting, generate executive dashboards, and provide natural language querying over your Zoho Bug Tracker exports.

---

## Features

- **Executive Dashboard** — KPI cards, status at a glance, one-click AI summary
- **Analytics** — Tabbed deep-dive: Overview, Projects, Severity, Phase, Modules, Timeline, People, Effort
- **Weekly Reports** — Consulting-style reports with PDF and Markdown export
- **AI Assistant** — ChatGPT-style interface with streaming, conversation memory, and automatic chart generation
- **Dataset Capability Engine** — Automatically detects available columns and shows only supported features
- **Dynamic UI** — Never shows empty charts, placeholder boxes, or fake values
- **Future-ready** — Architecture is pre-wired for Zoho Projects API integration

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| UI Framework | Streamlit |
| Data Processing | Pandas, OpenPyXL |
| Visualizations | Plotly |
| AI Backend | Groq API (Llama 3.3 70B) |
| PDF Export | ReportLab |
| Config | python-dotenv |

---

## Architecture

```
qa_platform/
├── app.py                    # Entry point: sidebar nav, project filter, session state
├── .env                      # GROQ_API_KEY (create this yourself)
├── requirements.txt
├── README.md
├── data/
│   └── latest_qa.xlsx        # Drop your weekly export here for auto-load
│
├── core/
│   ├── data_provider.py      # Data abstraction layer (Excel ↔ future Zoho API)
│   ├── capabilities.py       # Dataset Capability Engine
│   └── context_builder.py    # Builds structured AI context; calculates all KPIs
│
├── pages/
│   ├── dashboard.py          # 🏠 Executive overview
│   ├── analytics.py          # 📊 Tabbed visualizations
│   ├── reports.py            # 📄 Report generator + exports
│   ├── ai_assistant.py       # 🤖 ChatGPT-style AI interface
│   └── settings.py           # ⚙ Upload, validate, API config
│
└── utils/
    ├── charts.py             # All Plotly chart factories (return Figure | None)
    ├── kpis.py               # Pure KPI calculation functions
    └── pdf_export.py         # ReportLab PDF generation
```

---

## How the Data Provider Works

`core/data_provider.py` is the **only** file that knows where data comes from.

```
Dashboard → Analytics → Reports → AI Assistant
                ↓
          Data Provider
                ↓
       Excel  OR  Zoho API (future)
```

All pages call `get_provider().get_dataframe()`. The rest of the app never touches file I/O.

**To add Zoho API later:** implement `_load_from_zoho_api()` in `data_provider.py`. Nothing else changes.

---

## Dataset Capability Engine

When a dataset loads, `core/capabilities.py` inspects it **once** and produces a `Capabilities` object:

```python
caps.supports_status         # True/False
caps.supports_severity       # True/False
caps.supports_phase          # True/False
caps.supports_aging          # True if both created_time + closed_time exist
caps.has_multi_project       # True if more than one project
# ... and 20+ more flags
```

Every page reads from `caps`. No page ever checks `if "column" in df.columns`.

If a feature is unsupported, its UI components are simply not rendered.

---

## Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd qa_platform
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Linux / Mac
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Groq API

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your Groq API key:

```
GROQ_API_KEY=gsk_your_actual_key_here
```

Get a free key at [console.groq.com](https://console.groq.com).

---

## Running the Application

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## Uploading Weekly Excel Files

**Option 1 — Auto-load (recommended):**
Place your export at `data/latest_qa.xlsx`. The app loads it automatically on startup.

**Option 2 — Manual upload:**
Go to **⚙ Settings → Upload Dataset** and upload any `.xlsx` file.

The app normalizes column names automatically, so minor variations in export format are handled.

---

## Supported Dataset Columns

The platform recognizes these columns (case-insensitive, with common aliases):

| Column | Canonical Name | Required |
|--------|---------------|----------|
| Issue Name / Bug Name | `issue_name` | Recommended |
| Issue Prefix | `issue_prefix` | Optional |
| Project Name | `project_name` | Recommended |
| Reporter | `reporter` | Optional |
| Created Time / Created Date | `created_time` | Optional |
| Last Closed Time / Closed Time | `closed_time` | Optional |
| Status | `status` | Recommended |
| Severity | `severity` | Recommended |
| Module | `module` | Optional |
| Classification | `classification` | Optional |
| Resolution | `resolution` | Optional |
| Assignee | `assignee` | Optional |
| Tags | `tags` | Optional |
| Release Milestone | `release_milestone` | Optional |
| Affected Milestone | `affected_milestone` | Optional |
| Escalation Level | `escalation_level` | Optional |
| Billable Hours | `billable_hours` | Optional |
| Non Billable Hours | `non_billable_hours` | Optional |
| Total Log Hours | `total_log_hours` | Optional |
| Phase | `phase` | Optional |

**The app works with any subset of these columns.** Missing columns simply remove the related features from the UI.

---

## Dynamic Dataset Adaptation

| Condition | Behaviour |
|-----------|-----------|
| `status` column present | Show Status KPIs, Status charts, Status report section |
| `status` column missing | Remove all status-related UI |
| `phase` column present | Enable Phase tab, Phase report, Phase AI analysis |
| `phase` column missing | Remove all phase-related UI silently |
| `created_time` + `closed_time` both present | Enable Issue Aging analysis |
| Only one date column | Disable aging, keep timeline trend |
| `total_log_hours` present | Enable Effort tab and Effort report section |
| Single project in dataset | Remove multi-project comparison charts |

---

## Generating Reports

1. Select a project filter in the sidebar (or keep "All Projects")
2. Go to **📄 Weekly Reports**
3. Click **Generate Report**
4. Download as **PDF** or **Markdown**

Reports automatically include only sections supported by your dataset.

---

## Using the AI Assistant

1. Go to **🤖 AI Assistant**
2. Select a project filter if needed
3. Click a **suggested prompt** or type your own question
4. The assistant streams its response and **automatically generates a chart** when relevant

Example questions:
- "Which project has the most critical issues?"
- "Give me an executive summary for this week"
- "Compare severity distribution across all projects"
- "What are the top defect hotspot modules?"
- "Who has the highest unresolved workload?"

The AI **never** receives raw data rows. Python computes all KPIs first; the AI receives a structured summary.

---

## Project Navigation

| Page | Purpose |
|------|---------|
| 🏠 Dashboard | Executive overview — KPIs, quick charts, AI summary |
| 📊 Analytics | Full tabbed visualization suite |
| 📄 Weekly Reports | Generate + export consulting-style reports |
| 🤖 AI Assistant | Natural language Q&A with streaming + auto charts |
| ⚙ Settings | Upload, validate, API config, capability inspection |

The **Project Filter** in the sidebar applies to all pages simultaneously.

---

## Future Zoho API Integration

The architecture is already prepared. To activate:

1. Open `core/data_provider.py`
2. Implement `_load_from_zoho_api()` — fetch issues from the Zoho Projects REST API and return a DataFrame with canonical column names
3. In `Settings`, fill in the API URL and credentials
4. Call `provider.load_from_api()` instead of `provider.load_excel()`

**Zero changes required** in any page, chart, report, or AI module.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: groq` | Run `pip install groq` |
| `GROQ_API_KEY not set` | Create `.env` with your key |
| Charts not showing | Check ⚙ Settings → Dataset Capabilities to see what's detected |
| Excel loads but all caps are False | Verify column names match the supported list above |
| PDF export fails | Run `pip install reportlab` |
| App won't start | Ensure you're in the virtual env: `source venv/bin/activate` |

---

## Future Improvements

- Zoho Projects REST API integration (architecture already in place)
- Multi-file comparison (week-over-week trend)
- Email report delivery via SMTP
- Role-based access (manager vs developer view)
- Custom KPI threshold alerts
- Scheduled auto-refresh from API
- Export charts as PNG in PDF report
- Persistent conversation history across sessions

---

## License

Internal use — QA AI Automation Platform · Built as part of internship deliverable.
