from config import azure_deployment
from backend.utils.utilities import openai_client as client


# ── System prompts ────────────────────────────────────────────────────────────

DIAGNOSTIC_SYSTEM_PROMPT = """You are an expert automotive diagnostic assistant 
specializing in DTC (Diagnostic Trouble Code) analysis.

When answering questions:
- Use ONLY the provided diagnostic knowledge context
- Be specific about fault codes, symptoms, and repair steps
- If the context mentions related codes, mention them
- Structure your answer clearly with causes and recommended actions
- If you cannot find relevant information in the context, say so clearly
- Never guess or make up diagnostic procedures

Always prioritize safety warnings when present in the context."""


GENERAL_SYSTEM_PROMPT = """You are a helpful automotive assistant. 
Answer questions clearly and concisely.
If asked about specific fault codes or diagnostics, let the user know 
they can share the DTC code for a detailed step-by-step diagnosis."""


def generate_bot_reply(
    conversation_history: list,
    has_rag_context: bool = False
) -> str:
    """
    Takes conversation history and returns assistant reply.
    Uses diagnostic prompt when RAG context is present,
    general prompt for casual conversation.
    """
    system_prompt = DIAGNOSTIC_SYSTEM_PROMPT if has_rag_context else GENERAL_SYSTEM_PROMPT

    messages = [
        {"role": "system", "content": system_prompt}
    ] + conversation_history

    response = client.chat.completions.create(
        model=azure_deployment,
        messages=messages
    )
    return response.choices[0].message.content.strip()


def generate_bot_reply_stream(
    conversation_history: list,
    has_rag_context: bool = False
):
    """
    Streams the assistant reply token by token.
    """
    system_prompt = DIAGNOSTIC_SYSTEM_PROMPT if has_rag_context else GENERAL_SYSTEM_PROMPT

    messages = [
        {"role": "system", "content": system_prompt}
    ] + conversation_history

    response = client.chat.completions.create(
        model=azure_deployment,
        messages=messages,
        stream=True
    )

    for chunk in response:
        if chunk.choices:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content


def generate_title(user_message: str) -> str:
    response = client.chat.completions.create(
        model=azure_deployment,
        messages=[
            {
                "role": "system",
                "content": (
                    "Generate a short 4-6 word conversation title based on the user message. "
                    "If the message is a greeting like 'hi', 'hello', 'hey', 'how are you', "
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