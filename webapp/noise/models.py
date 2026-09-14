from pydantic import BaseModel, ConfigDict


class NoiseConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
