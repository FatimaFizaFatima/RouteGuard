from app.config import ModelConfig, Weights
from app.schemas import ChatRequest

def estimate_tokens(req: ChatRequest) -> int:

    chars = sum(len(m.content) for m in req.messages)
    return chars // 4 + (req.max_tokens or 0)

def filter_models(req: ChatRequest, models : dict[str, ModelConfig]) -> list[ModelConfig]:

    needed = estimate_tokens(req)
    return [
        m for m in models.values()
        if req.task_type in m.tasks and needed <= m.max_context
    ]


def score_models(candidates: list[ModelConfig], weights: Weights, latency: dict[str, float]) -> list[tuple[float, ModelConfig]]:
    costs = {m.id: m.cost_per_1m_input + m.cost_per_1m_output for m in candidates}
    max_cost = max(costs.values(), default=0)
    known = [latency[m.id] for m in candidates if m.id in latency]
    best_latency = min(known) if known else None

    scored = []
    for m in candidates:
        
        cost_score = 1 - costs[m.id] / max_cost if max_cost > 0 else 1.0
        if m.id in latency:
            speed_score = best_latency / latency[m.id]
        else:
            speed_score = 0.5
        quality_score = m.quality / 10

        total = (weights.cost * cost_score
                 + weights.latency * speed_score
                 + weights.quality * quality_score)
        scored.append((total, m))
    return scored


def route(
    req: ChatRequest,
    models: dict[str, ModelConfig],
    strategies: dict[str, Weights],
    routes: dict[str, str],
    latency: dict[str, float],
) -> list[ModelConfig]:
    candidates = filter_models(req, models)
    strategy_name = routes.get(req.task_type, routes["default"])
    weights = strategies[strategy_name]

    scored = score_models(candidates, weights, latency)
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [m for _, m in scored]