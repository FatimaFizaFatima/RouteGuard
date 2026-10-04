import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str | None = None


class ModelConfig(BaseModel):

    id: str
    provider : str
    model : str
    tasks : list[str]
    cost_per_1m_input : float = Field(ge=0)
    cost_per_1m_output : float = Field(ge=0)
    max_context : int
    timeout_s : int = 30
    quality : float = Field(ge=1, le=10)


def load_models(path: str) -> dict[str, ModelConfig]:
   
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    items = raw["models"]
    models: dict[str, ModelConfig] = {}
    for item in items:
        cfg = ModelConfig(**item)
        if cfg.id in models:
            raise ValueError(f"duplicate model id: {cfg.id}")
        models[cfg.id] = cfg

    return models


class Weights(BaseModel):
    cost: float = Field(ge=0)
    latency: float = Field(ge=0)
    quality: float = Field(ge=0)


def load_routing(path: str) -> tuple[dict[str, Weights], dict[str, str]]:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    strategies = {name: Weights(**w) for name, w in raw["strategies"].items()}
    routes = raw["routes"]

    if "default" not in routes:
        raise ValueError("routes must define a 'default'")
    for task, strategy in routes.items():
        if strategy not in strategies:
            raise ValueError(f"route '{task}' uses unknown strategy '{strategy}'")

    return strategies, routes     