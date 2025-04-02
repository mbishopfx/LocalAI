import os
import openai
import json
import hmac
import hashlib
import time
import re
import requests
import logging
import threading
import datetime
from functools import lru_cache
from io import BytesIO

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt import App
from dotenv import find_dotenv, load_dotenv
from flask import Flask, request, jsonify, abort

from langchain.chains import ConversationalRetrievalChain
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import DirectoryLoader
from langchain.indexes import VectorstoreIndexCreator
from langchain_openai import OpenAIEmbeddings

# For PDF processing
from PyPDF2 import PdfReader

# --------------------------
# Setup Logging
# --------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------------
# Environment & Credentials
# --------------------------
load_dotenv()  # Load environment variables from .env file

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
SLACK_BOT_USER_ID = os.getenv("SLACK_BOT_USER_ID")  # This is set after fetching

# Admin user IDs for role-based access (replace with your admin IDs)
ADMIN_USER_IDS = os.getenv("ADMIN_USER_IDS", "").split(",")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
openai.api_key = OPENAI_API_KEY

# --------------------------
# History Folder Setup
# --------------------------
# Replace this with the actual path to your History folder
HISTORY_FOLDER = os.getenv("HISTORY_FOLDER", "History")
if not os.path.exists(HISTORY_FOLDER):
    os.makedirs(HISTORY_FOLDER)

def get_today_history_file():
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    return os.path.join(HISTORY_FOLDER, f"history_{today_str}.txt")

def log_interaction(user_id, query, response):
    now = datetime.datetime.now().isoformat()
    log_file = get_today_history_file()
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"Timestamp: {now}\nUser: {user_id}\nQuery: {query}\nResponse: {response}\n{'-'*40}\n")
    except Exception as e:
        logger.error(f"Error logging interaction: {e}")

def summarize_history():
    log_file = get_today_history_file()
    if not os.path.exists(log_file):
        return "No history found for today."
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()
        summary_prompt = (
            "Analyze the following conversation history and provide a summary of the key questions asked, "
            "identify common themes, and highlight areas where additional training might be beneficial:\n\n" + content
        )
        summary = query_openai_model(summary_prompt, custom_pretext)
        return summary
    except Exception as e:
        logger.error(f"Error summarizing history: {e}")
        return "An error occurred while summarizing the history."

# --------------------------
# Initialize LangChain Components
# --------------------------
embeddings_model = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
# Path to your LocalAI directory (update if needed)
LOCALAI_DIR = "C:\\Users\\Mattb\\Desktop\\BishopFX Trade Server\\src\\LocalAI"

loader = DirectoryLoader(LOCALAI_DIR)
index = VectorstoreIndexCreator(embedding=embeddings_model).from_loaders([loader])

# Adjusted custom pretext for the LocalAI assistant
custom_pretext = (
    "You are the LocalAI assistant and are trained to help build sales pitches that are short and to the point as well as rebuttals. "
    "You know everything about the internal script and scope of the program and how we can help. "
    "When providing answers, please format your response using Slack's formatting syntax: "
    "- Use single asterisks (*) around text to make it bold. "
    "- Do not use Markdown headings like ###. "
    "- Instead of headings, use bold text on a new line. "
    "Avoid any formatting that is not supported by Slack.\n\n"
)

chain = ConversationalRetrievalChain.from_llm(
    llm=ChatOpenAI(model="gpt-4o-2024-05-13"),
    retriever=index.vectorstore.as_retriever(search_kwargs={"k": 20}),
)

# --------------------------
# Initialize Slack & Flask Apps
# --------------------------
app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

# --------------------------
# Usage Analytics & Caching
# --------------------------
usage_stats = {"queries": 0, "files_processed": 0, "errors": 0}

@lru_cache(maxsize=128)
def cached_query(query_text):
    result = chain({"question": custom_pretext + query_text, "chat_history": []})
    return result['answer']

def query_openai_model(input_text, custom_pretext, use_cache=False):
    try:
        usage_stats["queries"] += 1
        if use_cache:
            return cached_query(input_text)
        else:
            result = chain({"question": custom_pretext + input_text, "chat_history": []})
            return result['answer']
    except Exception as e:
        usage_stats["errors"] += 1
        logger.error(f"Error querying model: {e}")
        return "An error occurred while processing your query."

