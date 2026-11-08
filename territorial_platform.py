"""Estudos territoriais dinâmicos sob demanda."""

from __future__ import annotations

from datetime import datetime
from time import perf_counter
import re
import unicodedata

import folium
from folium.plugins import HeatMap
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import folium_static
from shapely.geometry import box, shape

from config import CENARIOS_ORCAMENTO, COMMUNITY_CONFIG, PHASE_COLORS
from territorial_case import cause_counts, indicators, local_ranking, simulate_selected_segments
from territorial_dynamic import municipality_options, select_territory
from territorial_science import combined_table, mechanism_flags, mechanism_table, phase_severity, scientific_summary
from territorial_road_audit import audit_road_positions, road_geojson, ROAD_TOLERANCE_M, SOURCE as ROAD_SOURCE
from territorial_historical_audit import audit_historical_positions, segment_history_quality


KINDS = ("Município", "Estado", "Brasil", "Região Metropolitana", "Municípios selecionados", "Entorno de município")


def territory_pdf_filename(kind: str, name: str, uf: str, code: str | None, date: datetime | None = None) -> str:
    scope = unicodedata.normalize("NFKD", kind).encode("ascii", "ignore").decode().lower().replace(" ", "_")
    label = "espirito_santo" if kind == "Estado" and uf == "ES" else name
    slug = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug).strip("_")
    identity = f"_{code}" if kind == "Município" and code else ""
    return f"relatorio_territorial_{scope}_{slug}_{uf.lower()}{identity}_{(date or datetime.now()):%Y%m%d}.pdf"


def _format(value, digits=0):
    if value is None or pd.isna(value):
        return "Não estimável"
    return f"{value:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _map(data: pd.DataFrame, meta: dict, ranking: pd.DataFrame) -> None:
    geographic = data.dropna(subset=["latitude", "longitude"])
    geographic = geographic.loc[geographic.latitude.between(-34, 5.5) & geographic.longitude.between(-74, -32)]
    if geographic.empty:
        st.info("Mapa indisponível: nenhuma ocorrência tem coordenada válida no recorte.")
        return
    sample = geographic.sort_values("id").head(500)
    center = [sample.latitude.median(), sample.longitude.median()]
    view = folium.Map(location=center, zoom_start=11 if meta.get("codigo_ibge") else 8, tiles="OpenStreetMap")
    for geom in meta.get("geometrias", []):
        folium.GeoJson(geom.__geo_interface__, name="Limite municipal IBGE 2025",
                       style_function=lambda _: {"color": "#1D4ED8", "weight": 2, "fillOpacity": .08}).add_to(view)
    if meta.get("uf") == "ES":
        envelope = box(float(sample.longitude.min())-.08, float(sample.latitude.min())-.08,
                       float(sample.longitude.max())+.08, float(sample.latitude.max())+.08)
        roads = [feature for feature in road_geojson()["features"]
                 if shape(feature["geometry"]).intersects(envelope)]
        if roads:
            folium.GeoJson({"type": "FeatureCollection", "features": roads}, name="Traçado SNV/DNIT 202507A",
                           style_function=lambda _: {"color": "#475569", "weight": 2, "opacity": .65},
                           tooltip=folium.GeoJsonTooltip(fields=["vl_br"], aliases=["BR:"])).add_to(view)
    events = folium.FeatureGroup(name="Ocorrências PRF")
    for row in sample.itertuples():
        folium.CircleMarker([row.latitude, row.longitude], radius=3, color="#F59E0B",
                            fill=True, fill_opacity=.7, tooltip=f"PRF ID {row.id}").add_to(events)
    events.add_to(view)
    if len(sample) > 1:
        heat = folium.FeatureGroup(name="Concentração de coordenadas PRF", show=False)
        HeatMap(sample[["latitude", "longitude"]].to_numpy().tolist(), radius=14, blur=12).add_to(heat)
        heat.add_to(view)
    candidate = folium.FeatureGroup(name="Centros médios dos segmentos")
    if not ranking.empty:
        for row in ranking.head(50).itertuples():
            if pd.notna(row.latitude_media) and pd.notna(row.longitude_media) and row.n_acidentes_total >= 2:
                folium.Marker([row.latitude_media, row.longitude_media],
                              icon=folium.Icon(color="purple", icon="info-sign"),
                              tooltip=f"{row.trecho_id}: centro médio, não local de poste").add_to(candidate)
    candidate.add_to(view)
    folium.LayerControl().add_to(view)
    folium_static(view, width=850, height=500)
    st.caption(f"{len(sample)} de {len(geographic)} ocorrências com coordenada válida exibidas. Pontos laranja: registros PRF; camada de calor opcional: concentração de coordenadas registradas, sujeita a pontos repetidos; marcadores roxos: centros médios exploratórios; polígonos azuis: limites IBGE; linhas cinzas no ES: SNV/DNIT 202507A. Fora do ES, o traçado viário não está disponível nesta implantação. Não há localização proposta de postes.")


