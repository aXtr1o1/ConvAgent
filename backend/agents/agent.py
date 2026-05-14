from __future__ import annotations
import json
import logging
from backend.utils.utilities import openai_client as client
from config import azure_deployment
import re
from ingestion.retrieval.session_handler import get_active_session_for_conversation
from backend.agents.prompt import DECISION_AGENT_PROMPT, VALIDATION_AGENT_PROMPT, DCT_CODE_EXTRACTION_PROMPT, REPLY_AGENT_PROMPT, CASUAL_LLM_PROMPT
from backend.agents.metadata import DCT_METADATA, DCT_DATA
from ingestion.data.ingestion.embedding import get_embs
from ingestion.data.ingestion.retreival import connect_milvus
from pymilvus import Collection



logging.basicConfig(level=logging.INFO,format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger( __name__)

def decision_with_retrieval(conversation_hisotry, message, prior_list):
    decision = dct_code_decision_agent(conversation_hisotry, message, prior_list)
    if decision['status'] != 'success':
        return decision
    data = decision["data"]

    query = data.get("search_query","")
    dtc_code = data.get("filters",{}).get("dtc_code","")
    
    logger.info(f"Query: {query}")
    logger.info(f"DTC Code: {dtc_code}")

    connect_milvus()

    collection = Collection("dtc_embeddings")

    results = retrieve_from_milvus(collection, query, dtc_code, top_k=5)
    return {
        'status': 'success',
        'decision': data,
        "retrieved_steps": results
    }

def retrieve_from_milvus(collection, query, dtc_code=None, top_k=5):
    query_embs = get_embs([query])[0]

    collection.load()

    expr = None

    if dtc_code:
        expr = f"dtc_code == '{dtc_code}'"
    results = collection.search(
        data=[query_embs],
        anns_field="embedding",
        param={"metric_type": "IP", "params": {"nprobe": 10}},
        limit=top_k,
        expr=expr,   
        output_fields=["dtc_code", "step_number", "text"],
    )
    hits = []

    for hit in results[0]:
        hits.append({
            "score": float(hit.score),
            "dtc_code": hit.entity.get("dtc_code", ""),
            "step_number": hit.entity.get("step_number", ""),
            "text": hit.entity.get("text", ""),
        })
    return hits

def dct_code_extraction_agent(conversation_history: list[dict], message: str, prior_list: dict[list[dict[str,str]]])-> str:
    try:
        prompt = DCT_CODE_EXTRACTION_PROMPT.format(
            dtc_metadata = str(DCT_METADATA),
            conversation_history = conversation_history,
            message = message,
            previous_dtc_list = prior_list
        )

        response = client.chat.completions.create(
            model = azure_deployment,
            messages = [
                {"role":"system", "content": prompt},
                
            ],
            temperature = 0.7,
            max_tokens = 100,
            )
        logger.info(f"Response: {response.choices[0].message.content}")
        val = json.loads(response.choices[0].message.content.replace("json (","{").replace(")","}"))
        logger.info(f"DCT Code Extraction Agent: {val}")
        if not val.get("dtc_codes"):
            return {
                "status": "no_dtc",
                "data": {
                    "search_query": message,
                    "filters": {"dtc_code": "", "flow_type": None},
                    "confidence": 0.0
                }
            }
        logger.info(f"DCT Code Extraction Agent : {val}")
        
        return {"status": "success", "data": val}
    except Exception as e:
        logger.error(f"Error in DCT Code Extraction Agent: {e}")
        return {"status": "error", "message": str(e)}

def dct_code_decision_agent(conversation_history: list[dict], message: str, prior_list: dict[list[dict[str,str]]])-> str:
    try:
        if not prior_list:
            logger.info("No DTC found → casual mode")
            return {
                "status": "no_dtc",
                "data": {
                    "search_query": message,
                    "filters": {"dtc_code": "", "flow_type": None},
                    "confidence": 0.0
                }
            }

        min_dtc = min(prior_list.values(), key=lambda x: x['priority'])
        logger.info(f"Minimum DTC Code: {min_dtc}")
        dtc_info = [ dtc for dtc in DCT_DATA if dtc['dtc_code'] == min_dtc['code']]
        
        if not dtc_info:
            logger.info("DTC not in metadata → fallback")
            return {
                "status": "no_dtc",
                "data": {
                    "search_query": message,
                    "filters": {"dtc_code": min_dtc["code"], "flow_type": None},
                    "confidence": 0.5
                }
            }
        else:
            prompt = DECISION_AGENT_PROMPT.format(
                dtc_code = dtc_info,
                conversation_history = conversation_history,
                message = message,
            )
            response = client.chat.completions.create(
                model = azure_deployment,
                messages = [
                    {"role":"system", "content": prompt},
                ],
                temperature = 0.2,
                max_tokens = 300,
            )
            logger.info(f"Response: {response.choices[0].message.content}")
            val = json.loads(response.choices[0].message.content.replace("json(","{").replace(")","}"))
            logger.info(f"Val: {val}")
            val.setdefault("search_query", "")
            val.setdefault("filters", {})
            val["filters"].setdefault("dtc_code", min_dtc["code"])
            val["filters"].setdefault("flow_type", None)
            val.setdefault("confidence", 0.0)
            return {"status": "success", "data": val}   


    
    except Exception as e:
        logger.error(f"Error in DCT Code Decision Agent: {e}")
        return {
    "status": "error",
    "data": {
        "search_query": "",
        "filters": {"dtc_code": "", "flow_type": None},
        "confidence": 0.0
    },
    "message": str(e)
}



def reply_agent(conversation_history, message, retrieved_steps):
    try:
        context = "\n\n".join([f"DTC: {step['dtc_code']} | Step: {step['step_number']}: {step['text']}" for step in retrieved_steps])
        prompt = REPLY_AGENT_PROMPT.format(
            context= context,
            conversation_history= conversation_history,
            message= message,
        )
        response = client.chat.completions.create(
            model= azure_deployment,
            messages= [
                {"role":"system", "content": prompt},
            ],
            temperature= 0.2,

        )
        content = response.choices[0].message.content
        logger.info(f"Content: {content}")
        val = json.loads(
             content.replace("json (", "{").replace(")", "}")
        )
        logger.info(f"Reply Agent: {val}")

        return {
            "status": "success",
            "data": val,
        }

    except Exception as e:
        logger.error(f"Error in Reply Agent: {e}")
        return {
            "status": "error",
            "message":str(e)
        }


def casual_agent(conversation_history, message):
    try:
        prompt = CASUAL_LLM_PROMPT.format(
            conversation_history= conversation_history,
            message= message,
        )
        response = client.chat.completions.create(
                model=azure_deployment,
                messages=[
                    {"role": "system", "content": prompt},
                ],
                temperature=0.7,
            )
        return {
            "status": "success",
            "data": {
                "response": response.choices[0].message.content.strip(),
                "requires_user_input": False
            }
        }

    except Exception as e:
        logger.error(f"Casual Agent Error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }