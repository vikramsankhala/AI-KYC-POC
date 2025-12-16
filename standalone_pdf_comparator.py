import pandas as pd
import re
from datetime import datetime
from difflib import SequenceMatcher
import os
import tkinter as tk
from tkinter import filedialog, messagebox

# Try importing PDF libraries with fallbacks
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("PyPDF2 not available. Please install with: pip install PyPDF2")

def select_file(title="Select PDF File"):
    """Open a GUI file picker to select a PDF file"""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    file_path = filedialog.askopenfilename(
        title=title,
        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
    )
    
    root.destroy()
    return file_path

def show_message(title, message, msg_type="info"):
    """Show a GUI message box"""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    if msg_type == "error":
        messagebox.showerror(title, message)
    elif msg_type == "warning":
        messagebox.showwarning(title, message)
    else:
        messagebox.showinfo(title, message)
    
    root.destroy()

def ask_yes_no(title, message):
    """Show a GUI yes/no dialog"""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    result = messagebox.askyesno(title, message)
    root.destroy()
    return result

def extract_text_from_pdf(pdf_path):
    """Extract text content from PDF file"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error reading PDF: {str(e)}")
        return ""

def extract_contract_info(text, filename):
    """Extract contract information from PDF text"""
    contract_info = {
        'filename': filename,
        'contract_number': '',
        'contract_date': '',
        'effective_date': '',
        'expiration_date': '',
        'contract_value': '',
        'currency': '',
        'party_a': '',
        'party_b': '',
        'contract_type': '',
        'payment_terms': '',
        'additional_data': {}
    }
    
    # Extract basic information using regex patterns
    patterns = {
        'contract_date': r'Date\s+(\d{4}/\d{2}/\d{2})',
        'currency': r'Currency\s+([A-Z]{3})',
        'contract_number': r'Contract\s+(\d+)\s+month',
        'contract_type': r'(SAP\s+[\w\s]+)',
        'party_a': r'Customer\s+([\w\s]+?)(?:\s+Production|$)',
        'version': r'Version:\s+([\w\-\d]+)',
        'delivery_options': r'Delivery Options\s+([\w\s:(),-]+)',
        'country': r'Country\s+([A-Z]+)',
        'dc_location': r'DC\s+([\w\s:()-]+)',
    }
    
    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if field in contract_info:
                contract_info[field] = match.group(1).strip()
            else:
                contract_info['additional_data'][field] = match.group(1).strip()
    
    # Extract customer name (Party A)
    customer_match = re.search(r'Customer\s+([\w\s]+)', text)
    if customer_match:
        contract_info['party_a'] = customer_match.group(1).strip()
    
    # Extract service provider (Party B) - usually SAP
    if 'SAP' in text:
        contract_info['party_b'] = 'SAP'
    
    # Extract contract duration
    duration_match = re.search(r'Contract\s+(\d+)\s+month', text)
    if duration_match:
        contract_info['additional_data']['duration_months'] = duration_match.group(1)
    
    # Extract system information
    systems = re.findall(r'(S/4HANA|SLT|DS|GRC|Cloud Connector)', text)
    if systems:
        contract_info['additional_data']['systems'] = list(set(systems))
    
    # Extract SLA information
    sla_matches = re.findall(r'(\d{2}\.\d{2})%', text)
    if sla_matches:
        contract_info['additional_data']['sla_percentages'] = list(set(sla_matches))
    
    # Extract storage information
    storage_matches = re.findall(r'(\d+)\.\s*\([^)]+\)', text)
    if storage_matches:
        contract_info['additional_data']['storage_amounts'] = storage_matches[:5]
    
    return contract_info

def calculate_similarity(text1, text2):
    """Calculate similarity percentage between two texts"""
    return SequenceMatcher(None, text1, text2).ratio() * 100

def compare_contracts(contract1, contract2):
    """Compare two contracts and identify similarities and differences"""
    comparison = {
        'similarities': {},
        'differences': {},
        'missing_in_contract1': {},
        'missing_in_contract2': {}
    }
    
    # Compare basic fields
    basic_fields = ['contract_number', 'contract_date', 'effective_date', 'expiration_date',
                   'contract_value', 'currency', 'party_a', 'party_b', 'contract_type', 'payment_terms']
    
    for field in basic_fields:
        val1 = contract1.get(field, '')
        val2 = contract2.get(field, '')
        
        if val1 and val2:
            if val1 == val2:
                comparison['similarities'][field] = val1
            else:
                comparison['differences'][field] = {'Contract 1': val1, 'Contract 2': val2}
        elif val1 and not val2:
            comparison['missing_in_contract2'][field] = val1
        elif val2 and not val1:
            comparison['missing_in_contract1'][field] = val2
    
    # Compare additional data
    add1 = contract1.get('additional_data', {})
    add2 = contract2.get('additional_data', {})
    
    all_keys = set(add1.keys()) | set(add2.keys())
    
    for key in all_keys:
        val1 = add1.get(key, '')
        val2 = add2.get(key, '')
        
        if val1 and val2:
            if str(val1) == str(val2):
                comparison['similarities'][f"additional_{key}"] = val1
            else:
                comparison['differences'][f"additional_{key}"] = {'Contract 1': val1, 'Contract 2': val2}
        elif val1 and not val2:
            comparison['missing_in_contract2'][f"additional_{key}"] = val1
        elif val2 and not val1:
            comparison['missing_in_contract1'][f"additional_{key}"] = val2
    
    return comparison

def print_contract_info(contract, title):
    """Print contract information"""
    print(f"\n{'='*50}")
    print(f"{title}: {contract['filename']}")
    print(f"{'='*50}")
    
    for key, value in contract.items():
        if key != 'additional_data' and key != 'filename' and value:
            print(f"{key.replace('_', ' ').title()}: {value}")
    
    if contract['additional_data']:
        print(f"\nAdditional Data:")
        for key, value in contract['additional_data'].items():
            print(f"  {key.replace('_', ' ').title()}: {value}")

def print_comparison_results(comparison, overall_similarity):
    """Print comparison results"""
    print(f"\n{'='*50}")
    print(f"COMPARISON RESULTS")
    print(f"{'='*50}")
    print(f"Overall Text Similarity: {overall_similarity:.1f}%")
    
    # Print similarities
    if comparison['similarities']:
        print(f"\n✅ SIMILARITIES ({len(comparison['similarities'])} found):")
        print("-" * 30)
        for field, value in comparison['similarities'].items():
            print(f"• {field.replace('_', ' ').title()}: {value}")
    
    # Print differences
    if comparison['differences']:
        print(f"\n⚠️ DIFFERENCES ({len(comparison['differences'])} found):")
        print("-" * 30)
        for field, values in comparison['differences'].items():
            print(f"• {field.replace('_', ' ').title()}:")
            print(f"  Contract 1: {values.get('Contract 1', 'N/A')}")
            print(f"  Contract 2: {values.get('Contract 2', 'N/A')}")
    
    # Print missing information
    if comparison['missing_in_contract1']:
        print(f"\n❌ MISSING IN CONTRACT 1 ({len(comparison['missing_in_contract1'])} items):")
        print("-" * 30)
        for field, value in comparison['missing_in_contract1'].items():
            print(f"• {field.replace('_', ' ').title()}: {value}")
    
    if comparison['missing_in_contract2']:
        print(f"\n❌ MISSING IN CONTRACT 2 ({len(comparison['missing_in_contract2'])} items):")
        print("-" * 30)
        for field, value in comparison['missing_in_contract2'].items():
            print(f"• {field.replace('_', ' ').title()}: {value}")

def save_report(contract1, contract2, comparison, overall_similarity, output_file):
    """Save comparison report to file as formatted tables"""
    report = f"""Contract Comparison Report
{'='*80}

