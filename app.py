import streamlit as st
from PyPDF2 import PdfReader
from PIL import Image
import os
import toml
from dotenv import load_dotenv
import google.generativeai as genai
from google.cloud import documentai
from google.api_core.client_options import ClientOptions
from google.oauth2 import service_account

# --- Page Config ---
# This should be the very first Streamlit command in your script
st.set_page_config(page_title="📜 Legal Document Demystifier", layout="wide")


# --- Authentication & Setup ---
# Use @st.cache_resource to run this setup only once
@st.cache_resource
def setup_clients():
    """A smart function to set up API clients for both local and deployed environments."""
    try:
        # --- For Deployed App (on Streamlit Cloud) ---
        # Load secrets from Streamlit's secrets manager
        service_account_info = toml.loads(st.secrets["gcp_service_account_key"])
        credentials = service_account.Credentials.from_service_account_info(service_account_info)

        api_key = st.secrets["genai_api_key"]
        project_id = st.secrets["google_cloud_project_id"]
        st.success("Connected to Google Cloud using Streamlit Secrets!")

    except (FileNotFoundError, KeyError):
        # --- For Local Development ---
        # Load secrets from the local .env file
        st.info("Running locally. Loading secrets from .env file.")
        load_dotenv()
        api_key = os.getenv("GENAI_API_KEY")
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
        key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if not os.path.isfile(key_path):
            st.error(f"Local dev: Service account key file not found at '{key_path}'. Please check your .env file.")
            st.stop()
        credentials = service_account.Credentials.from_service_account_file(key_path)

    # --- Configure and return clients (this part is the same for both environments) ---
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    docai_client = documentai.DocumentProcessorServiceClient(
        client_options=ClientOptions(api_endpoint="us-documentai.googleapis.com"),
        credentials=credentials
    )

    return model, docai_client, project_id


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
st.title("📜 Legal Document Demystifier")
st.write("Upload your legal document (PDF or image) to get a simple summary, risk analysis, and ask questions.")

# Initialize session state for storing data across reruns. This is the app's "memory".
if 'text_content' not in st.session_state:
    st.session_state.text_content = ""
if 'summary' not in st.session_state:
    st.session_state.summary = ""
if 'risk_analysis' not in st.session_state:
    st.session_state.risk_analysis = ""
if 'messages' not in st.session_state:
    st.session_state.messages = [] # For the Q&A chat history

# We move the file uploader to a sidebar for a cleaner layout
with st.sidebar:
    st.header("Upload Document")
    uploaded_files = st.file_uploader(
        "Upload a PDF or Image(s)",
        type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True
    )

    if st.button("Analyze Document"):
        if uploaded_files:
            # When the button is clicked, we process the files
            with st.spinner("Extracting text from document..."):
                all_texts = []
                for file in uploaded_files:
                    if file.type == "application/pdf":
                        all_texts.append(extract_text_from_pdf(file))
                    else:
                        all_texts.append(extract_text_from_image(file, project_id))

                st.session_state.text_content = "\n\n".join(all_texts)
                
                # Clear out any old results from previous documents
                st.session_state.summary = ""
                st.session_state.risk_analysis = ""
                st.session_state.messages = []

            if not st.session_state.text_content.strip():
                st.error("Could not extract any text. Please try a clearer document.")
            else:
                st.success("Document processed! You can now explore the analysis tabs.")
        else:
            st.warning("Please upload a file first.")

# This section only runs if text has been successfully extracted
if st.session_state.text_content:
    # Use tabs for organized output
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
        st.header("⚠️ Risk Analysis")
        if not st.session_state.risk_analysis:
            with st.spinner("Analyzing risks..."):
                risk_prompt = f"""
                From the legal text, identify 3-5 key clauses, potential risks, or points of negotiation.
                For each point, provide a simple explanation and classify its severity as 'Low', 'Medium', or 'High'.
                Format each point on a new line like this:
                Severity: [Severity Level] - [Explanation of the clause/risk]
                LEGAL TEXT: {st.session_state.text_content}
                """
                response = model.generate_content(risk_prompt)
                st.session_state.risk_analysis = response.text
        
        for line in st.session_state.risk_analysis.split('\n'):
            line = line.strip()
            if not line: continue
            if 'Severity: High' in line:
                st.error(line.replace("Severity: High -", "**High Risk:**"))
            elif 'Severity: Medium' in line:
                st.warning(line.replace("Severity: Medium -", "**Medium Risk:**"))
            elif 'Severity: Low' in line:
                st.info(line.replace("Severity: Low -", "**Low Risk:**"))
            else:
                st.write(line)

    with tab3:
        # --- All Q&A Chat UI and Logic is now correctly indented INSIDE this block ---
        st.header("❓ Ask a Question About Your Document")

        # Inject custom CSS
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

        # Display chat history
        for message in st.session_state.messages:
            role, content, avatar = message["role"], message["content"], "👤" if message["role"] == "user" else "📜"
            if role == "user":
                st.markdown(f'<div class="chat-row user-message"><div class="chat-bubble user-bubble">{content}</div><div class="chat-avatar">{avatar}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-row assistant-message"><div class="chat-avatar">{avatar}</div><div class="chat-bubble assistant-bubble">{content}</div></div>', unsafe_allow_html=True)
        
        # Chat input
        if prompt := st.chat_input("Ask anything about the document..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.markdown(f'<div class="chat-row user-message"><div class="chat-bubble user-bubble">{prompt}</div><div class="chat-avatar">👤</div></div>', unsafe_allow_html=True)

            with st.spinner("Thinking..."):
                qa_prompt = f"Answer the user's question based ONLY on the following document. If the answer isn't there, say so.\nDOCUMENT: {st.session_state.text_content}\nQUESTION: {prompt}"
                response = model.generate_content(qa_prompt)
                full_response = response.text
                
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
    st.info("Upload a document and click 'Analyze Document' to get started.")