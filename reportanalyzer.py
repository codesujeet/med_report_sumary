import streamlit as st
import pandas as pd
import io
import re
from pathlib import Path
import json
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
import PyPDF2
import docx
from typing import Dict, List, Set, Optional, Any, Tuple
import nltk
from nltk.tokenize import sent_tokenize

# Try to download nltk data, with error handling
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    try:
        nltk.download('punkt', quiet=True)
    except Exception as e:
        pass  # Graceful fallback if download fails


class MedicalReportAnalyzer:
    """Class to analyze and extract information from medical reports."""
    
    def __init__(self):
        self.reports = []
        self.summary = {}
        self.findings_patterns = {
            'diagnoses': r'(?:diagnosis|assessment|impression|diagnosed with)[:\s](.*?)(?:\n|$)',
            'medications': r'(?:medication|drug|prescription|prescribed)[:\s](.*?)(?:\n|$)',
            'vitals': r'(?:vital|measurement|blood pressure|temperature|pulse|height|weight)[:\s](.*?)(?:\n|$)',
            'lab_results': r'(?:lab|laboratory|test|result|blood work)[:\s](.*?)(?:\n|$)',
            'recommendations': r'(?:recommendation|plan|follow up|advised)[:\s](.*?)(?:\n|$)'
        }
        
    def process_file(self, file) -> bool:
        """
        Process individual file and extract content based on file type.
        
        Args:
            file: The uploaded file object
            
        Returns:
            bool: True if file processed successfully, False otherwise
        """
        try:
            file_ext = Path(file.name).suffix.lower()
            content = ""
            
            file.seek(0)
            
            if file_ext == '.pdf':
                content = self._extract_pdf_content(file)
            elif file_ext == '.txt':
                content = file.read().decode('utf-8')
            elif file_ext in ['.doc', '.docx']:
                content = self._extract_docx_content(file)
            else:
                st.warning(f"Unsupported file format: {file_ext}")
                return False
            
            # Clean content
            content = self._clean_text(content)
            
            report = {
                'name': file.name,
                'content': content,
                'date': datetime.now().isoformat(),
                'type': file_ext,
                'key_findings': self.extract_key_findings(content),
                'metadata': {
                    'word_count': len(content.split()),
                    'character_count': len(content),
                    'sentence_count': len(sent_tokenize(content)) if content else 0
                }
            }
            
            self.reports.append(report)
            return True
            
        except Exception as e:
            st.error(f"Error processing file {file.name}: {str(e)}")
            return False

    def _extract_pdf_content(self, file) -> str:
        """Extract text content from PDF files."""
        pdf_bytes = io.BytesIO(file.read())
        pdf_reader = PyPDF2.PdfReader(pdf_bytes)
        content = "\n".join(page.extract_text() for page in pdf_reader.pages if page.extract_text())
        return content
    
    def _extract_docx_content(self, file) -> str:
        """Extract text content from DOCX files."""
        doc = docx.Document(io.BytesIO(file.read()))
        content = "\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text)
        return content
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        
        # Replace multiple newlines with a single newline
        text = re.sub(r'\n+', '\n', text)
        
        # Replace multiple spaces with a single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove non-printable characters
        text = ''.join(c for c in text if c.isprintable() or c == '\n')
        
        return text.strip()

    def extract_key_findings(self, content: str) -> Dict[str, List[str]]:
        """
        Extract key medical information from report content.
        
        Args:
            content: The text content of the medical report
            
        Returns:
            Dict containing categorized medical findings
        """
        findings = {
            'diagnoses': [],
            'medications': [],
            'vitals': [],
            'lab_results': [],
            'recommendations': []
        }
        
        if not content:
            return findings
        
        for category, pattern in self.findings_patterns.items():
            matches = re.finditer(pattern, content, re.IGNORECASE)
            findings[category] = []
            
            for match in matches:
                text = match.group(1).strip()
                if text and len(text) > 2:
                    # Normalize the text (remove extra spaces, etc.)
                    text = re.sub(r'\s+', ' ', text).strip()
                    findings[category].append(text)
        
        return findings

    def generate_summary(self) -> str:
        """
        Generate comprehensive summary from all processed reports.
        
        Returns:
            Formatted summary text
        """
        if not self.reports:
            return "No reports have been processed yet."
        
        summary = {
            'total_reports': len(self.reports),
            'report_types': self._count_report_types(),
            'report_dates': self._extract_report_dates(),
            'key_findings': {
                'diagnoses': set(),
                'medications': set(),
                'vitals': set(),
                'lab_results': set(),
                'recommendations': set()
            },
            'metadata': {
                'total_word_count': sum(report['metadata']['word_count'] for report in self.reports),
                'avg_sentences_per_report': sum(report['metadata']['sentence_count'] for report in self.reports) / len(self.reports)
            }
        }
        
        for report in self.reports:
            for category, items in report['key_findings'].items():
                summary['key_findings'][category].update(items)
        
        # Convert sets to sorted lists
        for category in summary['key_findings']:
            summary['key_findings'][category] = sorted(list(summary['key_findings'][category]))
            if not summary['key_findings'][category]:
                summary['key_findings'][category] = []
        
        self.summary = summary
        return self.format_summary()
    
    def _count_report_types(self) -> Dict[str, int]:
        """Count the number of reports by file type."""
        type_counts = {}
        for report in self.reports:
            file_type = report['type']
            type_counts[file_type] = type_counts.get(file_type, 0) + 1
        return type_counts
    
    def _extract_report_dates(self) -> List[str]:
        """Extract processed dates for all reports."""
        return [report['date'] for report in self.reports]

    def format_summary(self) -> str:
        """
        Format summary for display.
        
        Returns:
            Formatted summary text
        """
        if not self.summary:
            return "No summary available."
        
        formatted = f"""# Medical Report Summary
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview
- **Total Reports**: {self.summary['total_reports']}
- **File Types**: {', '.join(f"{ext} ({count})" for ext, count in self.summary['report_types'].items())}
- **Total Words**: {self.summary.get('metadata', {}).get('total_word_count', 'N/A')}
- **Avg. Sentences/Report**: {self.summary.get('metadata', {}).get('avg_sentences_per_report', 'N/A'):.1f}

## Key Findings

### Diagnoses:
{self._format_list(self.summary['key_findings']['diagnoses'])}

### Medications:
{self._format_list(self.summary['key_findings']['medications'])}

### Vital Signs:
{self._format_list(self.summary['key_findings']['vitals'])}

### Lab Results:
{self._format_list(self.summary['key_findings']['lab_results'])}

### Recommendations:
{self._format_list(self.summary['key_findings']['recommendations'])}

## Important Note
The information above is automatically extracted and may not be complete or accurate.
Please verify all findings with healthcare professionals.
        """
        return formatted

    def _format_list(self, items: List[str]) -> str:
        """
        Helper function to format lists.
        
        Args:
            items: List of items to format
            
        Returns:
            Formatted string
        """
        if not items or len(items) == 0:
            return "- No findings in this category"
        
        return '\n'.join(f"- {item}" for item in items)
    
    def export_to_json(self) -> str:
        """Export all reports and summary to JSON format."""
        export_data = {
            'summary': self.summary,
            'reports': self.reports,
            'generated_at': datetime.now().isoformat()
        }
        
        return json.dumps(export_data, indent=2)
    
    def clear_data(self) -> None:
        """Reset the analyzer state."""
        self.reports = []
        self.summary = {}


