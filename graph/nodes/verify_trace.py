from graph.state import GraphState
from config import STATUS_VERIFIED, STATUS_FAILED, FAILURE_VERIFICATION
from verifier.verifier import verify_symbolic_trace


def verify_trace_node(state: GraphState) -> GraphState:
    symbolic_problem = state.get("symbolic_problem")
    symbolic_trace = state.get("symbolic_trace")

    result = verify_symbolic_trace(symbolic_problem, symbolic_trace)

    if result["verification_success"] is False:
        return {
            **state,
            "verification_success": False,
            "verification_error": result["verification_error"],
            "status": STATUS_FAILED,
            "failure_stage": FAILURE_VERIFICATION,
        }

    return {
        **state,
        "verification_result": result["verification_result"],
        "verification_success": True,
        "verification_error": None,
        "status": STATUS_VERIFIED,
    }