def _evidence() -> dict:
    with st.expander("Evidências opcionais da atividade extensionista — Vila Velha", expanded=False):
        st.caption("Preencha somente com evidência verificável; nenhum dado é enviado ou salvo fora desta sessão.")
        video = st.text_input("Vídeo demonstrativo", key="territory_video")
        linkedin = st.text_input("Publicação no LinkedIn", key="territory_linkedin")
        date = st.text_input("Data da apresentação", key="territory_date")
        participants = st.number_input("Participantes efetivamente registrados", min_value=0, value=0, key="territory_participants")
        comments = st.text_area("Comentários e síntese das interações", key="territory_comments")
        outcome = st.text_area("Resultados observados da apresentação", key="territory_outcome")
        feedback = st.text_area("Feedback voluntário, sem dados pessoais", key="territory_feedback")
    return {"video_demonstrativo": video, "publicacao_linkedin": linkedin, "data_divulgacao": date,
            "participantes_registrados": int(participants) if participants else None,
            "sintese_interacoes": comments, "resultados_apresentacao": outcome,
            "feedback_voluntario": feedback}


def render_territorial_platform(analyzer) -> None:
    st.title("Estudos Territoriais")
    st.caption("Comunidade extensionista oficial: Vila Velha (ES). O território abaixo é escolhido pelo usuário e não altera essa identificação acadêmica.")
    source = getattr(analyzer, "data", None)
    if source is None:
        source = analyzer.filtered_data
    if source is None or source.empty:
        st.warning("Carregue microdados PRF antes de selecionar um território.")
        return
    available_years = sorted(source["ano"].dropna().astype(int).unique())
    default_years = [year for year in available_years if year in COMMUNITY_CONFIG["periodo_principal"]]
    years = st.multiselect("Período — anos disponíveis", available_years, default=default_years, key="territory_years")
    if not years:
        st.warning("Selecione ao menos um ano.")
        return
    if any(year >= datetime.now().year for year in years):
        st.warning("O ano corrente ou futuro pode estar parcial na base carregada.")
    base = source.loc[source["ano"].isin(years)]
    kind = st.selectbox("Abrangência", KINDS, key="territory_kind")
    uf_options = sorted(base["uf"].dropna().astype(str).str.upper().unique())
    uf = st.selectbox("UF", uf_options, index=uf_options.index("ES") if "ES" in uf_options else 0, key="territory_uf") if kind != "Brasil" else "ES"
    options = municipality_options(base, uf) if kind in ("Município", "Municípios selecionados", "Entorno de município") else []
    municipality = "Vila Velha" if "Vila Velha" in options else (options[0] if options else "")
    chosen = st.selectbox("Município", options, index=options.index(municipality) if options else 0, key="territory_city") if kind in ("Município", "Entorno de município") and options else municipality
    names = st.multiselect("Municípios comparados", options, default=[municipality] if municipality else [], key="territory_cities") if kind == "Municípios selecionados" else []
    distance = st.slider("Distância do entorno ao limite municipal (km)", 1, 100, 20, key="territory_distance") if kind == "Entorno de município" else 20
    selected, meta = select_territory(base, kind, uf, chosen, tuple(names), float(distance))
    meta["abrangencia"] = kind
    if selected.empty:
        st.warning("Sem registros elegíveis neste recorte e período. Escolha explicitamente outra abrangência ou anos.")
        return
    name = meta["nome"]
    st.subheader(f"{name}{' — ' + uf if kind not in ('Brasil', 'Estado') else ''}")
    st.caption(f"Código IBGE: {meta.get('codigo_ibge') or 'não aplicável'} | Anos: {', '.join(map(str, years))} | Método: {meta['metodo']}")
    for detail in meta.get("detalhes", []):
        st.caption(f"Reconciliação IBGE/PRF — {detail.get('nome', detail.get('municipio', name))}: {detail.get('rotulos_prf', 0)} rótulos PRF; {detail.get('pontos_confirmados', 0)} pontos no polígono; {detail.get('rotulo_externo', 0)} rótulos com ponto externo; {detail.get('ponto_interno_rotulo_outro', 0)} pontos internos com outro rótulo; {detail.get('apenas_rotulo', 0)} registros sem ponto incluídos pelo rótulo.")
        if detail.get("limite"):
            st.warning(detail["limite"])
    metrics = indicators(selected)
    national = indicators(base)
    metrics_cols = st.columns(4)
    for col, label, value in zip(metrics_cols, ("Acidentes únicos", "Plena noite", "Óbitos", "Óbitos / 100 acidentes"),
                                 (metrics["acidentes"], metrics["noturnos"], metrics["obitos"], metrics["obitos_por_100"])):
        col.metric(label, _format(value, 2 if "100" in label else 0))
    st.dataframe(pd.DataFrame({"Indicador": ["Acidentes", "Óbitos", "Feridos graves"], name: [metrics["acidentes"], metrics["obitos"], metrics["feridos_graves"]],
                               "Brasil, base carregada": [national["acidentes"], national["obitos"], national["feridos_graves"]]}),
                 hide_index=True, width="stretch")
    if base["uf"].dropna().nunique() != 27:
        st.caption("A coluna Brasil representa somente a base carregada; não há cobertura das 27 UFs.")
    if kind == "Brasil":
        st.info("Rankings, mapa e relatório científicos nacionais permanecem nos módulos nacionais.")
        return
    state_data, state_meta = select_territory(base, "Estado", uf)
    state_metrics = indicators(state_data)
    st.caption(f"Comparação de óbitos por 100 acidentes — {name}: {_format(metrics['obitos_por_100'], 2)} (N={metrics['acidentes']}); {uf}: {_format(state_metrics['obitos_por_100'], 2)} (N={state_metrics['acidentes']}); Brasil carregado: {_format(national['obitos_por_100'], 2)} (N={national['acidentes']}). Comparação descritiva, sem ajuste para exposição ao tráfego. Referência estadual: {state_meta['metodo']}.")
    causes_data = getattr(analyzer, "causas_data", None)
    if causes_data is None:
        causes_data = analyzer.filtered_causas
    flags = mechanism_flags(selected, causes_data)
    st.subheader("Visibilidade Noturna, Percepção e Capacidade de Reação")
    st.write(scientific_summary(selected, flags, name))
    st.caption("Faróis, contraste, distância de percepção, tempo de reação e frenagem, velocidade, chuva, neblina e ofuscamento são mecanismos físicos possíveis, não medições diretas nesta base. Reação tardia não comprova ausência de postes. Referência técnica: [FHWA, visibilidade noturna](https://highways.dot.gov/safety/other/visibility/nighttime-visibility-overview).")
    table = mechanism_table(flags)
    st.dataframe(table, hide_index=True, width="stretch")
    if not table.empty:
        st.plotly_chart(px.bar(table, x="Fator registrado", y="Ocorrências associadas", color="Fase", barmode="group",
                               color_discrete_map={"Plena Noite": PHASE_COLORS["Plena Noite"], "Pleno dia": PHASE_COLORS["Pleno dia"]}), width="stretch")
        if table["Ocorrências associadas"].lt(5).any():
            st.caption("Algumas células têm menos de cinco ocorrências; percentuais são instáveis. Nenhuma significância estatística é afirmada.")
    severity = phase_severity(flags)
    if not severity.empty:
        st.markdown("**Gravidade por fase do dia**")
        st.dataframe(severity, hide_index=True, width="stretch")
        st.plotly_chart(px.bar(severity, x="Fase", y="Óbitos por 100 acidentes", color="Fase",
                               color_discrete_map=PHASE_COLORS), width="stretch")
        if {"Acidentes fatais", "Acidentes"}.issubset(severity):
            stacked = severity[["Fase", "Acidentes fatais", "Acidentes"]].copy()
            stacked["Acidentes sem óbito"] = stacked["Acidentes"] - stacked["Acidentes fatais"]
            stacked = stacked.melt("Fase", value_vars=["Acidentes fatais", "Acidentes sem óbito"],
                                   var_name="Gravidade", value_name="Ocorrências")
            st.plotly_chart(px.bar(stacked, x="Fase", y="Ocorrências", color="Gravidade", barmode="stack"), width="stretch")
        st.caption("IC de Wilson de 95% descreve a incerteza da proporção de acidentes fatais, pressupondo ocorrências independentes; não corrige exposição ao tráfego nem confundimento. Não foi realizado teste de causalidade.")
    if {"fase_dia_oficial", "tipo_acidente"}.issubset(flags):
        types = (flags.groupby(["fase_dia_oficial", "tipo_acidente"], observed=True).size()
                 .reset_index(name="Ocorrências").loc[lambda frame: frame["Ocorrências"].gt(0)])
        if not types.empty:
            most_common = types.groupby("tipo_acidente")["Ocorrências"].sum().nlargest(8).index
            st.plotly_chart(px.bar(types.loc[types["tipo_acidente"].isin(most_common)],
                                   x="tipo_acidente", y="Ocorrências", color="fase_dia_oficial", barmode="group",
                                   color_discrete_map=PHASE_COLORS), width="stretch")
    combined = combined_table(flags)
    if not combined.empty:
        st.markdown("**Fase × meteorologia × reação × gravidade**")
        st.dataframe(combined, hide_index=True, width="stretch")
        heat = combined.loc[combined["Reação registrada"]].groupby(["condicao_metereologica", "fase_dia_oficial"], observed=True)["ocorrencias"].sum().reset_index()
        if not heat.empty:
            pivot = heat.pivot(index="condicao_metereologica", columns="fase_dia_oficial", values="ocorrencias").fillna(0)
            st.plotly_chart(px.imshow(pivot, color_continuous_scale="Blues", labels={"color": "Ocorrências"}), width="stretch")
    ranking = local_ranking(selected)
    historical = None
    historical_summary = None
    if uf == "ES" and kind in ("Município", "Região Metropolitana", "Municípios selecionados", "Entorno de município"):
        geographic_name = pd.Series(name if kind == "Município" else None, index=selected.index)
        historical = audit_historical_positions(selected, geographic_name)
        historical_summary = historical["status_localizacao"].value_counts().to_dict()
        ranking = segment_history_quality(ranking, selected, historical)
    st.subheader("Segmentos Prioritários para Investigação")
    if uf == "ES" and selected["br"].astype(str).str.replace(r"\D", "", regex=True).eq("447").any():
        st.warning("BR-447: a posição de ocorrências históricas não comprova a configuração atual ou operação de trechos novos. Consulte a auditoria SNV antes de interpretar o mapa ou ranking.")
    _map(selected, meta, ranking)
    if not ranking.empty:
        st.caption("Score heurístico = (5 × óbitos noturnos + 3 × feridos graves noturnos + feridos leves noturnos + 2 × acidentes noturnos) × (1 + fração noturna). Sem denominador de tráfego; não prova falta de iluminação. Triagem SNV: P=espacialmente plausível, D=divergência, I=insuficiente; nenhuma categoria certifica operação histórica.")
        ranking_columns = ["ranking", "trecho_id", "n_acidentes_total", "n_acidentes_noturnos",
                           "acidentes_fatais_noturno", "mortos_noturno", "feridos_graves_total",
                           "feridos_graves_noturno", "score_iluminacao_solar"]
        if "triagem_snv" in ranking:
            ranking_columns.append("triagem_snv")
        st.dataframe(ranking[ranking_columns], hide_index=True, width="stretch")
        with st.expander("Detalhes de um segmento", expanded=False):
            segment_name = st.selectbox("Segmento prioritário para investigação", ranking["trecho_id"].tolist(), key="territory_segment_detail")
            segment = ranking.loc[ranking["trecho_id"].eq(segment_name)].iloc[0]
            records = selected.loc[
                selected["br"].astype(str).eq(str(segment.br))
                & selected["uf"].astype(str).eq(str(segment.uf))
                & selected["km"].between(segment.km_inicio, segment.km_fim, inclusive="left")
            ]
            segment_causes = cause_counts(records, causes_data)
            st.write(f"{segment_name}; {len(records)} ocorrências, {int(segment.n_acidentes_noturnos)} noturnas, {int(segment.mortos_total)} óbitos, {int(segment.feridos_graves_total)} feridos graves. Município PRF mais frequente: {records['municipio'].mode().iloc[0] if not records.empty else 'Não verificado'}.")
            st.caption("Causas associadas: " + ("; ".join(f"{row.causa_acidente}: {row.ocorrencias_associadas}" for row in segment_causes.head(6).itertuples(index=False)) if not segment_causes.empty else "Não verificadas"))
            st.caption("Qualidade da localização: exige conferência de BR/KM e traçado. Situação da iluminação: Não verificada.")
    road_summary = None
    if uf == "ES" and kind in ("Município", "Região Metropolitana", "Municípios selecionados", "Entorno de município"):
        road = audit_road_positions(selected)
        road_summary = road["situacao_rodovia"].value_counts().to_dict()
        st.caption(f"Confronto histórico SNV por mês de referência: {historical_summary}. Nenhuma correspondência é certificação operacional; datas de publicação não verificadas.")
        if selected["br"].astype(str).str.replace(r"\D", "", regex=True).eq("447").any():
            st.warning("BR-447: versões históricas registram trechos planejados, pavimentados e em obra, além de mudanças de quilometragem. Pontos e segmentos permanecem em triagem; não se infere configuração física atual ou local para postes.")
        st.caption(f"Confronto SNV/DNIT ES 202507A: {road_summary}; tolerância transversal {ROAD_TOLERANCE_M:.0f} m. Proximidade não confirma pista ou marco histórico.")
        with st.expander("Auditoria BR/KM e coordenadas", expanded=False):
            from territorial_case import territorial_audit, territorial_diagnostics
            ibge_audit = territorial_audit(base)
            diagnostics = territorial_diagnostics(ibge_audit)
            st.caption(f"Na malha compacta dos sete municípios da Grande Vitória: {diagnostics['divergencias']} divergências entre município PRF e posição IBGE; {diagnostics['pontos_prf_es_fora_malha_es']} ponto(s) fora da malha estadual. Para outros municípios do ES, a reconciliação do recorte usa a malha IBGE integral indicada acima. Registros divergentes permanecem disponíveis para inspeção.")
            cols = [column for column in ("id", "ano", "uf", "municipio", "br", "km", "latitude", "longitude") if column in selected]
            selected_audit = selected[cols].join(ibge_audit[["municipio_por_coordenada", "divergencia_municipio_coordenada", "situacao_localizacao"]], how="left").join(road)
            st.dataframe(selected_audit, hide_index=True, width="stretch")
            st.markdown("**Confronto com referência histórica SNV por ocorrência**")
            st.dataframe(historical, hide_index=True, width="stretch")
            divergent = base.loc[ibge_audit.index[ibge_audit["divergencia_municipio_coordenada"]]]
            if not divergent.empty:
                divergence_table = divergent[[column for column in cols if column in divergent]].join(
                    ibge_audit[["municipio_por_coordenada", "situacao_localizacao"]], how="left"
                )
                st.markdown("**Registros ES com divergência município/coordenada**")
                st.dataframe(divergence_table, hide_index=True, width="stretch")
            st.caption(f"Fonte do traçado: {ROAD_SOURCE}. Situação da iluminação: não verificada.")
    st.subheader("Simulação econômica condicional")
    segment_options = ranking["trecho_id"].tolist() if not ranking.empty else []
    chosen_segments = st.multiselect("Segmentos a simular", segment_options, default=segment_options[:min(5, len(segment_options))], key="territory_segments")
    subset_ranking = ranking.loc[ranking["trecho_id"].isin(chosen_segments)] if not ranking.empty else ranking
    scenario = st.selectbox("Cenário de custo", list(CENARIOS_ORCAMENTO), index=3,
                            format_func=lambda key: CENARIOS_ORCAMENTO[key]["nome"], key="territory_scenario")
    spacing = st.number_input("Espaçamento longitudinal hipotético (m)", min_value=20.0, max_value=100.0, value=50.0, step=5.0, key="territory_spacing")
    finance = simulate_selected_segments(selected, subset_ranking, scenario, spacing, allow_exploratory_vpl=False) if not subset_ranking.empty else {}
    if finance:
        st.write(f"{finance['segmentos']} segmentos; {_format(finance['extensao_km'],1)} km; {_format(finance['postes'])} postes hipotéticos; CAPEX R$ {_format(finance['capex'],2)}; manutenção anual R$ {_format(finance['manutencao_anual'],2)}; reserva de baterias R$ {_format(finance['reserva_reposicoes_baterias_15_anos'],2)}.")
        st.caption("Segmentos incluídos neste custo: " + "; ".join(subset_ranking["trecho_id"].astype(str).tolist()))
        st.warning("VPL territorial não calculado: falta estimativa causal local de redução de sinistros. Custos são hipóteses, não economia realizada.")
    st.caption("Uma fileira a cada 50 m é hipótese geométrica. Pista dupla, curvas, acessos e pedestres exigem projeto luminotécnico conforme ABNT NBR 5101:2024.")
    st.subheader("Relatórios")
    report_key = (kind, uf, name, meta.get("codigo_ibge"), tuple(years), tuple(chosen_segments), scenario, spacing,
                  st.session_state.get("cached_file_signature"), len(selected), len(base),
                  int(pd.util.hash_pandas_object(selected[["id", "ano"]], index=False).sum()) if "id" in selected else None)
    if st.button("Gerar Relatório do Território Selecionado", key="territory_pdf"):
        from territorial_report_dynamic import generate_selected_territory_report
        from config import get_current_rss_mb
        pdf_started = perf_counter()
        st.session_state["territory_generated"] = (report_key, generate_selected_territory_report(selected, base, meta, flags, ranking, finance, road_summary, historical_summary, subset_ranking))
        st.session_state["last_territory_pdf_diagnostic"] = {"seconds": round(perf_counter() - pdf_started, 3), "rss_mib": round(get_current_rss_mb(), 1)}
    generated = st.session_state.get("territory_generated")
    if generated and generated[0] == report_key:
        st.download_button("Baixar PDF do território selecionado", generated[1], territory_pdf_filename(kind, name, uf, meta.get("codigo_ibge")), "application/pdf")
    st.subheader("Aplicação comunitária oficial: Vila Velha (ES)")
    st.write("Sistema desenvolvido: sim. Sistema disponibilizado: sim. Aplicação comunitária realizada: somente após evidências verificáveis de apresentação ou participação.")
    if uf == "ES" and kind == "Município" and meta.get("codigo_ibge") == COMMUNITY_CONFIG["codigo_ibge"]:
        evidence = _evidence()
        if st.button("Gerar Relatório Extensionista — Vila Velha (ES)", key="territory_extension_pdf"):
            from territorial_case import territorial_audit
            from territorial_pdf import generate_territorial_report
            causes = cause_counts(selected, causes_data)
            pdf = generate_territorial_report(name, selected, base, causes, ranking, subset_ranking, finance,
                                              territorial_audit(base), evidence, historical_summary)
            st.session_state["territory_extension_generated"] = (report_key, tuple(sorted(evidence.items())), pdf)
        ext = st.session_state.get("territory_extension_generated")
        if ext and ext[:2] == (report_key, tuple(sorted(evidence.items()))):
            st.download_button("Baixar PDF extensionista de Vila Velha", ext[2], "relatorio_extensionista_vila_velha.pdf", "application/pdf")
    else:
        st.info("O relatório extensionista é exclusivo da comunidade oficial Vila Velha (ES); selecione esse município para gerá-lo.")
