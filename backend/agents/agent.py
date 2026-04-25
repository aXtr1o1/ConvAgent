from __future__ import annotations
import json
import logging
from backend.utils.utilities import openai_client as client
from config import azure_deployment
import re
from ingestion.retrieval.session_handler import get_active_session_for_conversation
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 1 — DECISION AGENT
# ══════════════════════════════════════════════════════════════════════════════
DECISION_AGENT_PROMPT = """
You are a diagnostic routing and execution agent for an automotive fault code assistant system.

Your job has TWO MODES:

1. ACTIVE DIAGNOSTIC EXECUTION (HIGHEST PRIORITY)
2. NORMAL ROUTING (ONLY if no active session)

────────────────────────────────────────
🚨 MODE 1: ACTIVE DIAGNOSTIC EXECUTION
────────────────────────────────────────

If ACTIVE_DIAGNOSTIC_CONTEXT is provided and NOT "NONE":

You are executing a diagnostic step — NOT routing.

INPUTS:
- ACTIVE_DIAGNOSTIC_CONTEXT:
    - current_dtc_code
    - parent_dtc_code (can be null)
    - step_data:
        - question
        - yes_action
        - no_action

────────────────────────
STEP EXECUTION RULES
────────────────────────

1. Interpret USER MESSAGE:

- "yes", "ok", "done", "checked", "working" → YES
- "no", "not working", "failed", "issue persists" → NO
- "cancel", "stop", "exit", "abort" → CANCEL

2. Execute:

IF YES → follow yes_action  
IF NO → follow no_action  

3. CANCEL RULE:

If user indicates cancel:
    - intent = "cancel"
    - dtc_code = current_dtc_code
    - go_to_parent = false

4. DTC FLOW CONTROL (CRITICAL)

Each session maintains:
- current_dtc_code
- parent_dtc_code

You MUST determine flow direction.

────────────────────────
FORWARD FLOW (CHILD DTC)
────────────────────────

If action contains:
    "Diagnose <NEW_DTC_CODE>"

Then:
    - intent = "start_session"
    - dtc_code = NEW_DTC_CODE
    - go_to_parent = false

────────────────────────
BACKTRACK FLOW (PARENT DTC)
────────────────────────

If action indicates returning such as:
    - "return to parent"
    - "go back"
    - "previous step"
    - "resume previous DTC"

AND parent_dtc_code is NOT null:

Then:
    - intent = "continue_session"
    - dtc_code = parent_dtc_code
    - go_to_parent = true

IMPORTANT:
- ONLY go back if parent_dtc_code exists
- NEVER guess parent DTC

────────────────────────
NORMAL CONTINUE
────────────────────────

If no DTC switch is mentioned:

    - intent = "continue_session"
    - dtc_code = current_dtc_code
    - go_to_parent = false

5. BACKTRACK PRIORITY RULE

If NO action implies failure AND includes return instruction:

→ PRIORITIZE going back to parent DTC over continuing current flow

6. STRICT EXECUTION RULES

- ALWAYS execute yes_action / no_action
- NEVER ignore action
- NEVER default blindly
- NEVER stay on same DTC if action says to switch
- MODE 1 overrides everything

────────────────────────
OUTPUT (MODE 1)
────────────────────────

Return STRICT JSON:

{
  "route": "diagnostic",
  "tool": "supabase",
  "intent": "start_session" | "continue_session" | "cancel",
  "dtc_code": "string",
  "go_to_parent": true | false,
  "confidence": 0.9-1.0,
  "reason": "forward flow | backtrack | step execution"
}

────────────────────────────────────────
🧠 MODE 2: NORMAL ROUTING (NO ACTIVE SESSION ONLY)
────────────────────────────────────────

ONLY apply this if ACTIVE_DIAGNOSTIC_CONTEXT = NONE

1. CASUAL:

- greetings
- vague problems

→ route: "casual"
→ tool: "none"
→ intent: "continue_session"
→ dtc_code: ""
→ go_to_parent: false

2. SUPABASE (DIAGNOSTIC START):

If user:
- provides DTC code
- or asks for diagnosis

→ route: "diagnostic"
→ tool: "supabase"
→ intent: "start_session"
→ dtc_code: extracted DTC
→ go_to_parent: false

────────────────────────
🧠 DTC DETECTION
────────────────────────

Detect patterns:
- P#### 
- P####-##

Extract EXACT code

Valid DTC codes (ONLY these allowed):
    P1194
    P1629-00
    P2452
    P2452-12
    P245E
    P2463-00

Rules:
- If close match in conversation → pick highest confidence match
- Only return DTC if ≥ 90% confident
- Else return empty string

────────────────────────
🚫 STRICT RULES
────────────────────────

- MODE 1 ALWAYS overrides MODE 2
- NEVER apply CASUAL in active session
- NEVER ignore step actions
- NEVER guess parent DTC
- ALWAYS respect flow direction
- ALWAYS return STRICT JSON
- go_to_parent MUST be explicitly set

────────────────────────
📦 FINAL OUTPUT FORMAT
────────────────────────

{
  "route": "casual" | "diagnostic",
  "tool": "none" | "supabase",
  "intent": "start_session" | "continue_session" | "cancel" | "qa",
  "dtc_code": "string",
  "go_to_parent": true | false,
  "confidence": 0.0-1.0,
  "reason": "one line"
}
"""
def parse_decision_context(active_session) -> dict:
    try:
        raw = active_session.get("decision_context","{}")
        return json.loads(raw)
    except Exception as e:
        print(f"Error parsing decision context: {e}")
        return {}
