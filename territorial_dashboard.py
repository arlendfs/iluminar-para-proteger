"""Módulo Streamlit sob demanda do estudo de caso de Vila Velha."""

from __future__ import annotations

from datetime import datetime

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import folium_static

from config import COMMUNITY_CONFIG, CENARIOS_ORCAMENTO, COLOR_PALETTE, PHASE_COLORS
from territorial_case import (
    CORRIDOR_BRS, MALHA_SOURCE, SCOPES, SCOPE_BRASIL, SCOPE_ENTORNO,
    SCOPE_ES, SCOPE_METRO, SCOPE_VILA, cause_counts, indicators,
    local_ranking, municipal_mesh, principal_period, select_scope,
    simulate_selected_segments, territorial_audit, territorial_diagnostics,
)


def _number(value: float | int | None, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "Não estimável"
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _money(value: float) -> str:
    return "R$ " + _number(value, 2)


def _metric_table(scope: str, local: dict, national: dict, national_available: bool) -> pd.DataFrame:
    rows = [
        ("Acidentes únicos", "acidentes", 0),
        ("Acidentes noturnos", "noturnos", 0),
        ("Acidentes diurnos", "diurnos", 0),
        ("Óbitos", "obitos", 0),
        ("Feridos graves", "feridos_graves", 0),
        ("Feridos leves", "feridos_leves", 0),
        ("Acidentes fatais (%)", "percentual_fatais", 2),
        ("Óbitos por 100 acidentes", "obitos_por_100", 2),
    ]
    return pd.DataFrame({
        "Indicador": [label for label, _, _ in rows],
        scope: [_number(local[key], decimals) for _, key, decimals in rows],
        "Brasil - referência": [_number(national[key], decimals) if national_available else "Indisponível" for _, key, decimals in rows],
    })


def _render_map(selected: pd.DataFrame, audit: pd.DataFrame, ranking: pd.DataFrame) -> None:
    geojson, geometries = municipal_mesh()
    vila = geometries[COMMUNITY_CONFIG["codigo_ibge"]]
    center = vila.representative_point()
    map_view = folium.Map(location=[center.y, center.x], zoom_start=11, tiles="OpenStreetMap")
    folium.GeoJson(
        geojson, name="Limites municipais IBGE 2025",
        style_function=lambda feature: {
            "color": "#F59E0B" if feature["properties"]["codigo_ibge"] == "3205200" else "#64748B",
            "weight": 3 if feature["properties"]["codigo_ibge"] == "3205200" else 1,
            "fillOpacity": 0.08,
        },
        tooltip=folium.GeoJsonTooltip(fields=["municipio"], aliases=["Município:"]),
    ).add_to(map_view)
    regional = selected.loc[selected.index.intersection(audit.index)]
    regional = regional.loc[audit.loc[regional.index, "dentro_metropole"] & audit.loc[regional.index, "coordenada_valida"]]
    sample = regional.sort_values("id").head(500)
    events = folium.FeatureGroup(name="Ocorrências PRF com coordenada")
    for row in sample.itertuples():
        label = audit.loc[row.Index, "situacao_localizacao"]
        color = "#F59E0B" if label.startswith("Vila Velha") else "#38BDF8"
        folium.CircleMarker(
            location=[row.latitude, row.longitude], radius=3, color=color,
            fill=True, fill_opacity=0.75,
            tooltip=f"Ocorrência {row.id} - {label}",
        ).add_to(events)
    events.add_to(map_view)
    recurrent = ranking.loc[(ranking["n_acidentes_total"] >= 2) & ranking["latitude_media"].notna() & ranking["longitude_media"].notna()] if not ranking.empty else pd.DataFrame()
    segments_layer = folium.FeatureGroup(name="Segmentos com recorrência (posição média dos registros)")
    for row in recurrent.head(100).itertuples():
        folium.Marker(
            [row.latitude_media, row.longitude_media],
            icon=folium.Icon(color="purple", icon="info-sign"),
            tooltip=f"{row.trecho_id}: {row.n_acidentes_total} ocorrências; posição média, não traçado viário",
        ).add_to(segments_layer)
    segments_layer.add_to(map_view)
    folium.LayerControl().add_to(map_view)
    folium_static(map_view, width=850, height=520)
    st.caption(
        f"Mapa: {len(sample)} de {len(regional)} ocorrências metropolitanas com coordenadas válidas "
        "(máximo de 500 pontos por desempenho). Os marcadores roxos são posições médias de segmentos "
        "com recorrência, não locais propostos para instalação. Limites: IBGE 2025, EPSG:4326."
    )


def _extension_evidence() -> dict:
    with st.expander("Evidências opcionais da atividade extensionista", expanded=False):
        st.caption("Preencha somente após a divulgação efetiva. Os campos ficam nesta sessão e entram apenas no PDF gerado aqui.")
        video = st.text_input("Link do vídeo demonstrativo", key="vv_video")
        linkedin = st.text_input("Link da publicação no LinkedIn", key="vv_linkedin")
        date = st.text_input("Data da divulgação (se realizada)", key="vv_divulgacao")
        participants = st.text_input("Número de participantes efetivamente registrados", key="vv_participantes")
        interaction = st.text_area("Síntese das interações e comentários", key="vv_interacoes")
        results = st.text_area("Resultados da apresentação pública", key="vv_resultados")
    if participants.strip() and not participants.strip().isdigit():
        st.warning("O número de participantes deve ser um inteiro não negativo; este campo não será incluído no PDF.")
        participants = ""
    return {
        "video_demonstrativo": video.strip(), "publicacao_linkedin": linkedin.strip(),
        "data_divulgacao": date.strip(),
        "participantes_registrados": int(participants) if participants.strip() else None,
        "sintese_interacoes": interaction.strip(), "resultados_apresentacao": results.strip(),
    }


def render_territorial_case(analyzer) -> None:
    st.title("Segurança Viária e Visibilidade Noturna: Vila Velha e seus Acessos Rodoviários")
    st.caption("Aplicação comunitária de Ciência de Dados para investigação de acidentes e avaliação exploratória de iluminação solar.")
    st.markdown(
        "A comunidade beneficiária é **Vila Velha (ES)**. O painel usa microdados de acidentes em rodovias federais "
        "registrados pela PRF para apoiar uma apresentação pública e a discussão metropolitana sobre segurança viária. "
        "Não cobre todas as ruas da cidade, não identifica residência das vítimas e não registra implantação física de postes."
    )
    full_data = getattr(analyzer, "data", None)
    base = principal_period(full_data if full_data is not None else analyzer.filtered_data)
    if base.empty:
        st.warning("Não há registros de 2021 a 2025 na base carregada. Carregue arquivos desse período explicitamente.")
        return
    national_available = "uf" in base and base["uf"].dropna().nunique() == 27
    audit = territorial_audit(base)
    scope = st.selectbox("Abrangência do estudo de caso", SCOPES, index=0, key="vv_scope")
    if scope == SCOPE_BRASIL and not national_available:
        st.warning("A base carregada não cobre as 27 UFs; a referência Brasil está indisponível. Carregue microdados nacionais e selecione o recorte novamente.")
        return
    selected = select_scope(base, audit, scope)
    if selected.empty:
        st.warning("Não há ocorrências elegíveis neste recorte. Selecione explicitamente um recorte maior no seletor acima.")
        return
    local = indicators(selected)
    national = indicators(base)
    years = sorted(int(year) for year in selected["ano"].dropna().unique())
    period = f"{years[0]}-{years[-1]}" if years else "não informado"
    st.caption(f"Período disponível: {period}; recorte: {scope}; base carregada independente dos filtros dos módulos nacionais. Fonte: PRF. N = {_number(local['acidentes'])} ocorrências únicas.")
    if not national_available:
        st.warning("A base carregada não cobre as 27 UFs; indicadores nacionais não são exibidos como referência completa.")
    if scope == SCOPE_VILA:
        diag = territorial_diagnostics(audit)
        st.info(
            f"Reconciliação territorial: {diag['rotulo_vila']} registros rotulados Vila Velha pela PRF; "
            f"{diag['vila_confirmada']} pontos dentro da malha IBGE 2025; "
            f"{diag['ponto_vila_rotulo_outro']} pontos internos rotulados como outro município e "
            f"{diag['rotulo_vila_ponto_fora']} rótulos Vila Velha com ponto fora do limite; "
            f"{diag['vila_sem_coordenada']} registros locais somente pelo rótulo; "
            f"{diag['divergencias']} divergências município/coordenada no ES, incluindo "
            f"{diag['pontos_prf_es_fora_malha_es']} ponto fora da malha estadual. "
            "O total local inclui pontos confirmados dentro do limite e registros municipais sem coordenadas; "
            "rótulos Vila Velha com ponto fora do limite ficam fora do total."
        )
    st.subheader("Indicadores do recorte e comparação nacional")
    cols = st.columns(4)
    for col, title, key in zip(cols, ["Acidentes únicos", "Acidentes noturnos", "Óbitos", "Óbitos / 100 acidentes"],
                               ["acidentes", "noturnos", "obitos", "obitos_por_100"]):
        col.metric(title, _number(local[key], 2 if key == "obitos_por_100" else 0))
    st.dataframe(_metric_table(scope, local, national, national_available), hide_index=True, use_container_width=True)
    if local["acidentes"] < 200:
        st.warning("A amostra deste recorte é pequena para projeções econômicas territoriais; taxas podem ser instáveis e não devem ser generalizadas.")
    st.caption("Os tamanhos amostrais acima são de acidentes, não de moradores. Diferenças entre recortes não demonstram efeito da iluminação.")

    st.subheader("Análise científica observacional")
    if local["noturnos"] and local["diurnos"]:
        st.write(
            f"No recorte {scope}, no período {period}, foram identificadas {_number(local['acidentes'])} ocorrências "
            f"em rodovias federais, das quais {_number(local['noturnos'])} ocorreram durante a plena noite. "
            f"A taxa de óbitos por 100 acidentes foi {_number(local['taxa_noturna'], 2)} no período noturno "
            f"e {_number(local['taxa_diurna'], 2)} no pleno dia."
        )
    else:
        st.write(f"O recorte {scope} contém {_number(local['acidentes'])} ocorrências, sem base suficiente para comparar taxas noturnas e diurnas.")
    st.caption("Hipótese: menor visibilidade pode afetar detecção de obstáculos e percepção de riscos, entre outros mecanismos. Acidente noturno não implica falta de postes nem causalidade da iluminação.")
    phase = selected["fase_dia_oficial"].value_counts().rename_axis("Fase do dia").reset_index(name="Ocorrências")
    st.plotly_chart(px.bar(phase, x="Fase do dia", y="Ocorrências", color="Fase do dia", color_discrete_map=PHASE_COLORS), use_container_width=True)
    causes = cause_counts(selected, analyzer.filtered_causas)
    accident_types = selected["tipo_acidente"].value_counts().head(10).rename_axis("Tipo de acidente").reset_index(name="Ocorrências")
    left, right = st.columns(2)
    with left:
        st.markdown("**Causas associadas**")
        if not causes.empty:
            st.plotly_chart(px.bar(causes.head(10), x="ocorrencias_associadas", y="causa_acidente", orientation="h", labels={"ocorrencias_associadas": "Ocorrências associadas", "causa_acidente": "Causa"}, color_discrete_sequence=[COLOR_PALETTE["contagem"]]), use_container_width=True)
            st.caption("Uma ocorrência pode ter múltiplas causas; as barras não são categorias exclusivas.")
        else:
            st.info("Causas não disponíveis para o recorte.")
    with right:
        st.markdown("**Tipos de acidente**")
        st.plotly_chart(px.bar(accident_types, x="Ocorrências", y="Tipo de acidente", orientation="h", color_discrete_sequence=[COLOR_PALETTE["contagem"]]), use_container_width=True)
    if not causes.empty:
        mechanism = causes.loc[causes["causa_acidente"].astype(str).str.contains(
            "reação|reacao|velocidade|ultrapassagem|dormindo|álcool|alcool", case=False, regex=True
        )]
        if not mechanism.empty:
            st.caption("Fatores selecionados para investigação (ocorrências associadas, não exclusivas): " +
                       "; ".join(f"{row.causa_acidente}: {_number(row.ocorrencias_associadas)}" for row in mechanism.itertuples(index=False)))
    for column, title in (("condicao_metereologica", "Condição meteorológica"), ("tipo_pista", "Tipo de pista"), ("tracado_via", "Traçado da via")):
        if column in selected:
            values = selected[column].value_counts().head(8)
            if not values.empty:
                st.caption(f"{title}: " + "; ".join(f"{name}: {_number(count)}" for name, count in values.items()))
    people = analyzer.filtered_pessoas
    if people is not None and not people.empty and {"id", "tipo_envolvido"}.issubset(people):
        involvement = people.loc[people["id"].isin(selected["id"]), "tipo_envolvido"].value_counts().head(8)
        if not involvement.empty:
            st.caption("Tipos de envolvimento (pessoas, não acidentes): " + "; ".join(f"{name}: {_number(count)}" for name, count in involvement.items()))
    st.warning(
        "Limitações: a PRF não fornece inventário completo de iluminação; fase do dia não mede lux; "
        "a visibilidade não foi medida diretamente; não há comprovação de residência das vítimas. "
        "Resultados observacionais e diferenças entre períodos não demonstram causalidade."
    )

    st.subheader("Mapa territorial e segmentos registrados")
    ranking = local_ranking(selected)
    _render_map(selected, audit, ranking)
    if ranking.empty:
        st.info("Não há segmentos com BR e KM válidos neste recorte.")
    else:
        st.caption(f"{len(ranking)} segmentos com BR e KM elegíveis no recorte ativo. Score heurístico de severidade e concentração noturna, sem validação causal ou inventário de iluminação.")
        columns = ["ranking", "trecho_id", "n_acidentes_total", "n_acidentes_noturnos", "mortos_noturno", "score_iluminacao_solar", "confiabilidade_geo"]
        st.dataframe(ranking[columns], hide_index=True, use_container_width=True)
    st.caption("A rede viária mudou entre 2021 e 2025. A BR-447 inclui trechos em implantação; ausência de registro em trecho novo não prova segurança. BR-101, BR-262 e BR-447 são referências de investigação, não seleção automática de intervenção.")
    br447 = selected.loc[selected["br"].astype(str).str.replace(r"\D", "", regex=True).eq("447")]
    distinct_coordinates = len(br447[["latitude", "longitude"]].dropna().drop_duplicates())
    st.caption(f"BR-447 no recorte ativo: {len(br447)} ocorrências registradas, com {distinct_coordinates} pares distintos de coordenadas. A localização por BR/KM e a evolução da infraestrutura exigem verificação de campo antes de qualquer inferência sobre trechos específicos.")

    st.subheader("Simulação condicional de iluminação solar")
    if ranking.empty:
        st.info("Sem segmentos observados elegíveis. É possível simular apenas o custo de um segmento hipotético de 2 km.")
        selected_rank = ranking
        scenario_id = st.selectbox("Cenário de custo do exemplo", list(CENARIOS_ORCAMENTO), index=3,
                                   format_func=lambda key: CENARIOS_ORCAMENTO[key]["nome"], key="vv_scenario_example")
        spacing = st.number_input("Espaçamento hipotético do exemplo (m)", min_value=20.0, max_value=100.0,
                                  value=50.0, step=5.0, key="vv_spacing_example")
        finance = simulate_selected_segments(selected, pd.DataFrame({"trecho_id": ["Exemplo hipotético"]}), scenario_id, spacing)
        finance["hipotetico"] = True
        st.metric("CAPEX do exemplo de 2 km", _money(finance["capex"]))
        st.caption("Exemplo de dimensionamento sem localização ou benefício local atribuído. Não representa trecho elegível nem VPL sustentado pela PRF.")
    else:
        options = ranking["trecho_id"].tolist()
        chosen = st.multiselect("Segmentos a simular", options, default=options[:min(5, len(options))], key="vv_segments")
        selected_rank = ranking.loc[ranking["trecho_id"].isin(chosen)]
        scenario_id = st.selectbox("Cenário de custo unitário", list(CENARIOS_ORCAMENTO), index=3, format_func=lambda key: CENARIOS_ORCAMENTO[key]["nome"], key="vv_scenario")
        spacing = st.number_input("Espaçamento hipotético entre postes (m)", min_value=20.0, max_value=100.0, value=50.0, step=5.0, key="vv_spacing")
        finance = simulate_selected_segments(selected, selected_rank, scenario_id, spacing)
        if finance:
            fcols = st.columns(4)
            for col, title, value in zip(fcols, ["Extensão hipotética", "Postes estimados", "Custo unitário", "CAPEX"],
                                         [f"{_number(finance['extensao_km'], 1)} km", _number(finance["postes"]), _money(finance["custo_unitario"]), _money(finance["capex"])]):
                col.metric(title, value)
            st.caption(f"Manutenção anual: {_money(finance['manutencao_anual'])}; reserva para duas reposições de bateria em 15 anos: {_money(finance['reserva_reposicoes_baterias_15_anos'])}. Espaçamento de 50 m é hipótese preliminar, não projeto fotométrico.")
            if finance["vpl_exploratorio_disponivel"]:
                st.dataframe(pd.DataFrame({"Redução hipotética de acidentes noturnos": ["20%", "35%", "50%"], "VPL social exploratório (R$)": [_money(value) for value in finance["sensibilidade"].values()]}), hide_index=True)
                st.caption("VPL social representa custos socioeconômicos potencialmente evitados, não receita. A redução de óbitos no modelo supõe proporcionalidade adicional; custos sociais e ano-base ainda são provisórios. Taxa social de desconto hipotética: 8% a.a.; horizonte: 15 anos.")
            else:
                st.warning("A amostra ou a seleção de segmentos não sustenta VPL territorial. Exibimos apenas custos hipotéticos; nenhuma economia local é publicada.")
    st.caption("Protótipo conceitual: poste 8 m, LED 40 W, painel 240 Wp, bateria LiFePO4, telemetria e sensor de movimento. A ABNT NBR 5101:2024 exige estudo fotométrico e validação de campo; não há postes implantados pelo projeto.")

    st.subheader("Aplicação na Comunidade de Vila Velha")
    st.write("A aplicação extensionista consiste em disponibilizar e apresentar o sistema digital, compartilhar as análises e incentivar a discussão pública sobre segurança viária. A atividade de apresentação só será descrita como realizada quando houver evidências registradas.")
    st.markdown("[Dashboard](https://iluminar-para-proteger.streamlit.app/) · [Código-fonte](https://github.com/arlendfs/iluminar-para-proteger) · [Conversor](https://github.com/arlendfs/parquet-conversor)")
    evidence = _extension_evidence()
    st.markdown("**ODS 11 - Cidades e Comunidades Sustentáveis.** O acesso comunitário à informação e a análise exploratória podem subsidiar o planejamento de mobilidade mais segura. Não se afirma implantação física nem melhora medida de indicadores oficiais da ODS.")
    report_key = (
        scope, tuple(selected_rank["trecho_id"]) if not selected_rank.empty else (),
        finance.get("cenario"), finance.get("espacamento_m"), len(selected),
        int(selected["id"].sum()), tuple(sorted(evidence.items())),
    )
    if st.button("Gerar Relatório — Estudo de Caso Vila Velha", key="vv_generate_pdf"):
        from territorial_pdf import generate_territorial_report
        pdf = generate_territorial_report(scope, selected, base, causes, ranking, selected_rank, finance, audit, evidence)
        st.session_state["vv_generated_pdf"] = (report_key, pdf)
    generated = st.session_state.get("vv_generated_pdf")
    if generated and generated[0] == report_key:
        st.download_button("Baixar relatório territorial em PDF", generated[1],
                           "relatorio_estudo_caso_vila_velha_" + datetime.now().strftime("%Y%m%d") + ".pdf",
                           "application/pdf", key="vv_download_pdf")