def render_sidebar():
    """Render the sidebar with about information and help."""
    with st.sidebar:
        st.title("ℹ️ About")
        st.markdown("""
        The Medical Report Analyzer is a tool designed to help process and analyze medical reports efficiently.
        
        ### Features
        - Multi-format support (PDF, TXT, DOC, DOCX)
        - Automatic key finding extraction
        - Interactive summary editing
        - Data visualization
        - Report exporting in multiple formats
        
        ### How to Use
        1. Upload your medical reports using the file uploader
        2. Click "Process Files" to extract information
        3. Click "Generate Analysis" to view results
        4. Edit and download the summary as needed
        
        ### Privacy Notice
        All processing is done locally in your browser. No data is stored or transmitted to external servers.
        """)
        
        st.markdown("---")
        
        # Add file format information
        st.subheader("📄 Supported Formats")
        formats = {
            "PDF": "Medical reports, discharge summaries",
            "TXT": "Plain text medical notes",
            "DOC/DOCX": "Word document reports"
        }
        
        for fmt, desc in formats.items():
            st.markdown(f"**{fmt}**: {desc}")
            
        st.markdown("---")
        
        # Add a help section
        st.subheader("❓ Need Help?")
        with st.expander("Common Issues"):
            st.markdown("""
            - **File not processing**: Ensure the file is not corrupted and in a supported format
            - **No findings detected**: Check if the report uses standard medical terminology
            - **Text extraction issues**: Try converting PDF to text format
            """)
            
        # Add a system status section
        with st.expander("System Status"):
            st.markdown("""
            - **NLTK Data**: Checking...
            """)
            try:
                nltk.data.find('tokenizers/punkt')
                st.success("NLTK Tokenizer: Available")
            except LookupError:
                st.error("NLTK Tokenizer: Not Available")
            
        # Version information
        st.markdown("---")
        st.markdown("**Version**: 1.1.0")
        st.markdown("**Last Updated**: 2025-02-26")