def current_step(active_session) -> dict:
    context= parse_decision_context(active_session)
    steps = context.get("steps",[])
    try:
        current_step = steps[int(active_session.get("current_step",0))]
        

    except Exception as e:
        print(f"Error getting current step: {e}")
        current_step = steps[0]
    print(f"Current step: {type(current_step)} {current_step}")
    print(f"Type of Steps: {type(steps)}")
    
    if 0 < int(active_session.get("current_step",0)) < len(steps):
        return {
            "dtc_code": context.get("dtc_code",""),
            "step_index":int(active_session.get("current_step",0)),
            "step_data": current_step,
            "total_steps": len(steps)
        }
    return {
        "dtc_code": context.get("dtc_code",""),
        "step_index":0,
        "step_data": steps[0],
        "total_steps": len(steps)
    }

def run_decision_agent(
    message: str,
    has_active_session: bool = False,
    conversation_history: list = None,
    supabase_tool=None,
  
    conversation_id: str = None
) -> dict:
    """
    Classifies intent, calls the appropriate tool, and returns a unified dict:
      {
        "route":       "casual" | "diagnostic",
        "tool":        "none" | "supabase",
        "confidence":  float,
        "reason":      str,
        "raw_context": str,
        "source_type": "casual" | "supabase" ,
        "db_used":     "llm_only" | "supabase",
        "sources":     list,
      }

    KEY INVARIANT: if has_active_session is True the tool is forced to
    "supabase" before the LLM even runs — this prevents any mis-classification
    of short answers like "yes" / "no" from breaking session flow.
    """

    # ── Step 1: session hard-override ────────────────────────────────────────
    # An active session means the user is mid-diagnosis. Short replies like
    # "yes", "no", "ok" must ALWAYS feed the session handler, never casual.
    active_session = None
    session_context = None

    if has_active_session:
        active_session = get_active_session_for_conversation(conversation_id)
        if active_session:
            session_context = current_step(active_session)
            
            print(f"Active session context: {session_context}")
    if conversation_history is None:
        conversation_history = []
    
    
    print("Active session:", session_context)
    intent="qa"
    dtc_code = None
    system_prompt = DECISION_AGENT_PROMPT

    active_context_block = "NONE"

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "system",
            "content": f"ACTIVE_DIAGNOSTIC_CONTEXT:\n{session_context}"
        },
        {
            "role": "system",
            "content": f"CONVERSATION_HISTORY:\n{json.dumps(conversation_history)}"
        },
        {"role": "user", "content": message}
    ]

        # ── Step 2: LLM classification (no active session) ────────────────
    print(f"Messages: {messages}")
    try:
        response = client.chat.completions.create(
            model=azure_deployment,
            messages=messages,
            temperature=0.1,
            max_tokens=150,
            response_format={"type": "json_object"} 
        )
        print(f"Response: {response}")
        raw      = response.choices[0].message.content
        match = re.search(r"\{.*\}", raw, re.DOTALL)

        if not match:
            raise ValueError(f"Decision agent response is not valid JSON: {raw}")
        decision_json = match.group(0)
        decision = json.loads(decision_json)
        print(f"Decisions: {decision}")
    except Exception as e:
        logger.error("Decision Agent classification failed: %s", e)
        decision = {}

    route      = decision.get("route", "casual")
    tool       = decision.get("tool", "none")
    confidence = decision.get("confidence", 0.5)
    reason     = decision.get("reason", "fallback")
    intent     = decision.get("intent", "qa")
    dtc_code   = decision.get("dtc_code")
    parent_bool = decision.get("go_to_parent", False)
    # ── Step 3: execute the selected tool ────────────────────────────────────
    if has_active_session :
        tool = "supabase"
        route = "diagnostic"
        if intent == "start_session" and dtc_code:
            reason = "switching to new DTC during active session"
        elif intent == "cancel":
            reason = "user wants to cancel the session"
        else:
            intent="continue_session"

            reason = "active session — routing to supabase for session continuity"
    raw_context = ""
    sources     = []

    if tool == "supabase":
        raw_context, sources = _call_supabase_tool(message, supabase_tool,intent,dtc_code,parent_bool)
        
        
        return {
                "route": "diagnostic", "tool": "supabase",
                "confidence": confidence, "reason": reason,
                "raw_context": raw_context, "source_type": "supabase",
                "db_used": "supabase", "sources": sources,
                
            }
     
        
    

    # ── Casual / fallback ─────────────────────────────────────────────────────
    return {
        "route": "casual", "tool": "none",
        "confidence": confidence, "reason": reason,
        "raw_context": "", "source_type": "casual",
        "db_used": "llm_only", "sources": [],
    }

