import pytest
import json
from backend.agents.agent import dct_code_extraction_agent, dct_code_decision_agent


def convert_to_prior_list(llm_output):
    dtc_list = llm_output.get("dtc_codes")

    if not dtc_list:
        return {}

    return {
        f"dtc{i+1}": dtc
        for i, dtc in enumerate(dtc_list)
    }


conversation_history = [
        {"role": "user", "content": "Vehicle showing DPF issue"},
    {"role": "assistant", "content": "Please provide the DTC code"},
    {"role": "user", "content": "P245E-11 is active"},
    {"role": "assistant", "content": "Proceeding with diagnostics"},
    {"role": "user", "content": "yes"}
]

valid_prior_list = {
        "dtc1": {"code": "P245E-11", "priority": 1},
    "dtc2": {"code": "P2452-12", "priority": 2},
    "dtc3": {"code": "P1194-00", "priority": 3}
}



def validate_decision_output(output, prior_list):
    assert output['status'] == 'success'
    data = output['data']

    assert "search_query" in data
    assert "filters" in data
    assert "dtc_code" in data["filters"]
    assert "confidence" in data


    assert isinstance(data['search_query'], str)
    assert isinstance(data['filters'], dict)
    assert isinstance(data['confidence'],(float,int))


def test_extraction_clean_input():
    message = "P245E-11 is active"
    res = dct_code_extraction_agent(conversation_history, message,valid_prior_list)
    assert res['status'] == 'success'
    assert "data" in res


def test_extraction_messy_ouput():
    message = "yeah I think code P245E-11 popped up again not sure tho"

    res = dct_code_extraction_agent(conversation_history, message, valid_prior_list)

    assert res['status'] == 'success'


def test_extraction_no_dict():
    message = "yeah I think code P245E-11 popped up again not sure tho"
    res = dct_code_extraction_agent(conversation_history, message, {})

    assert res['status'] == 'success'


def test_decision_messy_user_input():
    message ="yeah bro wiring looks fine but voltage drops sometimes idk"
    res = dct_code_decision_agent(conversation_history, message, valid_prior_list)
    prior_list = convert_to_prior_list(res['data'])
    validate_decision_output(res, prior_list)


def test_decision_complex_input():
    message = """
            I checked hoses they look fine,
            wiring also seems okay,
            but voltage fluctuates between 0.2 and 0.3 V,
            sometimes drops below threshold
    """     
    res = dct_code_decision_agent(conversation_history, message, valid_prior_list)

    prior_list = convert_to_prior_list(res['data'])
    validate_decision_output(res, prior_list)


def test_filter_electrical():
    message = "measure voltage at pin C it's not 5 V"
    res = dct_code_decision_agent(conversation_history, message, valid_prior_list)

    prior_list = convert_to_prior_list(res['data'])
    validate_decision_output(res, prior_list)
    assert res['data']['filters']['flow_type'] in ["ELECTRICAL", None]
def test_filter_inspection():
    mess = "hoses are cracked and loose"
    res = dct_code_decision_agent(conversation_history, mess, valid_prior_list)
    prior_list = convert_to_prior_list(res['data'])
    validate_decision_output(res, prior_list)
    assert res['data']['filters']['flow_type'] in ["INSPECTION", None]



def test_priority_selection():

    prior_list = {
        "dtc1": {"code": "P245E-11", "priority": 3},
        "dtc2": {"code": "P2452-12", "priority": 1}
    }
    message = "voltage issues"
    res = dct_code_decision_agent(conversation_history, message, prior_list)
    prior_list = convert_to_prior_list(res['data'])
    validate_decision_output(res, prior_list)
    assert res['data']['filters']['dtc_code'] == "P2452-12"


def test_same_prioirty_selection():
    prior_list = {
        "dtc1": {"code": "P245E-11", "priority": 1},
        "dtc2": {"code": "P2452-12", "priority": 1}
    }
    message = "sensor issues"
    res = dct_code_decision_agent(conversation_history, message, prior_list)

    prior_list = convert_to_prior_list(res['data'])
    validate_decision_output(res, prior_list)


def test_empty_prior_list():
    message = "voltage issues"
    res = dct_code_decision_agent(conversation_history, message, {})
    assert res['status'] in  ['success', 'error']


def test_invalid_dtc():
    prioir_list = {
        "dtc1": {"code": "INVALID", "priority": 1}
    }
    message = "random issues"
    res = dct_code_decision_agent(conversation_history, message, prioir_list)
    assert res['status']  in ['success', 'error']

def test_invalid_json_handling(monkeypatch):
    class MockResponse:
        class Choice:
            def __init__(self):
                self.message = type("msg", (), {"content": "INVALID JSON"})
        
        choices = [Choice()]

    def mock_create(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(
        "backend.agents.agent.client.chat.completions.create",
        mock_create
    )

    message = "voltage issue"
    result = dct_code_decision_agent(conversation_history, message, valid_prior_list)

    assert result["status"] == "error"