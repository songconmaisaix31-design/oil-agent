"""Official DeepSeek Flash Responses binding; no gateway or credential discovery.

Reuse the bounded one-request extraction and durable usage path. Cached/reasoning
tokens are already included in the provider's input/output totals; never subtract
or add them again. Live use requires C/I's exact provider/model authorization.
"""

from dataclasses import dataclass

from oil_agent.intelligence.openai import OpenAIResponsesClient, OpenAISettings

ENDPOINT = "https://api.deepseek.com/responses"
MODEL = "deepseek-flash"


@dataclass(frozen=True)
class DeepSeekSettings(OpenAISettings):
    def __post_init__(self):
        super().__post_init__()
        if self.model != MODEL:
            raise ValueError("This official DeepSeek adapter requires exact model deepseek-flash")


class DeepSeekResponsesClient(OpenAIResponsesClient):
    _provider = "deepseek"
    _provider_name = "DeepSeek"
    _endpoint = ENDPOINT
    _host = "api.deepseek.com"
    _exact_response_model = True

    def __init__(self, settings: DeepSeekSettings, **kwargs):
        # Reject incompatible settings before the shared client can construct a request.
        if not isinstance(settings, DeepSeekSettings):
            raise ValueError("DeepSeek client requires explicit DeepSeekSettings")
        super().__init__(settings, **kwargs)