# ── Internal tool callers ─────────────────────────────────────────────────────

def _call_supabase_tool(message: str, supabase_tool,intent=None, dtc_code=None, parent_bool=False) :
    """
    Calls the Supabase session tool (sync wrapper).
    Returns (raw_context, sources).

    IMPORTANT: supabase_tool must be a plain synchronous callable.
    Never wrap handle_diagnostic_routing with asyncio.run() here —
    FastAPI's threadpool already has a running event loop, which causes
    'RuntimeError: This event loop is already running'.
    The _make_supabase_tool factory in conversations.py handles this.

    TYPE ERROR NOTE: if session_handler.advance_session raises
    '>= not supported between str and int', the fix is in session_handler.py:
        current_step = int(session.get("current_step", 0))
    Supabase returns JSON integers as strings when the column type is text.
    """
    try:
        if supabase_tool is None:
            return "", []
        result = supabase_tool(message,intent=intent,dtc_code=dtc_code, parent_bool=parent_bool) #this is supposed to be else statements
        if result:
            return (
                result,
                [],
               
            )

        return "", []
    except Exception as e:
        logger.error("Supabase tool call failed: %s", e, exc_info=True)
        return "", []




CASUAL_AGENT_PROMPT = """
You are a friendly and professional automotive diagnostic assistant.

Your primary goal:

* Guide the user to provide a valid DTC (Diagnostic Trouble Code)
* Use the Knowledge Base (KB) to give accurate, structured diagnostics
* Ask intelligent probing questions when information is incomplete
* NEVER hallucinate or invent diagnostics

---

## KNOWN DTC CONTEXT (KB AWARENESS)

DTC: P2463-00
Description: DPF soot load Stage 2 (> 8.5 g/L)
System: Exhaust After-Treatment / DPF

⚠️ CRITICAL RULE:
P2463 diagnosis is NOT valid unless ALL Primary Error Codes are checked first.

PRIMARY ERROR CODES:

Category 1 — Estimation Wrong:

* P245E-11 → Sensor voltage too LOW (<0.249V)
* P2452-12 → Sensor voltage too HIGH (>4.75V)
* P245E-1F → Pressure not zero at engine OFF (>1.5 kPa)

Category 2 — Soot Load Increased:

* P1194-00 → High soot load (>9 g/L)
* P2459-00 → Frequent regeneration
* P24A2-00 → Regen not reducing soot
* P1629-00 → Regen inhibited

These directly affect soot calculation and MUST be resolved first.

---

## BEHAVIOR LOGIC

1. IF USER PROVIDES NO DTC

DO NOT DIAGNOSE.

Instead, probe intelligently:

* Ask symptom-based question:
  "Can you describe the issue in more detail? (warning light, smoke, power loss, etc.)"

* Ask DTC-focused question (PRIORITY):
  "Do you have a fault code (DTC) from a scan tool? That will help me give an accurate diagnosis."

* If issue hints at DPF (smoke, regen, power loss), ask:
  "Have you noticed frequent regeneration or warning lights related to the exhaust system?"

---

2. IF USER MENTIONS P2463 OR SIMILAR

Respond in structured way:

Acknowledge:
"This indicates a high soot load condition in the DPF system."

⚠️ Immediately enforce dependency:
"Before diagnosing this, we MUST check if any primary error codes are active."

Ask probing questions:

* "Do you also see any of these codes: P245E-11, P2452-12, P245E-1F, P1194, P2459, P24A2, or P1629?"
* "Was this code triggered after frequent regeneration or poor vehicle performance?"

---

3. ONLY IF USER CONFIRMS NO PRIMARY CODES

Then provide structured info:

* Overview (what P2463 means)

* Impact:

  * Risk of DPF blockage
  * Possible thermal damage
  * Ineffective regeneration

* Possible Causes:

  * High soot accumulation
  * Sensor pipe blockage/leak
  * Exhaust leak
  * Engine producing excess soot

* Then give HIGH-LEVEL diagnostic flow:

  * Check DPF pressure system (hoses, leaks)
  * Check related sensors
  * Verify soot levels via scan tool

⚠️ DO NOT jump into step-by-step repair unless explicitly asked

---

4. IF USER PROVIDES PRIMARY ERROR CODE

Switch context immediately:
→ Focus on that code first
→ Ignore P2463 until resolved

---

5. SAFETY RULES

* NEVER skip primary error code validation
* NEVER hallucinate steps not in KB
* NEVER assume sensor values unless provided
* ALWAYS ask before diagnosing if data is incomplete

---

GOAL

Drive conversation like this:
User Issue → Ask DTC → Detect P2463 → Enforce Primary Codes → Probe → Then Diagnose

---

TONE

* Friendly
* Clear
* Slightly guiding (like a technician)
* Not overly verbose unless needed

"""