# --------------------------
# Re-indexing Functionality
# --------------------------
def reindex():
    global loader, index, chain
    try:
        loader = DirectoryLoader(LOCALAI_DIR)
        index = VectorstoreIndexCreator(embedding=embeddings_model).from_loaders([loader])
        chain = ConversationalRetrievalChain.from_llm(
            llm=ChatOpenAI(model="gpt-4o-2024-05-13"),
            retriever=index.vectorstore.as_retriever(search_kwargs={"k": 20}),
        )
        logger.info("Index re-built successfully.")
        return True, "Index has been re-built."
    except Exception as e:
        usage_stats["errors"] += 1
        logger.error(f"Error during re-indexing: {e}")
        return False, f"Error during re-indexing: {e}"

# --------------------------
# Formatting for Slack Output
# --------------------------
def format_for_slack(text):
    text = re.sub(r'^### (.*)', r'*\1*', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)
    return text

# --------------------------
# File Processing (Text & PDF Support)
# --------------------------
def process_file(file_url, mimetype):
    try:
        headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
        response = requests.get(file_url, headers=headers)
        if response.status_code != 200:
            logger.error("Failed to download file.")
            return None, "Failed to download the file."
        if "pdf" in mimetype:
            pdf_bytes = BytesIO(response.content)
            reader = PdfReader(pdf_bytes)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text, None
        elif "text" in mimetype:
            return response.text, None
        else:
            return None, "File type not supported for analysis."
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        usage_stats["errors"] += 1
        return None, f"Error processing file: {e}"

# --------------------------
# Role-Based Access Check
# --------------------------
def is_user_admin(user_id):
    return user_id in ADMIN_USER_IDS

# --------------------------
# Helper: Get Bot User ID (with caching)
# --------------------------
_bot_user_id = None
def get_bot_user_id():
    global _bot_user_id
    if _bot_user_id:
        return _bot_user_id
    try:
        slack_client = WebClient(token=SLACK_BOT_TOKEN)
        response = slack_client.auth_test()
        _bot_user_id = response["user_id"]
        return _bot_user_id
    except SlackApiError as e:
        logger.error(f"Error fetching bot user id: {e}")
        return None

# --------------------------
# Slack Event: app_mention
# --------------------------
@app.event("app_mention")
def handle_mentions(body, say):
    try:
        event = body.get("event", {})
        text = event.get("text", "")
        user_id = event.get("user", "unknown")
        bot_mention = f"<@{get_bot_user_id()}>"
        text = text.replace(bot_mention, "").strip()

        # Check for re-index command (admin-only)
        if text.lower() in ["reindex", "re-index", "update index"]:
            if not is_user_admin(user_id):
                say("You do not have permission to perform this action.")
                return
            success, message = reindex()
            say(message)
            log_interaction(user_id, text, message)
            return

        # Process as a normal query
        response_text = query_openai_model(text, custom_pretext)
        formatted_response = format_for_slack(response_text)
        say(formatted_response)
        log_interaction(user_id, text, response_text)
    except Exception as e:
        logger.error(f"Error handling app mention: {e}")
        usage_stats["errors"] += 1
        say("An error occurred processing your request.")

# --------------------------
# Slack Event: file_shared
# --------------------------
@app.event("file_shared")
def handle_file_shared(event, say):
    try:
        file_id = event.get("file_id")
        slack_client = WebClient(token=SLACK_BOT_TOKEN)
        file_info_response = slack_client.files_info(file=file_id)
        file_info = file_info_response.get("file", {})
        file_url = file_info.get("url_private_download")
        mimetype = file_info.get("mimetype", "")
        user_id = file_info.get("user", "unknown")
        if not file_url:
            say("Could not retrieve the file URL.")
            return
        file_content, error = process_file(file_url, mimetype)
        if error:
            say(error)
            return
        usage_stats["files_processed"] += 1
        analysis_prompt = "Please analyze the following file content:\n" + file_content
        analysis_result = query_openai_model(analysis_prompt, custom_pretext)
        formatted_response = format_for_slack(analysis_result)
        say(formatted_response)
        log_interaction(user_id, f"File analysis: {file_url}", analysis_result)
    except SlackApiError as e:
        logger.error(f"Slack API error: {e}")
        usage_stats["errors"] += 1
        say("Error retrieving file info.")
    except Exception as ex:
        logger.error(f"Error processing file shared event: {ex}")
        usage_stats["errors"] += 1
        say(f"An error occurred while processing the file: {ex}")

