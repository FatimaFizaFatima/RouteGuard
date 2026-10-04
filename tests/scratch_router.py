from app.config import load_models, load_routing
from app.router import estimate_tokens, filter_models, score_models, route
from app.schemas import ChatRequest

models = load_models("models.yaml")
strategies, routes = load_routing("models.yaml")


def make(task, text="hi", max_tokens=None):
    return ChatRequest(
        messages=[{"role": "user", "content": text}],
        task_type=task,
        max_tokens=max_tokens,
    )


def ids(items):
    return [m.id for m in items]


print("--- estimate_tokens ---")
print(estimate_tokens(make("chat", "a" * 400)))                  
print(estimate_tokens(make("chat", "a" * 400, max_tokens=50)))   

print("--- filter_models ---")
print(ids(filter_models(make("code"), models)))             
print(ids(filter_models(make("chat"), models)))             
print(ids(filter_models(make("translation"), models)))      
print(ids(filter_models(make("chat", "a" * 20000), models))) 
print(ids(filter_models(make("chat", "a" * 16384), models)))  
print(ids(filter_models(make("chat", "a" * 16388), models)))  

print("--- score_models (chat = fastest) ---")
fastest = strategies["fastest"]
cands = filter_models(make("chat"), models)
for s, m in score_models(cands, fastest, {}):
    print(m.id, round(s, 3))         
for s, m in score_models(cands, fastest, {"local-fast": 1000, "local-balanced": 3000}):
    print(m.id, round(s, 3))          

print("--- route ---")
print(ids(route(make("code"), models, strategies, routes, {})))

print(ids(route(make("chat"), models, strategies, routes, {})))

print(ids(route(make("chat"), models, strategies, routes,
                {"local-fast": 1000, "local-balanced": 3000})))

print(ids(route(make("summarization"), models, strategies, routes, {})))

print(ids(route(make("translation"), models, strategies, routes, {})))
