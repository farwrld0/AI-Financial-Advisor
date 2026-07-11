# AI Personal Finance Agent

AI Personal Finance Agent is a Streamlit web app that helps users understand their personal finances through a guided questionnaire, a financial health report, an AI chat advisor, and scenario planning tools.

The app is designed as a polished Apple-inspired personal finance dashboard. It collects a user's financial profile, analyzes income, expenses, assets, debt, savings rate, goals, and planned purchases, then uses AI to generate personalized financial guidance.

## Features

- Multi-step financial questionnaire
- Personalized financial health report
- Financial snapshot with income, expenses, savings rate, and net worth
- AI-powered Chat Advisor for personalized finance questions
- Scenario Planner for testing life changes such as salary changes, buying a house, job loss, or major purchases
- Goal and budget visualization
- Profile cache so completed questionnaire data can be reused across Streamlit tabs
- Apple-inspired custom UI built with Streamlit, HTML, and CSS

## Project Structure

```text
.
├── app.py                    # Main Streamlit router and page controller
├── questionnaire.py           # Multi-step questionnaire UI and profile collection
├── report.py                  # Financial report dashboard
├── llm.py                     # AI chat and scenario LLM calls
├── system_prompt_v2.py        # DeepSeek financial analysis prompt logic
├── adapter.py                 # Converts questionnaire data into backend schema
├── questionnaire_schema.py    # Financial profile data models and validation
├── goal_visualization.py      # Goal charts and visualizations
├── cost_of_living.py          # Cost-of-living helper logic
├── requirements.txt           # Python dependencies
├── secrets.toml               # Local secrets file, not for public sharing
└── .streamlit/config.toml     # Streamlit configuration
```

## Requirements

- Python 3.10+
- Streamlit
- pandas
- openai
- plotly
- reportlab

Install dependencies with:

```bash
pip install -r requirements.txt
```

If you are using the existing virtual environment:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the App

From the project directory:

```bash
source .venv/bin/activate
streamlit run app.py
```

Then open:

```text
http://localhost:8501
```

If port `8501` is already in use:

```bash
streamlit run app.py --server.port 8502
```

## API Key Setup

The report and AI advisor features require a DeepSeek-compatible API key.

Add the key to Streamlit secrets or your shell environment:

```toml
# .streamlit/secrets.toml
DEEPSEEK_API_KEY = "your_api_key_here"
```

or:

```bash
export DEEPSEEK_API_KEY="your_api_key_here"
```

Do not commit real API keys to Git.

## Main User Flow

1. Open the app.
2. Complete the Questionnaire.
3. View the Financial Report.
4. Ask personalized questions in Chat Advisor.
5. Use Scenario Planner to test possible future decisions.

Example Chat Advisor questions:

- Should I buy a $500 gadget?
- How much can I spend eating out?
- Am I on track for retirement?
- Can I afford a house?
- Can I travel this summer?

## Data Sync Notes

Streamlit stores `st.session_state` separately for each browser tab. To prevent the Chat Advisor from losing questionnaire data across tabs, the app saves completed questionnaire data to:

```text
.user_profile_cache.json
```

When a new tab opens and session state is empty, the app attempts to restore the latest completed profile from this cache.

This file is local runtime data and should not be committed if it contains personal financial information.

## Development Notes

- `app.py` controls routing between Home, Questionnaire, Report, Chat Advisor, and Scenario Planner.
- `questionnaire.py` owns user input collection and builds the completed profile.
- `report.py` renders the dashboard-style financial report.
- `llm.py` handles AI chat and scenario calls.
- `adapter.py` maps Streamlit session data into structured financial profile models.
- The UI uses custom HTML/CSS heavily, so avoid replacing the Chat Advisor with Streamlit's default chat components unless intentionally redesigning the page.

## Privacy

This app handles sensitive personal financial information. Treat local files such as `secrets.toml` and `.user_profile_cache.json` as private. Do not upload them, commit them, or share them publicly.

## Current Status

The app currently supports the full core workflow:

- Questionnaire completion
- Financial report generation
- Chat Advisor with restored financial profile context
- Scenario Planner analysis

Some export and comparison features may depend on optional modules or future enhancements.