OVERVIEW
{'-'*80}
Contract 1 Filename: {contract1['filename']}
Contract 2 Filename: {contract2['filename']}
Overall Text Similarity: {overall_similarity:.1f}%
Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
    
    # Contract Information Table
    report += f"""CONTRACT INFORMATION COMPARISON
{'-'*80}
{'Field':<25} {'Contract 1':<25} {'Contract 2':<25}
{'-'*80}
"""
    
    # Basic contract fields
    basic_fields = ['contract_number', 'contract_date', 'effective_date', 'expiration_date',
                   'contract_value', 'currency', 'party_a', 'party_b', 'contract_type', 'payment_terms']
    
    for field in basic_fields:
        field_name = field.replace('_', ' ').title()
        val1 = contract1.get(field, 'N/A')
        val2 = contract2.get(field, 'N/A')
        report += f"{field_name:<25} {str(val1):<25} {str(val2):<25}\n"
    
    # Additional data comparison
    add1 = contract1.get('additional_data', {})
    add2 = contract2.get('additional_data', {})
    all_keys = sorted(set(add1.keys()) | set(add2.keys()))
    
    if all_keys:
        report += f"\nADDITIONAL DATA COMPARISON\n{'-'*80}\n"
        report += f"{'Field':<25} {'Contract 1':<25} {'Contract 2':<25}\n{'-'*80}\n"
        
        for key in all_keys:
            field_name = key.replace('_', ' ').title()
            val1 = str(add1.get(key, 'N/A'))
            val2 = str(add2.get(key, 'N/A'))
            
            # Truncate long values for table formatting
            if len(val1) > 23:
                val1 = val1[:20] + "..."
            if len(val2) > 23:
                val2 = val2[:20] + "..."
                
            report += f"{field_name:<25} {val1:<25} {val2:<25}\n"
    
    # Similarities Table
    if comparison['similarities']:
        report += f"\nSIMILARITIES ({len(comparison['similarities'])} found)\n{'-'*80}\n"
        report += f"{'Field':<30} {'Shared Value':<48}\n{'-'*80}\n"
        
        for field, value in comparison['similarities'].items():
            field_name = field.replace('_', ' ').title()
            value_str = str(value)
            if len(value_str) > 46:
                value_str = value_str[:43] + "..."
            report += f"{field_name:<30} {value_str:<48}\n"
    
    # Differences Table
    if comparison['differences']:
        report += f"\nDIFFERENCES ({len(comparison['differences'])} found)\n{'-'*80}\n"
        report += f"{'Field':<25} {'Contract 1':<25} {'Contract 2':<25}\n{'-'*80}\n"
        
        for field, values in comparison['differences'].items():
            field_name = field.replace('_', ' ').title()
            val1 = str(values.get('Contract 1', 'N/A'))
            val2 = str(values.get('Contract 2', 'N/A'))
            
            # Truncate long values for table formatting
            if len(val1) > 23:
                val1 = val1[:20] + "..."
            if len(val2) > 23:
                val2 = val2[:20] + "..."
                
            report += f"{field_name:<25} {val1:<25} {val2:<25}\n"
    
    # Missing in Contract 1 Table
    if comparison['missing_in_contract1']:
        report += f"\nMISSING IN CONTRACT 1 ({len(comparison['missing_in_contract1'])} items)\n{'-'*80}\n"
        report += f"{'Field':<30} {'Value from Contract 2':<48}\n{'-'*80}\n"
        
        for field, value in comparison['missing_in_contract1'].items():
            field_name = field.replace('_', ' ').title()
            value_str = str(value)
            if len(value_str) > 46:
                value_str = value_str[:43] + "..."
            report += f"{field_name:<30} {value_str:<48}\n"
    
    # Missing in Contract 2 Table
    if comparison['missing_in_contract2']:
        report += f"\nMISSING IN CONTRACT 2 ({len(comparison['missing_in_contract2'])} items)\n{'-'*80}\n"
        report += f"{'Field':<30} {'Value from Contract 1':<48}\n{'-'*80}\n"
        
        for field, value in comparison['missing_in_contract2'].items():
            field_name = field.replace('_', ' ').title()
            value_str = str(value)
            if len(value_str) > 46:
                value_str = value_str[:43] + "..."
            report += f"{field_name:<30} {value_str:<48}\n"
    
    # Summary Statistics Table
    report += f"\nSUMMARY STATISTICS\n{'-'*80}\n"
    report += f"{'Metric':<40} {'Count':<10} {'Percentage':<10}\n{'-'*80}\n"
    
    total_fields = len(comparison['similarities']) + len(comparison['differences']) + len(comparison['missing_in_contract1']) + len(comparison['missing_in_contract2'])
    if total_fields > 0:
        sim_pct = (len(comparison['similarities']) / total_fields) * 100
        diff_pct = (len(comparison['differences']) / total_fields) * 100
        miss1_pct = (len(comparison['missing_in_contract1']) / total_fields) * 100
        miss2_pct = (len(comparison['missing_in_contract2']) / total_fields) * 100
        
        report += f"{'Similarities':<40} {len(comparison['similarities']):<10} {sim_pct:.1f}%\n"
        report += f"{'Differences':<40} {len(comparison['differences']):<10} {diff_pct:.1f}%\n"
        report += f"{'Missing in Contract 1':<40} {len(comparison['missing_in_contract1']):<10} {miss1_pct:.1f}%\n"
        report += f"{'Missing in Contract 2':<40} {len(comparison['missing_in_contract2']):<10} {miss2_pct:.1f}%\n"
        report += f"{'Total Fields Analyzed':<40} {total_fields:<10} 100.0%\n"
    
    report += f"\n{'-'*80}\nEnd of Report\n"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\nReport saved to: {output_file}")