def run_casual_agent(conversation_history: list) -> str:
    """
    Agent 2 — Handles casual conversation.
    Returns the assistant reply string.
    """
    try:
        messages = [
            {"role": "system", "content": CASUAL_AGENT_PROMPT}
        ] + conversation_history

        response = client.chat.completions.create(
            model=azure_deployment,
            messages=messages,
            max_tokens=300,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error("Casual agent failed: %s", e)
        return (
            "Hello! I'm here to help with automotive diagnostics. "
            "Share a fault code for a detailed step-by-step diagnosis."
        )


def run_casual_agent_stream(conversation_history: list):
    """Agent 2 — Streaming version for WebSocket."""
    messages = [
        {"role": "system", "content": CASUAL_AGENT_PROMPT}
    ] + conversation_history

    response = client.chat.completions.create(
        model=azure_deployment,
        messages=messages,
        stream=True,
        temperature=0.7
    )
    for chunk in response:
        if chunk.choices:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content



REPLY_AGENT_PROMPT = """You are an automotive diagnostic reply specialist.

Your job is to take raw data retrieved from a database or tool and format
it into a clear, concise, helpful response for a vehicle technician or owner.

You also have access to the conversation history to maintain context.

FORMATTING RULES: 


1. For diagnostic session responses (Supabase):
   - Present the current step clearly and concisely
   - Make the YES/NO instruction bold and prominent
   - Include what the expected result should be
   - Keep the technician focused on one step at a time
   - If fault is resolved, clearly state what was found and what to do

2. For resolution/escalation messages:
   - Clearly state whether fault was found or all checks passed
   - Give the repair action or escalation step prominently
   - Remind to clear fault codes and verify after repair

CRITICAL — Out of scope fallback:
If the knowledge base data provided does NOT contain relevant information
to answer the user's question, or if the data seems unrelated to what
the user asked, respond with ONLY this message:
"I'm sorry, I don't have specific information about that in my current
knowledge base. For accurate diagnosis, please share your fault code
(e.g. P2463-00) or consult your vehicle's service manual."
Do NOT attempt to answer from general knowledge — only use what is provided.

ALWAYS:
- Be technically accurate
- Use only what is provided — do not add information not in the context
- End every diagnostic step with:
   Reply YES if the check passes |  Reply NO if it fails
- Keep responses readable on a small screen
"""


def run_reply_agent(
    raw_context: str,
    user_message: str,
    conversation_history: list,
    source_type: str,
) -> str:
    """
    Agent 3 — Formats the final response for the frontend.

    raw_context:          raw data from Supabase tool
    user_message:         original user message for context
    conversation_history: past messages for continuity
    source_type:          "supabase" | "casual"
    """
    # Casual responses come from Casual Agent already formatted
    if source_type == "casual":
        return raw_context

    source_label = {
        
        "supabase": "DIAGNOSTIC SESSION DATA (retrieved from structured DB):",
    }.get(source_type, "DATA:")

    formatting_instructions = {
        
        "supabase": {
            "instructions": (
                "Format this diagnostic session step clearly for a technician. "
                "Make YES/NO instructions bold and prominent. "
                "One step at a time — keep it focused."
            ),
            "raw_contents": raw_context,"Past Chunks":conversation_history[-1]
        },
    }.get(source_type, "Format this response clearly and concisely.")

    # Build recent history summary for continuity
    recent = conversation_history[-4:] if conversation_history else []
    history_text = "\n".join([
        f"{m['role'].upper()}: {m['content'][:150]}"
        for m in recent
    ])

    try:
        messages = [
            {"role": "system", "content": REPLY_AGENT_PROMPT},
            {
                "role": "user",
                "content": (
                    f"CONVERSATION HISTORY (for context):\n{history_text}\n\n"
                    f"USER MESSAGE: {user_message}\n\n"
                    f"{source_label}\n{raw_context}\n\n"
                    f"INSTRUCTION: {formatting_instructions}"
                )
            }
        ]

        response = client.chat.completions.create(
            model=azure_deployment,
            messages=messages,
            max_tokens=600,
            temperature=0.3
        )
        print(f"Reply agent raw response: {response}")
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error("Reply agent failed: %s", e)
        return raw_context


def run_reply_agent_stream(
    raw_context: str,
    user_message: str,
    source_type: str,
    conversation_history: list = [],
):
    """Agent 3 — Streaming version for WebSocket."""
    if source_type == "casual":
        yield raw_context
        return

    source_label = {
        
        "supabase": "DIAGNOSTIC SESSION DATA:",
    }.get(source_type, "DATA:")

    formatting_instructions = {
       
        "supabase": {"instruction":"Format this diagnostic step clearly. Make YES/NO prominent.","previous_knowledge":""},
    }.get(source_type, "Format clearly.")

    recent = conversation_history[-4:] if conversation_history else []
    history_text = "\n".join([
        f"{m['role'].upper()}: {m['content'][:150]}"
        for m in recent
    ])

    messages = [
        {"role": "system", "content": REPLY_AGENT_PROMPT},
        {
            "role": "user",
            "content": (
                f"CONVERSATION HISTORY:\n{history_text}\n\n"
                f"USER MESSAGE: {user_message}\n\n"
                f"{source_label}\n{raw_context}\n\n"
                f"INSTRUCTION: {formatting_instructions}"
            )
        }
    ]

    response = client.chat.completions.create(
        model=azure_deployment,
        messages=messages,
        stream=True,
        temperature=0.3
    )
    for chunk in response:
        if chunk.choices:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content