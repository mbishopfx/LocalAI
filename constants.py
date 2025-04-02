# constants.py

import os
# Company Or Brand Name
PROGRAM_NAME = 'LocalAI'

# OpenAI API Key
OPENAI_API_KEY = "copy your api here"

# Custom system message
SYSTEM_MESSAGE = 'You are a powerful AI assistant tasked with performing at your smartest and most realistic, human manner:'

# Default temperature for OpenAI API
DEFAULT_TEMPERATURE = 0.2

# Default directory for history
DEFAULT_HISTORY_FOLDER = "History"

# Default model for ConversationalRetrievalChain
DEFAULT_MODEL = "gpt-4o-2024-05-13"   

# Stylesheet for the application
APP_STYLESHEET = '''
QWidget {
    background-color: #1e1e1e;  /* Darker background */
    color: #d1d1d1;  /* Light text */
    font-family: "Segoe UI", "Arial", sans-serif;
}
QLineEdit {
    background-color: #333;  /* Darker background */
    color: #fff;  /* White text */
    border: 1px solid #555;  /* Lighter border */
    border-radius: 6px;  /* Rounded corners */
    padding: 5px;
    font-size: 14px;
}
QPushButton {
    background-color: #0078d4;  /* Blue button background */
    color: #fff;
    border: none;
    border-radius: 6px;  /* Rounded corners */
    padding: 8px 16px;
    font-size: 14px;
}
QPushButton:hover {
    background-color: #0062a1;  /* Darker blue when hovered */
}
QTextEdit {
    background-color: #333;  /* Dark background */
    color: #fff;  /* White text */
    border: 1px solid #555;
    border-radius: 6px;
    padding: 8px;
    font-size: 14px;
    min-height: 100px;
}
QLabel {
    font-size: 14px;
    margin-bottom: 10px;
}
QControlText {
    background-color: #2c2c2c;
    color: #fff;
    padding: 5px;
}
'''
