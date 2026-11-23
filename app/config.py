
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    # API keys
    waqi_api_key: str
    llm_api_key: str

    # General application settings
    app_name: str
    default_location: str
    request_timeout: int

    @classmethod
    def from_environment(cls):

        waqi_api_key = os.getenv("WAQI_API_KEY", "")

        # Read Groq key, with backward compatibility
        llm_api_key = os.getenv(
            "GROQ_API_KEY",
            os.getenv("LLM_API_KEY", "")
        )

        app_name = os.getenv(
            "APP_NAME",
            "AI-Based Environmental Health Advisory System"
        )

        default_location = os.getenv(
            "DEFAULT_LOCATION",
            "Delhi"
        )

        request_timeout = os.getenv(
            "REQUEST_TIMEOUT",
            "10"
        )

        try:
            request_timeout = int(request_timeout)
        except ValueError:
            raise ValueError(
                "REQUEST_TIMEOUT must be a valid integer."
            )

        if request_timeout <= 0:
            raise ValueError(
                "REQUEST_TIMEOUT must be greater than 0."
            )

        return cls(
            waqi_api_key=waqi_api_key,
            llm_api_key=llm_api_key,
            app_name=app_name,
            default_location=default_location,
            request_timeout=request_timeout
        )


settings = Settings.from_environment()
