"""Dashboard Streamlit para a jornada demonstrativa do Conselho."""

import json
import os
from typing import Any

from conecta_conselho.dashboard.api_client import DashboardAPI, DashboardAPIError
from conecta_conselho.dashboard.presentation import (
    display_label,
    evidence_label,
    format_brl,
    format_value,
)


def _optional_number(st: Any, label: str, key: str, help_text: str) -> float | None:
    return st.number_input(
        label,
        min_value=0.0,
        value=None,
        placeholder="Não informado",
        step=1000.0,
        key=key,
        help=help_text,
    )


def _show_evidence_cards(st: Any, municipality: dict[str, Any]) -> None:
    st.subheader("Indicadores e evidências")
    if municipality.get("is_synthetic"):
        st.warning("Localidade sintética de demonstração; os valores não têm validade empírica.")
    else:
        st.info(
            "Localidade com dados oficiais somente para os indicadores exibidos. "
            "Informações ausentes sobre conectividade, custos e instituições não são presumidas."
        )
    evidences = municipality.get("indicators", [])
    for start in range(0, len(evidences), 3):
        columns = st.columns(3)
        for column, evidence in zip(columns, evidences[start : start + 3], strict=False):
            with column:
                st.metric(
                    evidence_label(evidence),
                    format_value(evidence.get("value"), evidence.get("unit")),
                )
                source = evidence.get("source_name", "Fonte não informada")
                year = evidence.get("reference_year")
                st.caption(f"Fonte: {source}" + (f" · Ano: {year}" if year else ""))
                if evidence.get("source_license"):
                    st.caption(f"Termos: {evidence['source_license']}")
                for limitation in evidence.get("limitations", []):
                    st.caption(f"Limitação: {limitation}")


def _render_opinions(st: Any, result: dict[str, Any]) -> None:
    st.subheader("Pareceres do Conselho")
    opinions = result.get("opinions", [])
    columns = st.columns(2)
    for index, opinion in enumerate(opinions):
        with columns[index % len(columns)]:
            with st.expander(opinion.get("agent_name", "Parecer"), expanded=True):
                st.write(opinion.get("summary", "Sem resumo."))
                st.caption(
                    f"Posição: {display_label(opinion.get('position', 'não informada'))} · "
                    f"Completude das evidências: "
                    f"{display_label(opinion.get('confidence_level', 'não informada'))}"
                )
                for title, key in (
                    ("Riscos", "risks"),
                    ("Premissas", "assumptions"),
                    ("Dados ausentes", "missing_data"),
                ):
                    values = opinion.get(key, [])
                    if values:
                        st.markdown(f"**{title}**")
                        for value in values:
                            st.markdown(f"- {value}")
                if opinion.get("supporting_evidence_ids"):
                    st.caption(
                        "Evidências: "
                        + ", ".join(opinion["supporting_evidence_ids"])
                    )


def _render_bridges(st: Any, result: dict[str, Any]) -> None:
    st.subheader("Pontes e instituições candidatas")
    candidates = result.get("bridge_proposal", {}).get("candidates", [])
    if not candidates:
        st.info("Nenhuma instituição candidata foi retornada.")
        return
    institutions_by_id = {
        institution["institution_id"]: institution
        for institution in result.get("municipality", {}).get("anchor_institutions", [])
    }
    for candidate in candidates:
        institution_id = candidate.get("institution_id", "")
        institution_name = institutions_by_id.get(institution_id, {}).get("name", institution_id)
        with st.expander(f"{institution_name} · {institution_id}"):
            st.write(candidate.get("rationale", "Sem justificativa."))
            st.caption(
                "Parceria não verificada · prioridade qualitativa: "
                f"{display_label(candidate.get('priority', 'não informada'))}"
            )
            for label, key in (("Premissas", "assumptions"), ("Ressalvas", "caveats")):
                for value in candidate.get(key, []):
                    st.markdown(f"- **{label}:** {value}")


def _scenario_value(scenario: dict[str, Any], key: str) -> str:
    if key == "estimated_total_cost_brl":
        return format_brl(scenario.get(key))
    if key == "hypothetical_anchor_revenue_brl":
        return format_brl(scenario.get(key))
    if key == "hypothetical_net_balance_brl":
        return format_brl(scenario.get(key))
    value = scenario.get(key)
    if value is None:
        return "Não disponível"
    return "Sim" if value else "Não"


