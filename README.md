# ⚖️ ParleyAlly – Legal Document Demystifier

ParleyAlly is a Python-based backend service designed to act as a digital interpreter for complex legal documents. By leveraging Optical Character Recognition (OCR) and Generative AI, it transforms dense, jargon-filled text into simple, understandable summaries, empowering non-lawyers to comprehend the documents they are reading or signing.

---

## The Problem
Legal documents—from rental agreements to terms of service—are often dense, filled with complex jargon, and intimidating for anyone without a law degree. This "information asymmetry" can lead to people signing contracts they don't fully understand, creating personal and financial risk. The goal of ParleyAlly is to democratize access to this information.

## The Solution
ParleyAlly provides a simple-to-use service that ingests a legal document (even a scanned copy) and outputs a clear, plain-language summary. It identifies key clauses, translates confusing terminology, and explains the practical implications of the text, allowing a user to quickly grasp the core of the document without needing a lawyer for a first-pass review.

---

## 📷 Demo

[ADD A SCREENSHOT HERE: Show a side-by-side comparison of a complex legal clause on the left and ParleyAlly's simplified explanation on the right.]

---

## ✨ Key Features Explained

- **Universal Document Ingestion:** The service handles both digitally-native PDFs and scanned, image-based documents by using a robust pipeline that first attempts direct text extraction and then falls back to a powerful Tesseract OCR engine.
- **Intelligent Summarization with RAG:** To ensure high accuracy and prevent AI "hallucinations," ParleyAlly uses a Retrieval-Augmented Generation (RAG) pipeline. This provides the Generative AI with relevant context before it creates the summary, dramatically improving the factual accuracy of the output.
- **Jargon-to-Plain-Language Translation:** The core value of the application. It can identify and translate specific legal terminology (e.g., "heretofore," "party of the first part") into simple, modern language.
- **Scalable API Endpoint:** The entire service is exposed via a RESTful API, allowing other applications—like a mobile app or a website front-end—to easily integrate its document simplification capabilities.

---

## ⚙️ How It Works

1.  **API Request:** A client sends a `POST` request to the API endpoint with a PDF document.
2.  **Text Extraction Pipeline:** The backend, built with Python, first uses the PyPDF2 library to attempt direct text extraction. If the text is garbled or absent (indicating a scan), it passes the PDF pages to the Tesseract OCR engine to convert the images to raw text.
3.  **Text Pre-processing:** The raw text is cleaned, structured, and prepared for the AI model using libraries like NumPy and Pandas.
4.  **RAG Execution:** The cleaned text is used as a query to a knowledge base. The original text plus the retrieved context are fed into the Generative AI model.
5.  **Summary Generation:** The GenAI model, guided by the RAG pipeline and sophisticated prompt engineering, generates the final simplified summary and explanations.
6.  **API Response:** The service returns the simplified text in a structured JSON format.

---

## 🛠️ Tech Stack Deep Dive

- **Core Language:** **Python**, chosen for its extensive ecosystem of data processing and AI/ML libraries.
- **Web Framework:** **Flask**, used to create a lightweight and efficient RESTful API for the service.
- **Text Extraction:** **Tesseract (via pytesseract)** for its powerful OCR capabilities and **PyPDF2** for native PDF text handling.
- **AI & ML:** A **Generative AI** model fine-tuned with a **Retrieval-Augmented Generation (RAG)** architecture for high-accuracy summarization. `PyTorch` is being explored for future model fine-tuning.
- **Data Processing:** **NumPy** and **Pandas** for cleaning and structuring the extracted text data.

---

## 🧠 Challenges & Future Work

- **Challenge:** Handling the vast variety of unconventional formatting and layouts found in legal documents, which often required creating pre-processing logic to assist the OCR engine.
- **Challenge:** Mitigating the risk of the AI misinterpreting a critical legal clause. This was addressed by implementing the RAG pipeline to ground the model's responses in factual context.

- **Future Work:**
    - Training a custom **Named Entity Recognition (NER)** model using a library like **spaCy** or **PyTorch** to automatically identify and tag key entities like names, dates, monetary values, and jurisdictions.
    - Adding support for more document formats, such as `.docx` and `.txt`.
    - Building a simple front-end with React or vanilla JavaScript to provide a user-friendly web interface for the service.

---

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement". Don't forget to give the project a star! Thanks again!

1.  **Fork** the Project
2.  Create your **Feature Branch** (`git checkout -b feature/AmazingFeature`)
3.  **Commit** your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  **Push** to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a **Pull Request**

---

## 👤 Contributor

- **Ayush Shukla** - *Project Lead & Developer* - [GitHub](https://github.com/technospes)

---

## 📄 License
This project is licensed under the MIT License.
