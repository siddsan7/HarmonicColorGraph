import httpx

from app.jobs.policy import is_retryable


def test_retry_policy_distinguishes_transient_and_permanent_http_failures():
    request = httpx.Request("GET", "https://example.invalid/test")
    for status in (429, 502, 503, 504):
        response = httpx.Response(status, request=request)
        assert is_retryable(httpx.HTTPStatusError("temporary", request=request, response=response))
    for status in (400, 401, 403, 404, 422):
        response = httpx.Response(status, request=request)
        assert not is_retryable(
            httpx.HTTPStatusError("permanent", request=request, response=response)
        )
    assert is_retryable(TimeoutError("timeout"))
    assert not is_retryable(ValueError("bad payload"))
