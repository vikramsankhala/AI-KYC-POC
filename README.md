# Contract Comparison Tool

A Streamlit application for comparing contract PDFs and extracting infrastructure components, with special focus on S/4 HANA systems.

## Features

- **Parallel Processing**: Uses parallel processing with OpenAI API for faster contract analysis
- **S/4 HANA Filtering**: Automatically filters and displays only systems containing 'S/4 HANA' in the name
- **Side-by-Side Comparison**: Displays contract versions side by side for easy comparison
- **System Extraction**: Extracts detailed system configurations including:
  - System Name, Amount, Service, Database
  - Tier-Name, Tier Type, RAM
  - HANA nodes, Standby nodes
  - Storage Information, OS, SLA, DR
  - And more...

## Requirements

- Python 3.8+
- OpenAI API key
- Streamlit
- PyPDF2
- OpenAI Python package

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Local Development

```bash
streamlit run streamlit_app_parallel.py
```

### Streamlit Community Cloud Deployment

1. Push this repository to GitHub
2. Go to [Streamlit Community Cloud](https://share.streamlit.io/)
3. Click "New app"
4. Connect your GitHub repository
5. Set the main file path to: `streamlit_app_parallel.py`
6. Deploy!

## Configuration

- Enter your OpenAI API key in the sidebar
- Select the OpenAI model to use
- Adjust the number of parallel workers as needed

## Notes

- The app requires an OpenAI API key to function
- API keys are not stored and are only used for the current session
- Large PDF files may take longer to process