def _render_scenarios(
    st: Any, result: dict[str, Any], budget_ceiling_brl: float | None
) -> None:
    st.subheader("Comparação de cenários")
    st.info("Simulação hipotética — não representa proposta comercial ou orçamento de engenharia.")
    columns = st.columns(2)
    for column, title, key in zip(
        columns,
        ("Base", "Com Pontes"),
        ("baseline", "with_bridges"),
        strict=True,
    ):
        scenario = result.get(key, {})
        with column:
            st.markdown(f"#### {title}")
            st.write(f"Teto hipotético: {format_brl(budget_ceiling_brl)}")
            st.write(f"Custo estimado: {_scenario_value(scenario, 'estimated_total_cost_brl')}")
            st.write(
                "Receita hipotética de âncoras: "
                f"{_scenario_value(scenario, 'hypothetical_anchor_revenue_brl')}"
            )
            st.write(
                "Saldo hipotético incremental: "
                f"{_scenario_value(scenario, 'hypothetical_net_balance_brl')}"
            )
            st.write(
                "Dentro do teto informado: "
                f"{_scenario_value(scenario, 'within_budget')}"
            )
            for warning in scenario.get("warnings", []):
                st.warning(warning)
            for note in scenario.get("calculation_notes", []):
                st.caption(note)
            if scenario.get("selected_anchor_ids"):
                st.caption(
                    "Âncoras selecionadas: "
                    + ", ".join(scenario["selected_anchor_ids"])
                )
    comparison = result.get("comparison") or {}
    st.markdown("**Variação hipotética entre cenários**")
    st.write(
        "Custo incremental: "
        f"{format_brl(comparison.get('incremental_cost_brl'))} · "
        "Saldo incremental: "
        f"{format_brl(comparison.get('hypothetical_net_balance_brl'))}"
    )
    for warning in comparison.get("warnings", []):
        st.warning(warning)


