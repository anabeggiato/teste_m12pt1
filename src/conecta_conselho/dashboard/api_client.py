"""Cliente HTTP tipado por convenção para a API local do dashboard."""

from typing import Any

import httpx


class DashboardAPIError(RuntimeError):
    """Erro HTTP retornado pela API ou falha de conexão com ela."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        payload: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class DashboardAPI:
    """Encapsula as rotas utilizadas pela interface Streamlit."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def health(self) -> dict[str, Any]:
        return self._json_request("GET", "/health")

    def list_municipalities(self) -> list[dict[str, Any]]:
        result = self._json_request("GET", "/api/v1/municipalities")
        if not isinstance(result, list):
            raise DashboardAPIError("Resposta inválida ao listar localidades.")
        return result

    def get_municipality(self, municipality_code: str) -> dict[str, Any]:
        return self._json_request("GET", f"/api/v1/municipalities/{municipality_code}")

    def create_analysis(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._json_request(
            "POST", "/api/v1/analyses", json=payload, timeout=600.0
        )

    def export_analysis(self, analysis_id: str) -> bytes:
        response = self._request(
            "GET", f"/api/v1/analyses/{analysis_id}/export"
        )
        return response.content

    def _json_request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._request(method, path, **kwargs)
        try:
            return response.json()
        except ValueError as exc:
            raise DashboardAPIError("A API retornou JSON inválido.") from exc

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise DashboardAPIError(
                "Não foi possível conectar à API. Verifique se ela está iniciada."
            ) from exc
        if response.is_error:
            try:
                body = response.json()
            except ValueError:
                body = response.text
            detail = body.get("detail", body) if isinstance(body, dict) else body
            raise DashboardAPIError(
                f"API respondeu HTTP {response.status_code}: {detail}",
                status_code=response.status_code,
                payload=body,
            )
        return response
