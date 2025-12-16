import asyncio
import io
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional

import streamlit as st

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None  # type: ignore


st.set_page_config(page_title="Contract Comparison Tool", layout="wide")


def read_pdf_bytes(data: bytes) -> str:
    if PdfReader is None:
        raise RuntimeError(
            "PyPDF2 is required to extract text from PDFs. "
            "Install it with: pip install PyPDF2"
        )
    pdf_reader = PdfReader(io.BytesIO(data))
    pages = []
    for page in pdf_reader.pages:
        text = page.extract_text() or ""
        pages.append(text.strip())
    return "\n\n".join(pages).strip()


def load_sample_pdf(path: str) -> Tuple[str, str]:
    with open(path, "rb") as fh:
        data = fh.read()
    return os.path.basename(path), read_pdf_bytes(data)


def extract_systems_from_contract(
    client: OpenAI, contract_text: str, contract_version: str, model: str, api_key: str
) -> List[Dict]:
    """Extract systems from a single contract using parallel processing."""
    if OpenAI is None:
        raise RuntimeError(
            "openai package is required. Install it with: pip install openai>=1.0.0"
        )

    schema = {
        "name": "systems_extraction",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "systems": {
                    "type": "array",
                    "description": f"List of all systems extracted from {contract_version} contract",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["System Name"],
                        "properties": {
                            "System Name": {"type": "string"},
                            "Amount": {"type": "string"},
                            "Service": {"type": "string"},
                            "Database": {"type": "string"},
                            "Tier-Name": {"type": "string"},
                            "Tier Type": {"type": "string"},
                            "RAM": {"type": "string"},
                            "No. of add HANA nodes": {"type": "string"},
                            "No. of Standby nodes": {"type": "string"},
                            "Storage Information": {"type": "string"},
                            "OS": {"type": "string"},
                            "SLA": {"type": "string"},
                            "DR": {"type": "string"},
                            "Add HW for DR": {"type": "string"},
                            "Pacemaker Included": {"type": "string"},
                            "Phase": {"type": "string"},
                            "Server": {"type": "string"},
                        },
                    },
                },
            },
            "required": ["systems"],
        },
    }

    system_prompt = (
        "You are a contracts analyst specializing in system configuration extraction. "
        f"Extract all systems and their configurations from the {contract_version} contract document. "
        "Be precise and reference concrete contract evidence."
    )

    user_prompt = (
        f"Extract all systems from the following {contract_version} contract.\n\n"
        f"Contract Text:\n"
        f"-----\n"
        f"{contract_text}\n"
        f"-----\n\n"
        "For each system found, extract the following fields: System Name (required), "
        "Amount, Service, Database, Tier-Name, Tier Type, RAM, No. of add HANA nodes, "
        "No. of Standby nodes, Storage Information, OS, SLA, DR, Add HW for DR, "
        "Pacemaker Included, Phase, Server. "
        "If a field is not found, use 'N/A' or 'Not specified'."
    )

    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        max_tokens=16000,
        response_format={"type": "json_schema", "json_schema": schema},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    if not response.choices or not response.choices[0].message.content:
        raise RuntimeError(f"Received empty response from OpenAI for {contract_version}.")

    text = response.choices[0].message.content
    
    try:
        result = json.loads(text)
        return result.get("systems", [])
    except json.JSONDecodeError as e:
        raise RuntimeError(f"JSON parsing error for {contract_version}: {str(e)}") from e