def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="Medical Report Analyzer",
        page_icon="🏥",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Apply custom CSS
    st.markdown("""
    <style>
    .reportview-container .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 20px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e6f0ff;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Render sidebar
    render_sidebar()
    
    # Main content
    st.title("🏥 Medical Report Analyzer")
    st.markdown("Upload and analyze medical reports to extract key findings and generate summaries")
    
    # Initialize session state
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = MedicalReportAnalyzer()
        st.session_state.edited_summary = ""
        st.session_state.uploaded_files_count = 0
        st.session_state.processed_files = []
    
    # Create tabs for better organization
    tabs = st.tabs(["📤 Upload & Process", "📊 Analysis & Results", "⚙️ Settings"])
    
    with tabs[0]:  # Upload & Process tab
        col1, col2 = st.columns([3, 1])
        
        with col1:
            uploaded_files = st.file_uploader(
                "Upload Medical Reports",
                type=['txt', 'pdf', 'doc', 'docx'],
                accept_multiple_files=True,
                help="Select one or more medical reports to analyze"
            )
        
        with col2:
            reset_button = st.button("Reset All Data", use_container_width=True, type="secondary")
            if reset_button:
                st.session_state.analyzer.clear_data()
                st.session_state.edited_summary = ""
                st.session_state.uploaded_files_count = 0
                st.session_state.processed_files = []
                st.success("All data has been reset!")
                st.rerun()
        
        st.divider()
        
        # Process files section
        if uploaded_files:
            if len(uploaded_files) != st.session_state.uploaded_files_count:
                st.session_state.uploaded_files_count = len(uploaded_files)
                st.session_state.processed_files = []
            
            # Display file information
            file_df = pd.DataFrame([
                {
                    "Filename": file.name,
                    "Size (KB)": round(file.size / 1024, 2),
                    "Type": Path(file.name).suffix,
                    "Status": "✅ Processed" if file.name in st.session_state.processed_files else "⏳ Pending"
                }
                for file in uploaded_files
            ])
            
            st.dataframe(file_df, use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                process_button = st.button("1. Process Files", use_container_width=True, type="primary")
            with col2:
                analyze_button = st.button("2. Generate Analysis", use_container_width=True)
            
            if process_button:
                # Reset analyzer to ensure fresh processing
                st.session_state.analyzer = MedicalReportAnalyzer()
                st.session_state.processed_files = []
                
                with st.spinner("Processing files..."):
                    progress_bar = st.progress(0)
                    total_files = len(uploaded_files)
                    
                    for i, file in enumerate(uploaded_files):
                        if st.session_state.analyzer.process_file(file):
                            st.session_state.processed_files.append(file.name)
                        else:
                            st.error(f"Failed to process: {file.name}")
                        
                        # Update progress
                        progress_bar.progress((i + 1) / total_files)
                
                st.success(f"Processed {len(st.session_state.processed_files)} of {total_files} files")
        else:
            st.info("Please upload medical reports to begin")
    
    with tabs[1]:  # Analysis & Results tab
        if 'analyzer' in st.session_state and st.session_state.analyzer.reports:
            # If 'analyze_button' was clicked or if reports are already processed
            if analyze_button or st.session_state.edited_summary:
                summary = st.session_state.analyzer.generate_summary()
                
                # Create columns for better layout
                st.markdown("### 📊 Findings Overview")
                
                # Display visualizations
                col1, col2 = st.columns(2)
                
                with col1:
                    # Create bar chart of key findings
                    categories = list(st.session_state.analyzer.summary['key_findings'].keys())
                    counts = [len(st.session_state.analyzer.summary['key_findings'][cat]) for cat in categories]
                    
                    fig = px.bar(
                        x=categories,
                        y=counts,
                        labels={"x": "Category", "y": "Count"},
                        title="Distribution of Findings",
                        color=counts,
                        color_continuous_scale="Blues",
                        template="plotly_white"
                    )
                    
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Create a pie chart of file types
                    file_types = list(st.session_state.analyzer.summary['report_types'].keys())
                    type_counts = list(st.session_state.analyzer.summary['report_types'].values())
                    
                    fig = px.pie(
                        values=type_counts,
                        names=file_types,
                        title="Report Types Distribution",
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
                
                st.divider()
                
                # Full summary section
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Summary section
                    st.markdown("### 📝 Report Summary")
                    st.code(summary, language="markdown")
                    
                    st.markdown("### ✏️ Edit Summary")
                    st.session_state.edited_summary = st.text_area(
                        "Edit the summary below:",
                        value=summary if not st.session_state.edited_summary else st.session_state.edited_summary,
                        height=400,
                        key="summary_editor"
                    )
                
                with col2:
                    # Actions and export options
                    st.markdown("### 🎯 Actions")
                    
                    st.download_button(
                        "📄 Download as Text",
                        st.session_state.edited_summary,
                        file_name="medical_report_summary.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                    
                    st.download_button(
                        "📊 Export as JSON",
                        st.session_state.analyzer.export_to_json(),
                        file_name="medical_report_data.json",
                        mime="application/json",
                        use_container_width=True
                    )
                    
                    # Display individual report details
                    st.markdown("### 📑 Report Details")
                    
                    for i, report in enumerate(st.session_state.analyzer.reports):
                        with st.expander(f"Report {i+1}: {report['name']}"):
                            st.markdown(f"**File Type**: {report['type']}")
                            st.markdown(f"**Processed**: {report['date']}")
                            st.markdown(f"**Word Count**: {report['metadata']['word_count']}")
                            
                            # Show findings from this report
                            st.markdown("#### Key Findings:")
                            for category, items in report['key_findings'].items():
                                if items:
                                    st.markdown(f"**{category.capitalize()}**:")
                                    for item in items:
                                        st.markdown(f"- {item}")
            else:
                st.info("Click 'Generate Analysis' to view results")
        else:
            st.warning("No processed reports available. Please upload and process files first.")
    
    with tabs[2]:  # Settings tab
        st.markdown("### ⚙️ Analysis Settings")
        
        if 'analyzer' in st.session_state:
            # Allow editing of regex patterns
            st.markdown("#### Pattern Settings")
            st.markdown("Customize the regular expressions used to extract findings from reports:")
            
            # Create a copy of patterns to edit
            patterns_modified = False
            
            for category, pattern in st.session_state.analyzer.findings_patterns.items():
                new_pattern = st.text_input(
                    f"{category.capitalize()} Pattern:",
                    value=pattern,
                    key=f"pattern_{category}"
                )
                
                if new_pattern != pattern:
                    st.session_state.analyzer.findings_patterns[category] = new_pattern
                    patterns_modified = True
            
            if patterns_modified:
                st.info("Patterns have been modified. Re-process your files to apply changes.")
            
            # Add option to save/load configurations
            st.divider()
            st.markdown("#### Configuration")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Save Configuration", use_container_width=True):
                    config = {
                        "patterns": st.session_state.analyzer.findings_patterns,
                        "version": "1.1.0"
                    }
                    st.download_button(
                        "Download Configuration File",
                        json.dumps(config, indent=2),
                        file_name="medical_analyzer_config.json",
                        mime="application/json",
                        key="download_config",
                        use_container_width=True
                    )
            
            with col2:
                config_file = st.file_uploader(
                    "Load Configuration",
                    type=['json'],
                    help="Upload a previously saved configuration file"
                )
                
                if config_file:
                    try:
                        config_data = json.loads(config_file.getvalue().decode('utf-8'))
                        if "patterns" in config_data:
                            st.session_state.analyzer.findings_patterns = config_data["patterns"]
                            st.success("Configuration loaded successfully!")
                        else:
                            st.error("Invalid configuration file!")
                    except Exception as e:
                        st.error(f"Error loading configuration: {str(e)}")

    # Footer
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center'>
            <p>🏥 Medical Report Analyzer v1.1.0</p>
            <p>For educational and assistive purposes only. Always verify findings with healthcare professionals.</p>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()