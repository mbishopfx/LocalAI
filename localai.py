import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton, QFileDialog, QMessageBox, QDockWidget, QListWidget, QListWidgetItem
from PyQt5.QtCore import QTimer
from langchain_community.document_loaders import DirectoryLoader
from langchain.indexes import VectorstoreIndexCreator
from langchain.chains import ConversationalRetrievalChain
import openai
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from constants import SYSTEM_MESSAGE, OPENAI_API_KEY, DEFAULT_HISTORY_FOLDER, DEFAULT_MODEL, PROGRAM_NAME

# Explicitly set the API key (This is for some reason the only way we can get the script to pull the API)
openai.api_key = "copy your API key here..."

class ConversationalRetrievalApp(QWidget):
    def __init__(self):
        super().__init__()

        # Initialize UI components 
        self._instructions = QLabel(f'Welcome to {PROGRAM_NAME}. You can interact with your data by prompting a question below. This AI is trained on all your internal files within the directory selected.')
        self._query_input = QLineEdit()
        self._search_button = QPushButton('Generate')
        self._response_display = QTextEdit()
        self._loading_label = QLabel('')  # For loading feedback

        # Chat history components
        self.chat_history_widget = QListWidget()
        self.toggle_history_button = QPushButton("Toggle History")
        self.chat_history_visible = False  # Flag to toggle history visibility

        # Set individual styles for controls
        self._instructions.setStyleSheet("color: #d1d1d1; font-size: 16px;")
        self._query_input.setStyleSheet("background-color: #333; color: #fff; border: 1px solid #555; border-radius: 6px; padding: 5px; font-size: 14px;")
        self._search_button.setStyleSheet("background-color: #0078d4; color: #fff; border: none; border-radius: 6px; padding: 8px 16px; font-size: 14px;")
        self._response_display.setStyleSheet("background-color: #333;   color: #fff; border: 1px solid #555; border-radius: 6px; padding: 8px; font-size: 14px; min-height: 100px;")
        self._loading_label.setStyleSheet("color: #d1d1d1; font-size: 14px;")
        self.chat_history_widget.setStyleSheet("background-color: #444; color: #fff; font-size: 10px; border: none;")
        self.toggle_history_button.setStyleSheet("background-color: #0078d4; color: #fff; border: none; border-radius: 6px; padding: 8px 16px; font-size: 14px;")



        # Layouts
        main_layout = QVBoxLayout()
        input_layout = QVBoxLayout()

        input_layout.addWidget(self._instructions)
        input_layout.addWidget(self._query_input)
        input_layout.addWidget(self._search_button)
        input_layout.addWidget(self._loading_label)
        input_layout.addWidget(self._response_display)

        # Create a horizontal layout to combine input area and history area
        split_layout = QHBoxLayout()
        split_layout.addLayout(input_layout)
        split_layout.addWidget(self.toggle_history_button)

        main_layout.addLayout(split_layout)
        main_layout.addWidget(self.chat_history_widget)
        self.setLayout(main_layout)

        # Set event handlers
        self._search_button.clicked.connect(self._on_search_button_click)
        self._query_input.returnPressed.connect(self._on_query_input_key_release)
        self.toggle_history_button.clicked.connect(self.toggle_history)

        # Initialize the loader with the chosen directory
        self.initialize_loader()

        # To simulate streaming, we need a timer and a chunk counter
        self.stream_timer = QTimer(self)
        self.stream_timer.timeout.connect(self.update_response_display)
        self.chunk_counter = 0
        self.response_chunks = []

    def initialize_loader(self):
        try:
            # Prompt the user to select a directory
            folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")

            if folder_path:
                # Initialize the loader and chain
                self.loader = DirectoryLoader(folder_path)
                embeddings_model = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
                self.index = VectorstoreIndexCreator(embedding=embeddings_model).from_loaders([self.loader])
                self.chain = ConversationalRetrievalChain.from_llm(
                    llm=ChatOpenAI(model=DEFAULT_MODEL, openai_api_key=OPENAI_API_KEY),
                    retriever=self.index.vectorstore.as_retriever(search_kwargs={"k": 15}),
                )
                self.history_folder = os.path.join(folder_path, DEFAULT_HISTORY_FOLDER)
                os.makedirs(self.history_folder, exist_ok=True)
            else:
                QMessageBox.critical(self, "Error", "No folder selected. The application will now exit.")
                sys.exit()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to initialize the loader: {str(e)}")
            sys.exit()

    def _on_search_button_click(self):
        self._execute_query()

    def _on_query_input_key_release(self):
        self._execute_query()

    def _execute_query(self):
        query = self._query_input.text()
        if not query:
            QMessageBox.warning(self, "Warning", "Query cannot be empty.")
            return

        try:
            # Show loading message
            self._loading_label.setText("Loading... Please wait.")

            # Prepend system message to query
            full_query = f"{SYSTEM_MESSAGE} {query}"

            result = self.chain({"question": full_query, "chat_history": []})
            response = result['answer']
            self.response_chunks = self.chunk_response(response)  # Chunk the response

            self.chunk_counter = 0
            self._response_display.clear()  # Clear previous responses
            self.stream_timer.start(100)  # Update every 100ms

            # Display the query and response in chat history
            self.add_to_history(f"User: {query}")
            self.add_to_history(f"AI: {response}")

            # Save query and response to history
            self.save_to_history(full_query, response)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error during query execution: {str(e)}")

    def chunk_response(self, response):
        """Simulate streaming by splitting the response into chunks."""
        # Split the response into chunks (simulate "streaming" of data)
        chunk_size = 300  # Characters per chunk
        return [response[i:i + chunk_size] for i in range(0, len(response), chunk_size)]

    def update_response_display(self):
        """Update the display with the next chunk of the response."""
        if self.chunk_counter < len(self.response_chunks):
            self._response_display.append(self.response_chunks[self.chunk_counter])
            self.chunk_counter += 1
        else:
            self.stream_timer.stop()  # Stop the timer when all chunks are displayed
            self._loading_label.setText("")  # Hide loading message when done

    def save_to_history(self, query, response):
        try:
            # Generate timestamp for filename
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{timestamp}.txt"
            filepath = os.path.join(self.history_folder, filename)

            # Save query and response with metadata
            with open(filepath, 'w') as file:
                file.write(f"Query Time: {timestamp}\n")
                file.write(f"Query: {query}\n\n")
                file.write(f"Response: {response}\n")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save history: {str(e)}")

    def add_to_history(self, text):
        """Add a new item to the chat history."""
        item = QListWidgetItem(text)
        item.setTextAlignment(4)  # Align text to the left
        self.chat_history_widget.addItem(item)

    def toggle_history(self):
        """Toggle visibility of the chat history."""
        if self.chat_history_visible:
            self.chat_history_widget.hide()
            self.chat_history_visible = False
        else:
            self.chat_history_widget.show()
            self.chat_history_visible = True


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ConversationalRetrievalApp()
    window.setWindowTitle(PROGRAM_NAME)
    window.resize(700, 600)  # Resize window as needed
    window.show()
    sys.exit(app.exec_())
