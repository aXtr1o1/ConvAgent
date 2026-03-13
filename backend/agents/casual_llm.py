from config import azure_deployment
from backend.utils.utilities import openai_client as client



def generate_bot_reply(conversation_history: list) -> str:
    """
    Takes the full conversation history as a list of
    {"role": "user"/"assistant", "content": "..."} dicts
    and returns the assistant's reply string.
    """
    messages = [
        {"role": "system", "content": "You are a helpful conversational AI assistant."}
    ] + conversation_history

    response = client.chat.completions.create(
        model=azure_deployment,
        messages=messages
    )
    return response.choices[0].message.content.strip()

def generate_bot_reply_stream(conversation_history: list):
    """
    Streams the assistant reply token by token.
    Yields each chunk as it arrives from Azure OpenAI.
    """
    messages = [
        {"role": "system", "content": "You are a helpful conversational AI assistant."}
    ] + conversation_history

    response = client.chat.completions.create(
        model=azure_deployment,
        messages=messages,
        stream=True  # ← this is what enables streaming
    )

    for chunk in response:
        if chunk.choices:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content  # ← sends one small piece at a time


def generate_title(user_message: str) -> str:
    """
    Generate a short 4-6 word title from the user message.
    If the message is a greeting or too vague, return 'New Conversation'
    so the next message gets another attempt.
    """
    response = client.chat.completions.create(
        model=azure_deployment,
        messages=[
            {
                "role": "system",
                "content": (
                    "Generate a short 4-6 word conversation title based on the user message. "
                    "If the message is a greeting like 'hi', 'hello', 'hey', 'how are you', 'good morning', "
                    "or is too short or vague to make a meaningful title from, "
                    "return exactly the text: New Conversation "
                    "Do not add quotes, punctuation, or explanation. Return only the title."
                )
            },
            {"role": "user", "content": user_message}
        ],
        max_tokens=20
    )
    return response.choices[0].message.content.strip().strip('"').strip("'")