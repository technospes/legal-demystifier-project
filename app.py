import streamlit as st
from PyPDF2 import PdfReader
from PIL import Image
import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
from google.cloud import documentai
from google.api_core.client_options import ClientOptions
from google.oauth2 import service_account

# --- Page Config ---
# This should be the very first Streamlit command in your script
st.set_page_config(page_title="📜 ParleyAlly: Legal Document Demystifier", layout="wide")
st.markdown("""
<style>
    /* --- Main App Layout --- */
    /* Remove the centered layout */
    .stApp {
        max-width: none;
        margin: 0;
        padding: 0;
    }
    
    /* Target the main content block to add padding */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 5rem;  /* Pushes content away from the sidebar */
        padding-right: 5rem; /* Adds a margin on the right */
    }

    /* --- Sidebar --- */
    /* Make the sidebar wider */
    .stSidebar {
        width: 350px !important; /* Force a wider sidebar */
    }

    /* --- General Styling (from before) --- */
    body {
        background-color: #0c121c;
        color: #e0e0e0;
    }
    h1, h2, h3 {
        color: #ffffff;
    }
    .stAlert {
        border-radius: 0.5rem;
    }
    
    /* --- Green Primary Button (from before) --- */
    button[kind="primary"] {
        background-color: #4CAF50;
        color: white;
    }
    button[kind="primary"]:hover {
        background-color: #45a049;
        color: white;
        border-color: #45a049;
    }
    button[data-baseweb="tab"] {
    font-size: 1.5em;   /* Increase font size slightly */
    font-weight: 600;   /* Make the font a bit bolder */
    padding: 0.75rem 1rem; /* Adjust padding to fit the new text size */
    }
</style>
""", unsafe_allow_html=True)


# --- Authentication & Setup ---
# Use @st.cache_resource to run this setup only once
@st.cache_resource
def setup_clients():
    """A smart function to set up API clients for both local and deployed environments."""
    try:
        # For Deployed App (on Streamlit Cloud)
        service_account_info = json.loads(st.secrets["gcp_service_account_key"])
        credentials = service_account.Credentials.from_service_account_info(service_account_info)
        api_key = st.secrets["genai_api_key"]
        project_id = st.secrets["gcp_project_id"]

    except (FileNotFoundError, KeyError):
        # For Local Development
        load_dotenv()
        api_key = os.getenv("GENAI_API_KEY")
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
        key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        if not os.path.isfile(key_path):
            st.error(f"Local dev: Service account key file not found at '{key_path}'.")
            st.stop()
        credentials = service_account.Credentials.from_service_account_file(key_path)

    # Configure and return clients
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    docai_client = documentai.DocumentProcessorServiceClient(
        client_options=ClientOptions(api_endpoint="us-documentai.googleapis.com"),
        credentials=credentials
    )
    
    return model, docai_client, project_id
# --- Helper Functions ---

def clear_all():
    """Clears all the stored information and widget states."""
    st.session_state.text_content = ""
    st.session_state.summary = ""
    st.session_state.risk_analysis = ""
    st.session_state.messages = []
    st.session_state.analysis_complete = False
    st.session_state.processing = False
    # Clear the file uploader widget state 
    st.toast("App has been reset.", icon="🔄")
# --- Helper Functions ---
def extract_text_from_pdf(pdf_file):
    """Extracts text from an uploaded PDF file."""
    text = ""
    try:
        reader = PdfReader(pdf_file)
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
    return text

def extract_text_from_image(img_file, project_id):
    """Extracts text from an uploaded image file using Document AI."""
    try:
        location = "us"
        processor_id = "6a4d6bf5a98ce47c" # Your Processor ID
        processor_name = docai_client.processor_path(project_id, location, processor_id)
        
        image_content = img_file.getvalue()
        raw_document = documentai.RawDocument(content=image_content, mime_type=img_file.type)
        request = documentai.ProcessRequest(name=processor_name, raw_document=raw_document)
        
        result = docai_client.process_document(request=request)
        return result.document.text
    except Exception as e:
        st.error(f"Document AI failed for {img_file.name}: {e}")
        return ""

model, docai_client, project_id = setup_clients()
# --- UI & Main Logic ---
st.markdown("<h1 style='text-align: center; color: #e0e0e0; font-size: 2.8em; margin-bottom: 0.5em;'>📜 <span style='color: #4CAF50;'>Parley</span>Ally</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #cccccc; font-size: 1.1em; max-width: 700px; margin: auto;'>Your intelligent assistant for understanding complex legal documents. Get instant summaries, risk analysis, and answers to your questions.</p>", unsafe_allow_html=True)

# Initialize session state for storing data across reruns. This is the app's "memory".
if 'text_content' not in st.session_state:
    st.session_state.text_content = ""
if 'summary' not in st.session_state:
    st.session_state.summary = ""
if 'risk_analysis' not in st.session_state:
    st.session_state.risk_analysis = ""