def _render_guardian_and_audit(st: Any, result: dict[str, Any], api: DashboardAPI) -> None:
    guardian = result.get("guardian", {})
    st.subheader("Guardião")
    st.markdown(f"### Decisão preliminar: {guardian.get('decision', 'Não disponível')}")
    st.warning("Toda decisão exige aprovação humana; esta tela não autoriza investimento.")
    st.write(guardian.get("rationale", "Sem justificativa."))
    for title, key in (
        ("Condições", "conditions"),
        ("Bloqueios", "blockers"),
        ("Questões em aberto", "unresolved_questions"),
        ("Motivos dos hard gates", "guard_reasons"),
    ):
        values = guardian.get(key, [])
        if values:
            st.markdown(f"**{title}**")
            for value in values:
                st.markdown(f"- {value}")

    st.subheader("Auditoria e exportação")
    st.write(f"ID: `{result.get('analysis_id', 'não informado')}`")
    st.write(f"Executada em: {result.get('created_at', 'não informado')}")
    st.write(
        f"Modo: {result.get('mode', 'não informado')} · "
        f"Status: {display_label(result.get('status', 'não informado'))}"
    )
    if result.get("errors"):
        st.warning("A análise foi concluída parcialmente.")
        st.json(result["errors"])
    if result.get("warnings"):
        for warning in result["warnings"]:
            st.warning(warning)
    disagreements = result.get("disagreements", [])
    if disagreements:
        st.markdown("**Divergências**")
        st.json(disagreements)
    with st.expander("Catálogo de evidências e limitações"):
        st.json(result.get("evidence_catalog", []))
    analysis_id = result.get("analysis_id")
    if analysis_id:
        try:
            export_json = api.export_analysis(analysis_id)
        except DashboardAPIError as exc:
            st.error(f"Falha ao carregar exportação: {exc}")
        else:
            try:
                export_document = json.loads(export_json)
            except ValueError:
                st.error("Falha ao interpretar o JSON de auditoria retornado pela API.")
            else:
                model_name = export_document.get("model_name") or "Nenhum (modo mock)"
                st.write(f"Modelo: {model_name}")
                st.caption(
                    "Versões dos prompts: "
                    + json.dumps(
                        export_document.get("prompt_versions", {}),
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
                with st.expander("Premissas e hipóteses auditáveis"):
                    st.json(
                        {
                            "request": export_document.get("request", {}),
                            "hypotheses": export_document.get("hypotheses", {}),
                        }
                    )
            st.download_button(
                "Baixar relatório JSON",
                data=export_json,
                file_name=f"analysis-{analysis_id}.json",
                mime="application/json",
            )


def render_dashboard() -> None:
    import streamlit as st

    st.set_page_config(page_title="Conecta Conselho", page_icon="📡", layout="wide")
    st.title("Conecta Conselho")
    st.caption(
        "Triagem demonstrativa para expansão de conectividade. Não autoriza obras ou investimentos."
    )
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    api = DashboardAPI(api_base_url)
    try:
        health = api.health()
        st.sidebar.success(
            f"API disponível · modo {health.get('mode', 'não informado')} · "
            f"versão {health.get('version', 'não informada')}"
        )
        municipalities = api.list_municipalities()
    except DashboardAPIError as exc:
        st.sidebar.error(str(exc))
        st.error("Não foi possível carregar o dashboard sem a API local.")
        return

    if not municipalities:
        st.error("A API não retornou localidades.")
        return
    municipality_by_code = {
        item["municipality_code"]: item for item in municipalities
    }
    selected_code = st.selectbox(
        "Localidade",
        options=list(municipality_by_code),
        format_func=lambda code: (
            f"{municipality_by_code[code]['name']} ({code})"
        ),
    )
    try:
        municipality = api.get_municipality(selected_code)
    except DashboardAPIError as exc:
        st.error(f"Falha ao consultar localidade: {exc}")
        return

    _show_evidence_cards(st, municipality)
    st.subheader("Premissas hipotéticas")
    st.caption("Os valores abaixo são informados pelo usuário e não são dados observados.")
    with st.form("analysis_form"):
        budget = st.number_input(
            "Teto hipotético de investimento (R$)",
            min_value=0.0,
            value=None,
            placeholder="Obrigatório para executar",
            step=10000.0,
            help="Premissa hipotética obrigatória para comparar o cenário com o teto.",
        )
        base_cost = _optional_number(
            st,
            "Custo base estimado (R$)",
            "base_cost",
            "Estimativa opcional informada pelo usuário.",
        )
        cost_per_anchor = _optional_number(
            st,
            "Custo estimado por âncora (R$)",
            "cost_per_anchor",
            "Estimativa opcional; não é orçamento de engenharia.",
        )
        monthly_revenue = _optional_number(
            st,
            "Receita mensal hipotética por âncora (R$)",
            "monthly_revenue",
            "Hipótese opcional; não representa receita contratada.",
        )
        horizon = st.number_input(
            "Horizonte da simulação (meses)", min_value=1, max_value=120, value=12
        )
        st.markdown("**Seleção explícita de instituições candidatas**")
        candidate_institutions = municipality.get("anchor_institutions", [])
        selected_anchor_ids = [
            institution["institution_id"]
            for institution in candidate_institutions
            if st.checkbox(
                f"{institution['name']} · "
                f"{display_label(institution['institution_type'])}",
                key=f"anchor_{institution['institution_id']}",
                value=False,
            )
        ]
        submitted = st.form_submit_button("Executar o Conselho")

    if submitted:
        st.session_state.pop("analysis_result", None)
        if budget is None:
            st.error("Informe o teto hipotético para executar a simulação.")
        else:
            st.session_state["analysis_budget_brl"] = budget
            payload = {
                "municipality_code": selected_code,
                "parameters": {
                    "budget_ceiling_brl": budget,
                    "estimated_base_cost_brl": base_cost,
                    "estimated_cost_per_anchor_brl": cost_per_anchor,
                    "hypothetical_monthly_anchor_revenue_brl": monthly_revenue,
                    "scenario_horizon_months": horizon,
                },
                "selected_anchor_ids": selected_anchor_ids,
            }
            with st.spinner("Executando pareceres e cenários..."):
                try:
                    st.session_state["analysis_result"] = api.create_analysis(payload)
                    st.session_state["analysis_budget_brl"] = budget
                except DashboardAPIError as exc:
                    if exc.status_code in {502, 503}:
                        partial_result = exc.payload
                        if isinstance(partial_result, dict) and partial_result.get(
                            "analysis_id"
                        ):
                            st.session_state["analysis_result"] = partial_result
                            st.warning(
                                "Análise degradada: a API retornou resultado parcial e erros."
                            )
                        else:
                            st.error(str(exc))
                        st.info(
                            "Verifique a configuração local do provedor e revise os erros."
                        )
                    else:
                        st.error(str(exc))

    result = st.session_state.get("analysis_result")
    if result and result.get("municipality", {}).get("municipality_code") == selected_code:
        _render_opinions(st, result)
        _render_bridges(st, result)
        _render_scenarios(
            st, result, st.session_state.get("analysis_budget_brl")
        )
        _render_guardian_and_audit(st, result, api)
    api.close()


render_dashboard()