# --------------------------
# Slash Command: /analyze
# Opens a modal to accept either a file URL or text for analysis.
# --------------------------
@app.command("/analyze")
def handle_analyze_command(ack, body, client):
    ack()  # Acknowledge the command
    trigger_id = body.get("trigger_id")
    modal_view = {
        "type": "modal",
        "callback_id": "analyze_modal",
        "title": {"type": "plain_text", "text": "Analyze File/Query"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "input_block",
                "label": {"type": "plain_text", "text": "Enter text or file URL for analysis:"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "input_value",
                    "multiline": True
                }
            }
        ]
    }
    try:
        client.views_open(trigger_id=trigger_id, view=modal_view)
    except SlackApiError as e:
        logger.error(f"Error opening modal: {e}")

@app.view("analyze_modal")
def handle_modal_submission(ack, body, client, view):
    ack()
    user_id = body.get("user", {}).get("id", "unknown")
    input_value = view["state"]["values"]["input_block"]["input_value"]["value"]
    if re.match(r'https?://', input_value):
        file_content, error = process_file(input_value, "text")
        if error:
            response_text = error
        else:
            analysis_prompt = "Please analyze the following file content:\n" + file_content
            response_text = query_openai_model(analysis_prompt, custom_pretext)
    else:
        response_text = query_openai_model(input_value, custom_pretext)
    formatted_response = format_for_slack(response_text)
    try:
        client.chat_postEphemeral(
            channel=body["view"].get("private_metadata", user_id),
            user=user_id,
            text=formatted_response
        )
        log_interaction(user_id, input_value, response_text)
    except SlackApiError as e:
        logger.error(f"Error posting ephemeral message: {e}")

# --------------------------
# Slash Command: /status (Usage Analytics)
# --------------------------
@app.command("/status")
def handle_status_command(ack, body, client):
    ack()
    user_id = body.get("user_id")
    if not is_user_admin(user_id):
        client.chat_postEphemeral(channel=body.get("channel_id"), user=user_id, text="You do not have permission to view status.")
        return
    status_message = (
        f"*Usage Statistics:*\n"
        f"Queries processed: {usage_stats['queries']}\n"
        f"Files processed: {usage_stats['files_processed']}\n"
        f"Errors encountered: {usage_stats['errors']}"
    )
    client.chat_postEphemeral(channel=body.get("channel_id"), user=user_id, text=status_message)

# --------------------------
# Slash Command: /summarize (History Summary)
# --------------------------
@app.command("/summarize")
def handle_summarize_command(ack, body, client):
    ack()
    user_id = body.get("user_id")
    if not is_user_admin(user_id):
        client.chat_postEphemeral(channel=body.get("channel_id"), user=user_id, text="You do not have permission to view summary.")
        return
    summary = summarize_history()
    client.chat_postEphemeral(channel=body.get("channel_id"), user=user_id, text=format_for_slack(summary))

# --------------------------
# Automated Alerts (Background Thread)
# --------------------------
def automated_alerts():
    while True:
        time.sleep(3600)  # Every hour; adjust as needed
        try:
            alert_message = "Automated Alert: Check out the latest high-impact news updates."
            slack_client = WebClient(token=SLACK_BOT_TOKEN)
            # Replace "#alerts" with your designated channel name
            slack_client.chat_postMessage(channel="#alerts", text=alert_message)
        except Exception as e:
            logger.error(f"Error sending automated alert: {e}")

alert_thread = threading.Thread(target=automated_alerts, daemon=True)
alert_thread.start()

# --------------------------
# Flask Route for Slack Events
# --------------------------
@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

SLACK_BOT_USER_ID = get_bot_user_id()
print(f"Bot User ID: {SLACK_BOT_USER_ID}")

if __name__ == "__main__":
    flask_app.run(port=3000)
