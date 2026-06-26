import httpx

from gitbook_translator.providers.base import SegmentInput, TranslationRequest
from gitbook_translator.providers.ollama_provider import OllamaProvider


def _transport(handler):
    return httpx.MockTransport(handler)


def test_ollama_healthcheck_lists_requested_model():
    def handler(request):
        assert request.url == "http://127.0.0.1:11434/api/tags"
        return httpx.Response(200, json={"models": [{"name": "qwen3:latest"}]})

    provider = OllamaProvider(model="qwen3:latest", transport=_transport(handler))

    assert provider.healthcheck().available is True


def test_ollama_healthcheck_reports_missing_model():
    def handler(request):
        return httpx.Response(200, json={"models": [{"name": "llama3:latest"}]})

    provider = OllamaProvider(model="qwen3:latest", transport=_transport(handler))

    health = provider.healthcheck()
    assert health.available is False
    assert "qwen3:latest" in health.message


def test_ollama_translate_posts_structured_chat_request():
    requests = []

    def handler(request):
        requests.append(request)
        assert request.url == "http://127.0.0.1:11434/api/chat"
        payload = httpx.Request("POST", request.url, content=request.content)
        assert payload.content
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": '{"segments":[{"id":"segment-0001","translation":"Hello"}]}'
                }
            },
        )

    provider = OllamaProvider(model="qwen3:latest", transport=_transport(handler))

    response = provider.translate(
        TranslationRequest(
            language="en",
            segments=[SegmentInput(id="segment-0001", text="こんにちは")],
            dictionary={},
        )
    )

    assert [(segment.id, segment.translation) for segment in response.segments] == [
        ("segment-0001", "Hello")
    ]
    assert requests