def compare_system_pair(
    client: OpenAI,
    system_a: Dict,
    system_b: Dict,
    model: str,
) -> Dict:
    """Compare a single system pair using an agent."""
    schema = {
        "name": "system_comparison",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["system_name", "status"],
            "properties": {
                "system_name": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["matched", "missing_in_b", "new_in_b"],
                },
                "config_a": {
                    "anyOf": [{"type": "object"}, {"type": "null"}],
                },
                "config_b": {
                    "anyOf": [{"type": "object"}, {"type": "null"}],
                },
                "field_differences": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["field_name", "value_a", "value_b", "analysis"],
                        "properties": {
                            "field_name": {"type": "string"},
                            "value_a": {"type": "string"},
                            "value_b": {"type": "string"},
                            "analysis": {"type": "string"},
                        },
                    },
                },
                "system_analysis": {"type": "string"},
            },
        },
    }

    system_prompt = (
        "You are a contracts analyst specializing in system configuration comparison. "
        "Compare two system configurations and identify differences hierarchically."
    )

    user_prompt = (
        f"Compare the following system configurations:\n\n"
        f"System A:\n{json.dumps(system_a, indent=2)}\n\n"
        f"System B:\n{json.dumps(system_b, indent=2)}\n\n"
        "Compare all fields hierarchically: Amount, Service, Database, Tier-Name, Tier Type, "
        "RAM, No. of add HANA nodes, No. of Standby nodes, Storage Information, OS, SLA, "
        "DR, Add HW for DR, Pacemaker Included, Phase, Server.\n\n"
        "For each field that differs, provide detailed analysis explaining what changed, "
        "why, and the impact. Set status to 'matched' if systems match, otherwise indicate "
        "which system is missing."
    )

    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        max_tokens=8000,
        response_format={"type": "json_schema", "json_schema": schema},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    if not response.choices or not response.choices[0].message.content:
        raise RuntimeError("Received empty response from OpenAI for system comparison.")

    text = response.choices[0].message.content
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"JSON parsing error for system comparison: {str(e)}") from e


def run_parallel_analysis(
    api_key: str, contract_a: str, contract_b: str, *, model: str, max_workers: int = 5
) -> Dict:
    """Run parallel analysis using agents for system extraction and comparison."""
    if OpenAI is None:
        raise RuntimeError(
            "openai package is required. Install it with: pip install openai>=1.0.0"
        )

    client = OpenAI(api_key=api_key)

    # Phase 1: Extract systems from both contracts in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(
            extract_systems_from_contract, client, contract_a, "Version A", model, api_key
        )
        future_b = executor.submit(
            extract_systems_from_contract, client, contract_b, "Version B", model, api_key
        )
        
        systems_config_a = future_a.result()
        systems_config_b = future_b.result()

    # Phase 2: Match systems and prepare comparison tasks
    systems_comparison = []
    
    # Create a map of systems by name for quick lookup
    systems_b_map = {sys.get("System Name", ""): sys for sys in systems_config_b}
    systems_a_map = {sys.get("System Name", ""): sys for sys in systems_config_a}
    
    # Prepare comparison tasks
    comparison_tasks = []
    
    # For systems in A: find matches in B
    for system_a in systems_config_a:
        system_name = system_a.get("System Name", "")
        system_b = systems_b_map.get(system_name)
        
        if system_b:
            # Both exist - compare them
            comparison_tasks.append(("matched", system_a, system_b))
        else:
            # System A exists but not in B
            comparison_tasks.append(("missing_in_b", system_a, None))
    
    # For systems in B that don't exist in A
    for system_b in systems_config_b:
        system_name = system_b.get("System Name", "")
        if system_name not in systems_a_map:
            comparison_tasks.append(("new_in_b", None, system_b))
    
    # Phase 3: Compare systems in parallel using agents
    def process_comparison_task(task):
        status, system_a, system_b = task
        
        if status == "matched" and system_a and system_b:
            # Use agent to compare
            try:
                result = compare_system_pair(client, system_a, system_b, model)
                result["status"] = "matched"
                return result
            except Exception as e:
                # Fallback: manual comparison
                return {
                    "system_name": system_a.get("System Name", ""),
                    "status": "matched",
                    "config_a": system_a,
                    "config_b": system_b,
                    "field_differences": _manual_field_comparison(system_a, system_b),
                    "system_analysis": f"Comparison completed with fallback method. Error: {str(e)}",
                }
        elif status == "missing_in_b" and system_a:
            return {
                "system_name": system_a.get("System Name", ""),
                "status": "missing_in_b",
                "config_a": system_a,
                "config_b": None,
                "field_differences": [],
                "system_analysis": f"System '{system_a.get('System Name', '')}' exists in Version A but is missing in Version B.",
            }
        elif status == "new_in_b" and system_b:
            return {
                "system_name": system_b.get("System Name", ""),
                "status": "new_in_b",
                "config_a": None,
                "config_b": system_b,
                "field_differences": [],
                "system_analysis": f"System '{system_b.get('System Name', '')}' is new in Version B (not present in Version A).",
            }
        return None
    
    # Execute comparisons in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_comparison_task, task) for task in comparison_tasks]
        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    systems_comparison.append(result)
            except Exception as e:
                st.warning(f"Error processing system comparison: {str(e)}")
    
    return {
        "systems_config_a": systems_config_a,
        "systems_config_b": systems_config_b,
        "systems_comparison": systems_comparison,
    }


