"""Cliente mock determinístico; não executa nem simula geração de texto por IA."""

from collections.abc import Iterable
from copy import deepcopy
from typing import Any

from pydantic import BaseModel

from conecta_conselho.domain.enums import ConnectivityStatus, Decision
from conecta_conselho.domain.models import AgentOpinion, BridgeProposal, GuardianDecision
from conecta_conselho.llm.base import LLMClient, LLMClientError


class MockLLMClient(LLMClient):
    """Respostas por regras e templates para execução offline e testes."""

    provider_name = "mock"
    model_name = None

    def __init__(self, responses: Iterable[Any] | None = None) -> None:
        self._responses = iter(responses) if responses is not None else None
        self.requests: list[tuple[str, dict[str, Any]]] = []

    async def generate_structured(
        self,
        system_prompt: str,
        payload: dict[str, Any],
        schema: type[BaseModel],
    ) -> Any:
        self.requests.append((system_prompt, deepcopy(payload)))
        if self._responses is not None:
            try:
                response = next(self._responses)
            except StopIteration as exc:
                raise LLMClientError("Mock sem resposta configurada para esta chamada.") from exc
            if isinstance(response, Exception):
                raise response
            return deepcopy(response)

        if schema is not AgentOpinion:
            if schema is BridgeProposal:
                return self._bridge_proposal(payload)
            if schema is GuardianDecision:
                return self._guardian_draft(payload)
            raise LLMClientError(f"O mock não tem template para o schema {schema.__name__}.")

        role = payload.get("agent_role")
        if role == "financial":
            return self._financial_opinion(payload)
        if role == "social":
            return self._social_opinion(payload)
        if role == "technical":
            return self._technical_opinion(payload)
        if role == "budget":
            return self._budget_opinion(payload)
        raise LLMClientError(f"O mock não tem template para o papel {role!r}.")

    @staticmethod
    def _financial_opinion(payload: dict[str, Any]) -> dict[str, Any]:
        indicators = payload.get("indicators", [])
        demand = next(
            (item for item in indicators if item.get("indicator") == "demand_proxy_index"),
            None,
        )
        cost = next(
            (item for item in indicators if item.get("indicator") == "estimated_base_cost_brl"),
            None,
        )
        parameters = payload.get("parameters") or {}
        supporting_ids = [
            item["evidence_id"]
            for item in (demand, cost)
            if item is not None and item.get("value") is not None
        ]
        missing_data = [
            "preço e taxa de adesão",
            "ARPU, margem e dados comerciais observados",
        ]
        if demand is None or demand.get("value") is None:
            missing_data.insert(0, "proxy de demanda")
            position = "insufficient_data"
            summary = "Não há proxy de demanda disponível para este parecer financeiro."
        else:
            cost_known = parameters.get("estimated_base_cost_brl") is not None or (
                cost is not None and cost.get("value") is not None
            )
            if not cost_known:
                missing_data.insert(0, "custo estimado do cenário")
            position = "conditional"
            summary = (
                f"O proxy de demanda ({demand['kind']}) foi considerado como sinal de triagem "
                f"[{demand['evidence_id']}], mas não demonstra clientes, receita ou retorno."
            )

        assumptions = [
            "Parâmetros de custo fornecidos pelo usuário são premissas, não orçamento executivo."
        ]
        if payload.get("municipality_is_synthetic"):
            assumptions.append("A localidade e suas evidências são sintéticas.")
        return {
            "agent_name": "financial",
            "position": position,
            "summary": summary,
            "supporting_evidence_ids": supporting_ids,
            "risks": [
                "Indicadores hipotéticos não validam demanda contratante.",
                "Sem preço e adesão, não há base para estimar sustentabilidade ou ROI.",
            ],
            "assumptions": assumptions,
            "missing_data": missing_data,
            "confidence_level": "low",
        }

    @staticmethod
    def _social_opinion(payload: dict[str, Any]) -> dict[str, Any]:
        indicators = payload.get("indicators", [])
        access_gap = next(
            (item for item in indicators if item.get("indicator") == "social_access_gap_pct"),
            None,
        )
        has_gap = access_gap is not None and access_gap.get("value") is not None
        evidence_ids = [access_gap["evidence_id"]] if has_gap else []
        if has_gap:
            summary = (
                f"O indicador de lacuna de acesso ({access_gap['kind']}) é um sinal para "
                f"triagem social [{access_gap['evidence_id']}], não uma medição de impacto."
            )
            position = "conditional"
            missing_data = [
                "medição observada de acesso à conectividade",
                "efeitos distributivos e resultados locais em educação e saúde",
                "consulta e validação com instituições públicas",
            ]
        else:
            summary = "Não há indicador de lacuna de acesso disponível para este parecer social."
            position = "insufficient_data"
            missing_data = [
                "indicador de lacuna de acesso observado ou estimado",
                "efeitos distributivos e resultados locais em educação e saúde",
            ]

        assumptions = []
        if payload.get("municipality_is_synthetic") or (
            has_gap and access_gap.get("is_synthetic")
        ):
            assumptions.append("O indicador é sintético/hipotético e não descreve população real.")
        return {
            "agent_name": "social",
            "position": position,
            "summary": summary,
            "supporting_evidence_ids": evidence_ids,
            "risks": [
                "Lacuna de acesso não comprova demanda contratante nem resultado social "
                "causado pela expansão.",
                "As fixtures não medem efeitos causais em educação, saúde ou inclusão.",
            ],
            "assumptions": assumptions,
            "missing_data": missing_data,
            "confidence_level": "low",
        }

    @staticmethod
    def _technical_opinion(payload: dict[str, Any]) -> dict[str, Any]:
        indicators = payload.get("indicators", [])
        critical_names = {
            "reported_coverage_pct",
            "backhaul_capacity_mbps",
            "technical_constraint_level",
            "powered_sites_estimate",
            "electricity_availability",
        }
        technical_evidence = [
            item for item in indicators if item.get("indicator") in critical_names
        ]
        known_evidence = [item for item in technical_evidence if item.get("value") is not None]
        supporting_ids = [item["evidence_id"] for item in technical_evidence]
        missing_data = []
        if not any(
            item.get("indicator") == "reported_coverage_pct"
            and item.get("value") is not None
            for item in technical_evidence
        ):
            missing_data.append("cobertura validada ou medição de rede")
        if not any(
            item.get("indicator") == "backhaul_capacity_mbps"
            and item.get("value") is not None
            for item in technical_evidence
        ):
            missing_data.append("capacidade de backhaul verificada")
        if not any(
            item.get("indicator") == "electricity_availability"
            and item.get("value") is not None
            for item in technical_evidence
        ):
            missing_data.append("verificação de disponibilidade elétrica")

        position = "conditional" if known_evidence else "insufficient_data"
        if known_evidence:
            summary = (
                "Há indicadores técnicos para triagem, mas eles não comprovam infraestrutura "
                "instalada ou capacidade de atendimento; é necessário survey de campo."
            )
        else:
            summary = (
                "Não há valores técnicos disponíveis para avaliar cobertura e infraestrutura; "
                "é necessário survey de campo."
            )
        risks = [
            "Evidências hipotéticas ou estimadas não comprovam disponibilidade de rede.",
            "Fibra, espectro, torres, energia e capacidade não foram presumidos.",
        ]
        assumptions = []
        if payload.get("municipality_is_synthetic"):
            assumptions.append("A localidade e suas evidências são sintéticas.")
        return {
            "agent_name": "technical",
            "position": position,
            "summary": summary,
            "supporting_evidence_ids": supporting_ids,
            "risks": risks,
            "assumptions": assumptions,
            "missing_data": missing_data,
            "confidence_level": "low",
        }

    @staticmethod
    def _budget_opinion(payload: dict[str, Any]) -> dict[str, Any]:
        indicators = payload.get("indicators", [])
        cost_evidence = next(
            (
                item
                for item in indicators
                if item.get("indicator") == "estimated_base_cost_brl"
                and item.get("value") is not None
            ),
            None,
        )
        scenario = (payload.get("additional_context") or {}).get("baseline_scenario")
        traceable_cost = cost_evidence is not None
        scenario_cost = (
            scenario.get("estimated_total_cost_brl") if scenario is not None else None
        )
        cost_matches_evidence = traceable_cost and scenario_cost == cost_evidence.get("value")
        if scenario is None or scenario.get("estimated_total_cost_brl") is None:
            position = "insufficient_data"
            summary = "O custo do cenário está indisponível; não é possível avaliar o teto."
            missing_data = ["custo estimado documentado", "validação e aprovação orçamentária"]
        elif not cost_matches_evidence:
            position = "insufficient_data"
            summary = (
                "A premissa do cenário não pode ser reconciliada com evidência de custo "
                "rastreável; não é possível validar o enquadramento orçamentário."
            )
            missing_data = [
                "evidência de custo compatível com a premissa do cenário",
                "validação e aprovação orçamentária",
            ]
        elif scenario.get("within_budget") is False:
            position = "unfavorable"
            summary = (
                f"A premissa de custo [{cost_evidence['evidence_id']}] excede o teto informado; "
                "o cenário requer revisão de escopo e validação orçamentária."
            )
            missing_data = ["orçamento formal aprovado", "cotação e composição detalhada do custo"]
        else:
            position = "conditional"
            summary = (
                f"A premissa de custo [{cost_evidence['evidence_id']}] cabe no teto do cenário, "
                "mas isso não equivale a orçamento aprovado ou custo executivo validado."
            )
            missing_data = ["orçamento formal aprovado", "cotação e composição detalhada do custo"]

        supporting_ids = [cost_evidence["evidence_id"]] if cost_matches_evidence else []
        assumptions = [
            "O teto informado é uma premissa de cenário e não comprova dotação orçamentária."
        ]
        if payload.get("municipality_is_synthetic"):
            assumptions.append("A localidade e suas evidências são sintéticas.")
        return {
            "agent_name": "budget",
            "position": position,
            "summary": summary,
            "supporting_evidence_ids": supporting_ids,
            "risks": [
                "Custos hipotéticos não são orçamento executivo nem cotação validada.",
                "A comparação não inclui itens que não estejam nas premissas fornecidas.",
            ],
            "assumptions": assumptions,
            "missing_data": missing_data,
            "confidence_level": "low",
        }

    @staticmethod
    def _bridge_proposal(payload: dict[str, Any]) -> dict[str, Any]:
        candidates = []
        provided_evidence_ids = {
            item.get("evidence_id") for item in payload.get("indicators", [])
        }
        for institution in payload.get("anchor_institutions", []):
            status = institution.get("connectivity_status", ConnectivityStatus.UNKNOWN)
            if status == ConnectivityStatus.UNCONNECTED:
                priority = "high"
                rationale = "O cadastro informa status não conectado; validar em campo."
            elif status == ConnectivityStatus.CONNECTED:
                priority = "low"
                rationale = "O cadastro informa status conectado; confirmar se há lacuna local."
            else:
                priority = "medium"
                rationale = (
                    "O status de conectividade é desconhecido; verificar necessidade em campo."
                )

            evidence_ids = [
                evidence_id
                for evidence_id in institution.get("evidence_ids", [])
                if evidence_id in provided_evidence_ids
            ]
            caveats = [
                "Candidatura não representa parceria, contrato ou autorização confirmada."
            ]
            if institution.get("is_synthetic") or payload.get("municipality_is_synthetic"):
                caveats.append("Instituição e dados são sintéticos e servem apenas à demonstração.")
            if not evidence_ids:
                caveats.append("Não há evidência associada disponível neste catálogo.")
            candidates.append(
                {
                    "institution_id": institution["institution_id"],
                    "rationale": rationale,
                    "evidence_ids": evidence_ids,
                    "assumptions": [
                        "A necessidade e a viabilidade de articulação dependem de validação local."
                    ],
                    "partnership_status": "unverified",
                    "priority": priority,
                    "caveats": caveats,
                }
            )
        return {
            "candidates": candidates,
            "notes": [
                "Prioridade qualitativa deriva apenas do status de conectividade cadastrado.",
                "As candidatas exigem confirmação local; nenhuma parceria é presumida.",
            ],
        }

    @staticmethod
    def _guardian_draft(payload: dict[str, Any]) -> dict[str, Any]:
        opinions = payload.get("opinions", [])
        disagreements = payload.get("disagreements", [])
        scenario = payload.get("with_bridges", {})
        opinion_positions = {item.get("position") for item in opinions}
        if (
            disagreements
            or "insufficient_data" in opinion_positions
            or scenario.get("within_budget") is None
        ):
            decision = Decision.HUMAN_REVIEW
            disagreement_topics = ", ".join(
                item.get("topic", "divergência") for item in disagreements
            )
            rationale = (
                "As lacunas, divergências ou incertezas do cenário impedem uma conclusão "
                "operacional; é necessária revisão humana."
            )
            if disagreement_topics:
                rationale += f" A rodada de contestação identificou: {disagreement_topics}."
        elif scenario.get("within_budget") is False or "unfavorable" in opinion_positions:
            decision = Decision.WAIT
            rationale = (
                "As evidências recebidas indicam riscos que precisam ser resolvidos antes "
                "de avançar."
            )
        else:
            decision = Decision.INVEST
            rationale = (
                "Esta é uma decisão preliminar baseada somente nas entradas fornecidas e "
                "sujeita a validação humana e aos hard gates."
            )

        available_ids = {
            item.get("evidence_id") for item in payload.get("evidence_catalog", [])
        }
        cited_ids = list(
            dict.fromkeys(
                evidence_id
                for opinion in opinions
                for evidence_id in opinion.get("supporting_evidence_ids", [])
                if evidence_id in available_ids
            )
        )
        return {
            "decision": decision.value,
            "rationale": rationale,
            "conditions": [
                "Validar em campo cobertura, infraestrutura e capacidade de backhaul.",
                "Validar custos e orçamento antes de qualquer decisão operacional.",
                "Ponderar prioridade social junto aos custos e riscos técnicos, sem substituir "
                "validação humana.",
            ],
            "blockers": [
                warning
                for warning in payload.get("warnings", [])
                if "ausente" in warning.lower() or "indisponível" in warning.lower()
            ],
            "unresolved_questions": [
                question
                for opinion in opinions
                for question in opinion.get("missing_data", [])
            ],
            "cited_evidence_ids": cited_ids,
            "requires_human_approval": True,
        }