def main():
    print("PDF Contract Comparison Tool")
    print("="*50)
    
    # Check if required libraries are available
    if not PDF_AVAILABLE:
        error_msg = "Error: PyPDF2 is required. Please install with: pip install PyPDF2"
        print(error_msg)
        show_message("Missing Library", error_msg, "error")
        return
    
    try:
        # Show welcome message
        welcome_msg = ("Welcome to PDF Contract Comparison Tool!\n\n"
                      "You will now be prompted to select two PDF files for comparison.\n"
                      "Click OK to start selecting files.")
        show_message("Welcome", welcome_msg)
        
        # Get first PDF file using GUI
        print("\nPlease select the first PDF file...")
        pdf1_path = select_file("Select First PDF Contract File")
        
        if not pdf1_path:
            print("No file selected. Exiting.")
            return
        
        # Get second PDF file using GUI
        print(f"First file selected: {os.path.basename(pdf1_path)}")
        print("\nPlease select the second PDF file...")
        pdf2_path = select_file("Select Second PDF Contract File")
        
        if not pdf2_path:
            print("No second file selected. Exiting.")
            return
        
        print(f"Second file selected: {os.path.basename(pdf2_path)}")
        
        # Check if files exist (additional safety check)
        if not os.path.exists(pdf1_path):
            error_msg = f"Error: File not found: {pdf1_path}"
            print(error_msg)
            show_message("File Not Found", error_msg, "error")
            return
        
        if not os.path.exists(pdf2_path):
            error_msg = f"Error: File not found: {pdf2_path}"
            print(error_msg)
            show_message("File Not Found", error_msg, "error")
            return
        
        print("\nExtracting text from PDFs...")
        
        # Extract text from both PDFs
        text1 = extract_text_from_pdf(pdf1_path)
        text2 = extract_text_from_pdf(pdf2_path)
        
        if not text1 or not text2:
            error_msg = "Error: Could not extract text from one or both PDF files"
            print(error_msg)
            show_message("Extraction Error", error_msg, "error")
            return
        
        print("Analyzing contract information...")
        
        # Extract contract information
        contract1 = extract_contract_info(text1, os.path.basename(pdf1_path))
        contract2 = extract_contract_info(text2, os.path.basename(pdf2_path))
        
        # Print extracted information
        print_contract_info(contract1, "CONTRACT 1")
        print_contract_info(contract2, "CONTRACT 2")
        
        # Compare contracts
        comparison = compare_contracts(contract1, contract2)
        overall_similarity = calculate_similarity(text1, text2)
        
        # Print comparison results
        print_comparison_results(comparison, overall_similarity)
        
        # Ask if user wants to save report using GUI
        save_choice = ask_yes_no("Save Report", 
                               "Do you want to save a detailed report to a file?\n\n"
                               "This will create a markdown file with all the comparison results.")
        
        if save_choice:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Ask user to choose format
            format_choice = ask_yes_no("Report Format", 
                                     "Choose report format:\n\n"
                                     "YES = HTML (styled tables, viewable in browser)\n"
                                     "NO = TXT (plain text tables)")
            
            if format_choice:
                # HTML format
                default_filename = f"contract_comparison_{timestamp}.html"
                file_types = [("HTML files", "*.html"), ("All files", "*.*")]
            else:
                # TXT format  
                default_filename = f"contract_comparison_{timestamp}.txt"
                file_types = [("Text files", "*.txt"), ("All files", "*.*")]
            
            # Let user choose where to save the file
            root = tk.Tk()
            root.withdraw()
            
            output_file = filedialog.asksaveasfilename(
                title="Save Comparison Report",
                defaultextension=".html" if format_choice else ".txt",
                filetypes=file_types,
                initialfile=default_filename
            )
            root.destroy()
            
            if output_file:
                if format_choice:
                    save_report_html(contract1, contract2, comparison, overall_similarity, output_file)
                else:
                    save_report(contract1, contract2, comparison, overall_similarity, output_file)
                    
                success_msg = f"Report successfully saved to:\n{output_file}"
                print(f"\n{success_msg}")
                show_message("Report Saved", success_msg)
            else:
                print("\nSave cancelled by user.")
        
        # Final completion message
        completion_msg = ("Analysis complete!\n\n"
                         f"Files compared:\n"
                         f"• {os.path.basename(pdf1_path)}\n"
                         f"• {os.path.basename(pdf2_path)}\n\n"
                         f"Overall similarity: {overall_similarity:.1f}%\n"
                         f"Check the terminal/console for detailed results.")
        show_message("Analysis Complete", completion_msg)
        
    except Exception as e:
        error_msg = f"An unexpected error occurred: {str(e)}"
        print(f"\n{error_msg}")
        show_message("Unexpected Error", error_msg, "error")

if __name__ == "__main__":
    main()