if 'messages' not in st.session_state:
    st.session_state.messages = [] 
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'processing' not in st.session_state:
    st.session_state.processing = False

# We move the file uploader to a sidebar for a cleaner layout
# We move the file uploader and buttons to a sidebar
with st.sidebar:
    st.markdown("<h2 style='color: #ffffff; text-align: center;'>📄 Document Uploader</h2>", unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader(
        "**Choose your legal document(s):**", # Bolder label
        type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="file_uploader" 
    )

    st.markdown("---") # Replaced st.divider() with a markdown divider for better styling control

    # A short explanatory text for button functionality
    st.info("Upload and click 'Analyze' to begin. Use 'Reset' to clear all data.")

    is_processing = st.session_state.processing
    analyze_button_type = "primary" if st.session_state.analysis_complete else "secondary"

    col1, col2 = st.columns(2)
    with col1:
        analyze_button = st.button("Analyze", use_container_width=True, type=analyze_button_type, disabled=is_processing)
    with col2:
        st.button("Reset", use_container_width=True, disabled=is_processing, on_click=clear_all)

    if analyze_button:
        if uploaded_files:
            st.session_state.processing = True
            st.rerun()
        else:
            st.toast("Please upload a file first.", icon="⚠️")

    if st.session_state.processing:
        # ... (The rest of your processing logic remains exactly the same) ...
        with st.spinner("Processing document..."):
            st.toast("Extracting text from your files...", icon="🔍")
            all_texts = []
            for file in st.session_state.file_uploader:
                if file.type == "application/pdf":
                    all_texts.append(extract_text_from_pdf(file))
                else:
                    all_texts.append(extract_text_from_image(file, project_id))
            
            st.session_state.text_content = "\n\n".join(all_texts)
            st.session_state.summary = ""
            st.session_state.risk_analysis = ""
            st.session_state.messages = []

        if not st.session_state.text_content.strip():
            st.toast("Could not extract any text.", icon="❌")
            st.session_state.analysis_complete = False
        else:
            st.toast("Analysis complete!", icon="✅")
            st.session_state.analysis_complete = True
        
        st.session_state.processing = False
        st.rerun()
# This section only runs if text has been successfully extracted
if st.session_state.text_content:
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Summary", "⚠️ Risk Analysis", "❓ Q&A Chat", "🧐 Explain Clause"])
    with tab1:
        st.header("📄 Document Summary")
        if not st.session_state.summary:
            with st.spinner("Generating summary..."):
                prompt = f"""
                You are a legal expert. Analyze the provided document text and provide a structured summary. Use simple language.
                Include: Document Type, Main Purpose, Parties Involved, Key Dates, Financial Aspects, Main Rights & Obligations, and Termination Conditions.
                DOCUMENT TEXT: {st.session_state.text_content}
                """
                response = model.generate_content(prompt)
                st.session_state.summary = response.text
        st.markdown(st.session_state.summary)

    with tab2:
        st.header("⚠️ Consolidated Risk Analysis")
        st.info("The AI has scanned your document for risky, ambiguous, and positive clauses. Click to expand each category.")

        # We'll use a new session state key to store this analysis
        if 'grouped_risks' not in st.session_state:
            st.session_state.grouped_risks = None

        if st.session_state.grouped_risks is None and st.session_state.text_content:
            with st.spinner("Categorizing clauses by risk level..."):
                
                # This is our new, smarter prompt
                risk_grouping_prompt = f"""
                You are a legal analyst. Your task is to analyze the provided document and categorize important clauses into three distinct groups: "High Risk", "Medium Risk", and "Good Clause".

                A "Good Clause" is one that is fair, clear, and standard for this type of document.

                You must respond ONLY with a single valid JSON object. Do not include any other text or markdown.
                The JSON object should have three keys: "high_risks", "medium_risks", and "good_clauses".
                Each key should correspond to a list of objects, where each object has two keys: "clause" (the exact text snippet) and "explanation".

                Example format:
                {{
                "high_risks": [
                    {{ "clause": "The tenant is responsible for all structural repairs.", "explanation": "This is highly unusual and places an unfair financial burden on the tenant." }}
                ],
                "medium_risks": [
                    {{ "clause": "The rent may be adjusted periodically.", "explanation": "This is ambiguous. It should specify when and by how much the rent can be adjusted." }}
                ],
                "good_clauses": [
                    {{ "clause": "The landlord shall provide a 24-hour notice before entering the premises.", "explanation": "This is a standard and fair clause that respects the tenant's privacy." }}
                ]
                }}

                Now, analyze the following document:
                ---
                {st.session_state.text_content}
                ---
                """
                
                flash_model = genai.GenerativeModel('gemini-1.5-flash')
                response = flash_model.generate_content(risk_grouping_prompt)
                
                try:
                    clean_response = response.text.strip().replace("```json", "").replace("```", "")
                    st.session_state.grouped_risks = json.loads(clean_response)
                except (json.JSONDecodeError, AttributeError):
                    st.error("Failed to get a valid risk analysis from the AI.")
                    st.session_state.grouped_risks = {}

        # --- Display the categorized risks using expanders ---
        if st.session_state.grouped_risks:
            risks = st.session_state.grouped_risks
            
            # Display High Risks
            high_risks = risks.get("high_risks", [])
            if high_risks:
                with st.expander(f"🔴 High Risks ({len(high_risks)})", expanded=True):
                    for item in high_risks:
                        st.error(f"**Clause:** \"{item['clause']}\"\n\n**Reasoning:** {item['explanation']}")
            
            # Display Medium Risks
            medium_risks = risks.get("medium_risks", [])
            if medium_risks:
                with st.expander(f"🟠 Medium Risks ({len(medium_risks)})"):
                    for item in medium_risks:
                        st.warning(f"**Clause:** \"{item['clause']}\"\n\n**Reasoning:** {item['explanation']}")

            # Display Good Clauses
            good_clauses = risks.get("good_clauses", [])
            if good_clauses:
                with st.expander(f"🟢 Good Clauses ({len(good_clauses)})"):
                    for item in good_clauses:
                        st.success(f"**Clause:** \"{item['clause']}\"\n\n**Reasoning:** {item['explanation']}")

    with tab3:
        st.header("❓ Ask a Question About Your Document")

        # Inject custom CSS (this part is the same)
        st.markdown("""
            <style>
                .chat-row { display: flex; align-items: flex-start; margin-bottom: 1rem; }
                .user-message { justify-content: flex-end; }
                .assistant-message { justify-content: flex-start; }
                .chat-bubble { padding: 0.9rem 1rem; border-radius: 1rem; max-width: 70%; word-wrap: break-word; }
                .user-bubble { background-color: #2b313e; color: #ffffff; }
                .assistant-bubble { background-color: #444654; color: #ffffff; }
                .chat-avatar { font-size: 1.8rem; margin: 0 0.5rem; }
            </style>
        """, unsafe_allow_html=True)

        # Display welcome message if chat is empty
        if not st.session_state.messages:
            st.info("Ask me anything about the document you uploaded!")

        # Display chat history using our custom HTML
        for message in st.session_state.messages:
            role, content = message["role"], message["content"]
            avatar = "👤" if role == "user" else "📜"
            
            if role == "user":
                st.markdown(f'<div class="chat-row user-message"><div class="chat-bubble user-bubble">{content}</div><div class="chat-avatar">{avatar}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-row assistant-message"><div class="chat-avatar">{avatar}</div><div class="chat-bubble assistant-bubble">{content}</div></div>', unsafe_allow_html=True)
        
        # --- UNIFIED CHAT INPUT USING THE PRO MODEL AND BETTER PROMPT ---
        if prompt := st.chat_input("Ask anything about the document..."):
            # Add and display the user's message
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.markdown(f'<div class="chat-row user-message"><div class="chat-bubble user-bubble">{prompt}</div><div class="chat-avatar">👤</div></div>', unsafe_allow_html=True)

            # Generate the response using the Pro model and the improved prompt
            with st.spinner("Thinking..."):
                pro_model = genai.GenerativeModel('gemini-1.5-flash')
                
                # This improved prompt instructs the model to be more factual and careful
                improved_prompt = f"""
                You are a meticulous legal assistant. Your task is to answer the user's question with high accuracy, based ONLY on the provided document text.

                Instructions:
                1.  Carefully read the user's question and the entire document.
                2.  Formulate an answer based exclusively on the information present in the text.
                3.  If possible, quote the exact phrase or sentence from the document that supports your answer.
                4.  If the answer is not found in the document, you must state: "The answer to that question is not found in the provided document." Do not guess or infer information.

                ---
                DOCUMENT TEXT:
                {st.session_state.text_content}
                ---
                USER'S QUESTION:
                "{prompt}"
                """
                
                response = pro_model.generate_content(improved_prompt)
                full_response = response.text
                
                # Display the assistant's response and add it to history
                st.markdown(f'<div class="chat-row assistant-message"><div class="chat-avatar">📜</div><div class="chat-bubble assistant-bubble">{full_response}</div></div>', unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": full_response})

    with tab4:
        st.header("🧐 Explain a Confusing Clause")
        clause_to_explain = st.text_area("Paste a clause or term from the document here:", key="clause_input")

        if st.button("Explain This!", key="explain_button"):
            if clause_to_explain:
                with st.spinner("Demystifying..."):
                    explain_prompt = f'Explain the following legal clause in simple terms for a non-lawyer.\nCLAUSE: "{clause_to_explain}"'
                    response = model.generate_content(explain_prompt)
                    st.success("Here's a simple explanation:")
                    st.markdown(response.text)
            else:
                st.warning("Please paste a clause to explain.")
    
    with st.expander("Show Extracted Raw Text"):
        st.text_area("Raw Text", st.session_state.text_content, height=300, disabled=True)

else:
    st.info("Upload a document and click 'Analyze' to get started.")
    # Add this entire block at the end of your other "with tabX:" sections