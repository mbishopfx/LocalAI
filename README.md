# LocalAI App

This repository contains the **LocalAI App**, a PyQt5-based application that integrates LangChain's Conversational Retrieval Chain with OpenAI's GPT models. The app allows users to interact with their data in natural language by training an AI on internal files within a selected directory.

![Screen Shot 2024-11-13 at 10 34 17 AM](https://github.com/user-attachments/assets/4f26b949-0858-4434-b813-da82e9ee857a)


---

## Features

- **File-Based AI Training**  
  Load a directory of files, and the AI is trained to retrieve and respond based on the data within the files.

- **Conversational Interface**  
  Interact with your AI by typing queries and receiving detailed, conversational responses.

- **Chat History Management**  
  View, toggle, and save chat history for future reference.

- **Streaming Responses**  
  Simulates real-time response streaming by displaying AI answers in chunks.

- **Customizable UI**  
  User-friendly design with styled components for better visual feedback.

---

## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/mbishopfx/LocalAI.git
   ```

2. **Install Dependencies**
   Use the provided `requirements.txt` to install the necessary Python packages:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Environment Variables**  
   Add your OpenAI API key and other configuration details in a `constants.py` file, including:  
   - `SYSTEM_MESSAGE`: Default system message for guiding the AI.
   - `OPENAI_API_KEY`: Your OpenAI API key.
   - `DEFAULT_MODEL`: Model to use (e.g., `gpt-4` or `gpt-3.5-turbo`).
   - `DEFAULT_HISTORY_FOLDER`: Directory for storing chat history.

---

## How to Use

1. **Run the App**  
   Launch the app by running the main script.

2. **Select a Directory**  
   On the first run, select the directory containing files you want the AI to train on.

3. **Ask Questions**  
   Enter a query in the input field and click "Generate" or press Enter to receive an AI-generated response.

4. **View Responses**  
   The AI's responses appear in the response display area. Chat history is visible in the toggleable history panel.

5. **Save and Review History**  
   Queries and responses are automatically saved as `.txt` files in the history folder.

---

## Key Components

### Conversational Retrieval Chain  
Uses LangChain's `ConversationalRetrievalChain` to retrieve relevant information from the loaded directory and provide detailed answers.

### DirectoryLoader  
Facilitates the loading and indexing of files from the user-selected directory.

### Streaming Responses  
Simulates real-time AI interaction by splitting responses into smaller chunks and displaying them progressively.

### PyQt5 UI  
The graphical interface provides a seamless way to interact with the AI, view chat history, and manage queries.

---

## Known Issues

- **Empty Query Warning**: A warning appears if you try to submit an empty query.
- **Folder Selection Error**: Ensure you select a valid folder with readable files.
- **API Key Issues**: Verify that your `OPENAI_API_KEY` is set correctly in `constants.py`.

---

## Contact

For questions or feedback, feel free to reach out at:  
**Email**: matt@bishopfx.org  