def _manual_field_comparison(system_a: Dict, system_b: Dict) -> List[Dict]:
    """Fallback manual field comparison if agent comparison fails."""
    field_order = [
        "Amount", "Service", "Database", "Tier-Name", "Tier Type", "RAM",
        "No. of add HANA nodes", "No. of Standby nodes", "Storage Information",
        "OS", "SLA", "DR", "Add HW for DR", "Pacemaker Included", "Phase", "Server"
    ]
    
    differences = []
    for field in field_order:
        value_a = system_a.get(field, "N/A")
        value_b = system_b.get(field, "N/A")
        
        if value_a != value_b:
            differences.append({
                "field_name": field,
                "value_a": str(value_a),
                "value_b": str(value_b),
                "analysis": f"Field '{field}' changed from '{value_a}' to '{value_b}'.",
            })
    
    return differences


# Copy the rest of the main function from the original file
def main() -> None:
    st.title("Contract Comparison Tool (Parallel Processing)")
    st.write(
        "Upload two contract PDFs or choose from the sample files to compare changes "
        "and extract infrastructure components using parallel processing with OpenAI API."
    )

    with st.sidebar:
        st.header("Configuration")
        api_key = st.text_input("OpenAI API Key", type="password")
        model = st.selectbox(
            "Model",
            options=[
                "gpt-4.1-mini",
                "gpt-4o-mini",
                "gpt-4.1",
                "o4-mini",
            ],
            index=0,
            help="Choose a model with JSON output support.",
        )
        max_workers = st.slider(
            "Max Parallel Workers",
            min_value=2,
            max_value=10,
            value=5,
            help="Number of parallel agents for system comparisons",
        )
        st.caption(
            "API key is used only for this session and is not stored.\n"
            "Need an account? Visit https://platform.openai.com/"
        )

    sample_files = sorted(
        [
            f
            for f in os.listdir(".")
            if f.lower().endswith(".pdf") and "contract" in f.lower()
        ]
    )

    mode = st.radio(
        "Select Input Method",
        options=[
            "Upload PDF files",
            "Use sample files from project directory",
        ],
    )

    contract_a_name = contract_b_name = ""
    contract_a_text = contract_b_text = ""

    if mode == "Upload PDF files":
        col_a, col_b = st.columns(2)
        with col_a:
            uploaded_a = st.file_uploader("Version A (PDF)", type=["pdf"], key="pdf_a")
        with col_b:
            uploaded_b = st.file_uploader("Version B (PDF)", type=["pdf"], key="pdf_b")

        if uploaded_a is not None:
            try:
                contract_a_name = uploaded_a.name
                contract_a_text = read_pdf_bytes(uploaded_a.read())
            except Exception as err:  # pylint: disable=broad-except
                st.error(f"Failed to read Version A: {err}")
        if uploaded_b is not None:
            try:
                contract_b_name = uploaded_b.name
                contract_b_text = read_pdf_bytes(uploaded_b.read())
            except Exception as err:  # pylint: disable=broad-except
                st.error(f"Failed to read Version B: {err}")
    else:
        if not sample_files:
            st.warning(
                "No sample contract PDFs found in the project directory. "
                "Please upload your own files instead."
            )
        else:
            col_a, col_b = st.columns(2)
            with col_a:
                sample_a = st.selectbox(
                    "Version A Sample", options=sample_files, key="sample_a"
                )
            with col_b:
                sample_b = st.selectbox(
                    "Version B Sample", options=sample_files, key="sample_b"
                )
            if sample_a and sample_b:
                try:
                    contract_a_name, contract_a_text = load_sample_pdf(sample_a)
                except Exception as err:  # pylint: disable=broad-except
                    st.error(f"Failed to load Version A sample: {err}")
                try:
                    contract_b_name, contract_b_text = load_sample_pdf(sample_b)
                except Exception as err:  # pylint: disable=broad-except
                    st.error(f"Failed to load Version B sample: {err}")

    compare_disabled = not (
        api_key
        and contract_a_text
        and contract_b_text
        and contract_a_name
        and contract_b_name
    )

    if st.button("Compare Contracts (Parallel)", type="primary", disabled=compare_disabled):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with st.spinner("Analyzing contracts with parallel processing..."):
            try:
                status_text.text("Phase 1: Extracting systems from both contracts in parallel...")
                progress_bar.progress(10)
                
                result = run_parallel_analysis(
                    api_key=api_key,
                    contract_a=contract_a_text,
                    contract_b=contract_b_text,
                    model=model,
                    max_workers=max_workers,
                )
                
                progress_bar.progress(100)
                status_text.text("Analysis complete!")
                
            except Exception as err:  # pylint: disable=broad-except
                st.error(f"Parallel analysis failed: {err}")
                import traceback
                st.code(traceback.format_exc())
                return

        st.success("Analysis complete!")
        progress_bar.empty()
        status_text.empty()

        # Display results
        systems_config_a = result.get("systems_config_a", [])
        systems_config_b = result.get("systems_config_b", [])
        systems_comparison = result.get("systems_comparison", [])
        
        if systems_config_a or systems_config_b or systems_comparison:
            st.header("🔍 S/4 HANA Systems Comparison")
            
            # Filter systems to only include those with 'S/4 HANA' in the name
            s4_hana_systems = [
                comp for comp in systems_comparison
                if comp.get("system_name", "").upper().find("S/4 HANA") != -1
            ]
            
            if not s4_hana_systems:
                st.warning("No systems found with 'S/4 HANA' in the name.")
            else:
                st.info(f"Found {len(s4_hana_systems)} system(s) containing 'S/4 HANA'")
                
                # Display each S4 HANA system side by side
                for idx, system_comp in enumerate(s4_hana_systems, 1):
                    system_name = system_comp.get("system_name", "Unknown System")
                    config_a = system_comp.get("config_a")
                    config_b = system_comp.get("config_b")
                    
                    st.subheader(f"System {idx}: {system_name}")
                    
                    # Create side-by-side columns
                    col_a, col_b = st.columns(2)
                    
                    # Define all fields to display
                    fields_to_display = [
                        "System Name", "Amount", "Service", "Database", "Tier-Name", 
                        "Tier Type", "RAM", "No. of add HANA nodes", "No. of Standby nodes", 
                        "Storage Information", "OS", "SLA", "DR", "Add HW for DR", 
                        "Pacemaker Included", "Phase", "Server"
                    ]
                    
                    with col_a:
                        st.markdown("### Version A")
                        if config_a:
                            for field in fields_to_display:
                                value = config_a.get(field, "N/A")
                                if value and str(value).strip() and str(value) != "N/A":
                                    st.markdown(f"**{field}:** {value}")
                                else:
                                    st.markdown(f"**{field}:** *Not specified*")
                        else:
                            st.warning("System not found in Version A")
                    
                    with col_b:
                        st.markdown("### Version B")
                        if config_b:
                            for field in fields_to_display:
                                value = config_b.get(field, "N/A")
                                if value and str(value).strip() and str(value) != "N/A":
                                    st.markdown(f"**{field}:** {value}")
                                else:
                                    st.markdown(f"**{field}:** *Not specified*")
                        else:
                            st.warning("System not found in Version B")
                    
                    # Show field differences if available
                    field_differences = system_comp.get("field_differences", [])
                    if field_differences:
                        with st.expander(f"View Differences for {system_name}"):
                            for diff in field_differences:
                                st.markdown(f"**{diff.get('field_name', 'Unknown')}:**")
                                st.markdown(f"- Version A: {diff.get('value_a', 'N/A')}")
                                st.markdown(f"- Version B: {diff.get('value_b', 'N/A')}")
                                if diff.get('analysis'):
                                    st.info(diff.get('analysis'))
                    
                    # Show system analysis if available
                    system_analysis = system_comp.get("system_analysis", "")
                    if system_analysis:
                        st.info(f"**Analysis:** {system_analysis}")
                    
                    st.divider()
        else:
            st.warning("No systems data found in the analysis results.")


if __name__ == "__main__":
    main()




