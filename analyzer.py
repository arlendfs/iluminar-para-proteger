"""
Módulo Principal de Análise de Acidentes Rodoviários.
Integra ingestão, validação, deduplicação, segmentação e avaliação financeira.
Mantém compatibilidade total com a interface do Streamlit e relatórios.
"""

import os
import re
import gc
import time
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
import numpy as np
import streamlit as st
from config import (
    APP_CONFIG,
    FINANCIAL_PARAMS,
    EFFECTIVENESS_PARAMS,
    ECONOMIC_VALUES,
    DEFAULT_SPACING_M,
    DEFAULT_COMPRIMENTO_TRECHO_KM,
    DEFAULT_TRECHOS_TOP_N,
    log_memory_checkpoint,
    get_current_rss_mb,
)
from data_loader import process_raw_dataframe
from segmentation import create_road_segments, rank_segments
from financial_model import avaliar_viabilidade_economica, dimensionar_postes, calcular_capex_opex
from reaction_analysis import analyze_visibility_and_reaction


class AccidentAnalyzer:
    """
    Classe controladora da análise de acidentes rodoviários da PRF.
    Preserva dados brutos, dados em nível de ocorrência, pessoas, veículos e causas.
    Implementa processamento incremental para estabilidade de memória no Streamlit Cloud.
    """

    def __init__(self):
        self.data: Optional[pd.DataFrame] = None
        self.pessoas_data: Optional[pd.DataFrame] = None
        self.veiculos_data: Optional[pd.DataFrame] = None
        self.causas_data: Optional[pd.DataFrame] = None
        self.quality_summary: Dict[str, Any] = {}
        self.filtered_data: Optional[pd.DataFrame] = None
        self.filtered_pessoas: Optional[pd.DataFrame] = None
        self.filtered_veiculos: Optional[pd.DataFrame] = None
        self.filtered_causas: Optional[pd.DataFrame] = None
        self.top_segments: Optional[pd.DataFrame] = None
        self.financial_analysis: Optional[Dict[str, Any]] = None
        self.visibility_analysis: Optional[Dict[str, Any]] = None

    def _consolidate_incremental_tables(
        self,
        all_oc: List[pd.DataFrame],
        all_pes: List[pd.DataFrame],
        all_veic: List[pd.DataFrame],
        all_caus: List[pd.DataFrame],
        all_qual: List[Dict[str, Any]],
        source_name: str,
    ) -> Optional[pd.DataFrame]:
        """
        Consolida tabelas relacionais de múltiplos arquivos mantendo desduplicação global.
        Libera referências intermediárias e coleta lixo para estabilidade de RAM.
        """
        if not all_oc:
            return None

        t0 = time.time()
        log_memory_checkpoint("Iniciando consolidação relacional global")

        # 1. Concatenação e desduplicação global de ocorrências por ID
        ocorrencias = pd.concat(all_oc, ignore_index=True).drop_duplicates(subset=["id"])
        del all_oc
        gc.collect()

        # 2. Concatenação e desduplicação global de pessoas por (id, pesid)
        if all_pes:
            pessoas = pd.concat(all_pes, ignore_index=True).drop_duplicates(subset=["id", "pesid"])
            del all_pes
        else:
            pessoas = pd.DataFrame()
        gc.collect()

        # 3. Concatenação e desduplicação global de veículos por (id, id_veiculo)
        if all_veic:
            veiculos = pd.concat(all_veic, ignore_index=True).drop_duplicates(subset=["id", "id_veiculo"])
            del all_veic
        else:
            veiculos = pd.DataFrame()
        gc.collect()

        # 4. Concatenação e desduplicação global de causas
        if all_caus:
            causas = pd.concat(all_caus, ignore_index=True).drop_duplicates()
            del all_caus
        else:
            causas = pd.DataFrame()
        gc.collect()

        # 5. Consolidação estatística do Resumo de Qualidade
        total_linhas_brutas = sum(q.get("registros_brutos", 0) for q in all_qual)
        total_ocorrencias = len(ocorrencias)
        total_pessoas = len(pessoas)
        total_veiculos = len(veiculos)
        desdobramentos = total_linhas_brutas - total_ocorrencias

        com_km_count = int(ocorrencias["km_limpo"].notna().sum()) if "km_limpo" in ocorrencias.columns else 0
        sem_km_count = total_ocorrencias - com_km_count
        sem_km_df = ocorrencias[ocorrencias["km_limpo"].isna()] if "km_limpo" in ocorrencias.columns else pd.DataFrame()
        mortos_sem_km = int(sem_km_df["mortos"].sum()) if not sem_km_df.empty and "mortos" in sem_km_df.columns else 0
        feridos_sem_km = int(sem_km_df["total_feridos"].sum()) if not sem_km_df.empty and "total_feridos" in sem_km_df.columns else 0

        com_geo_count = int((ocorrencias["latitude_limpa"].notna() & ocorrencias["longitude_limpa"].notna()).sum()) if ("latitude_limpa" in ocorrencias.columns and "longitude_limpa" in ocorrencias.columns) else 0
        sem_geo_count = total_ocorrencias - com_geo_count

        total_mortos = int(ocorrencias["mortos"].sum()) if "mortos" in ocorrencias.columns else 0
        total_graves = int(ocorrencias["feridos_graves"].sum()) if "feridos_graves" in ocorrencias.columns else 0
        total_leves = int(ocorrencias["feridos_leves"].sum()) if "feridos_leves" in ocorrencias.columns else 0
        total_feridos = int(ocorrencias["total_feridos"].sum()) if "total_feridos" in ocorrencias.columns else 0
        acidentes_fatais = int(ocorrencias["acidente_fatal"].sum()) if "acidente_fatal" in ocorrencias.columns else 0

        # Estatísticas de idade agregadas
        idades_validas_count = int(pessoas["idade_valida_flag"].sum()) if "idade_valida_flag" in pessoas.columns else 0
        idades_invalidas_count = total_pessoas - idades_validas_count
        idades_maior_110 = sum(q.get("idades_superiores_110_anos", 0) for q in all_qual)

        # Mortos por tipo de envolvimento
        mortos_envolvidos = (
            pessoas[pessoas["mortos"] > 0]["tipo_envolvido"].value_counts().to_dict()
            if "tipo_envolvido" in pessoas.columns else {}
        )

        anos_presentes = sorted([int(a) for a in ocorrencias["ano"].dropna().unique()]) if "ano" in ocorrencias.columns else []
        anos_incompletos = []
        if "ano" in ocorrencias.columns and "mes" in ocorrencias.columns:
            for a in anos_presentes:
                meses = ocorrencias[ocorrencias["ano"] == a]["mes"].dropna().unique()
                if len(meses) < 12 and a >= 2024:
                    anos_incompletos.append((a, sorted(list(meses))))

        # Agregar divergências de classificação auditadas
        todas_divergencias = []
        for q in all_qual:
            todas_divergencias.extend(q.get("divergencias_classificacao", []))

        quality_summary = {
            "arquivo_origem": source_name,
            "registros_brutos": total_linhas_brutas,
            "ocorrencias_unicas": total_ocorrencias,
            "pessoas_unicas_pesid": total_pessoas,
            "linhas_sem_pesid": sum(q.get("linhas_sem_pesid", 0) for q in all_qual),
            "veiculos_unicos": total_veiculos,
            "desdobramentos_consolidados": desdobramentos,
            "duplicatas_linhas_evitadas": desdobramentos,
            "taxa_consolidacao": (total_linhas_brutas / total_ocorrencias) if total_ocorrencias > 0 else 1.0,
            "ocorrencias_com_km": com_km_count,
            "ocorrencias_sem_km": sem_km_count,
            "mortos_sem_km": mortos_sem_km,
            "feridos_sem_km": feridos_sem_km,
            "perc_com_km": (com_km_count / total_ocorrencias * 100) if total_ocorrencias > 0 else 0.0,
            "ocorrencias_com_geo": com_geo_count,
            "ocorrencias_sem_geo": sem_geo_count,
            "perc_com_geo": (com_geo_count / total_ocorrencias * 100) if total_ocorrencias > 0 else 0.0,
            "total_mortos_real": total_mortos,
            "total_feridos_graves_real": total_graves,
            "total_feridos_leves_real": total_leves,
            "total_feridos_real": total_feridos,
            "acidentes_fatais_real": acidentes_fatais,
            "taxa_acidentes_fatais_pct": (acidentes_fatais / total_ocorrencias * 100) if total_ocorrencias > 0 else 0.0,
            "obitos_por_100_acidentes": (total_mortos / total_ocorrencias * 100) if total_ocorrencias > 0 else 0.0,
            "idades_validas": idades_validas_count,
            "idades_inconsistentes_ou_ausentes": idades_invalidas_count,
            "idades_superiores_110_anos": idades_maior_110,
            "divergencias_classificacao": todas_divergencias,
            "mortos_por_envolvimento": mortos_envolvidos,
            "anos_presentes": anos_presentes,
            "anos_incompletos": anos_incompletos,
            "data_minima": str(ocorrencias["data_inversa"].min()) if "data_inversa" in ocorrencias.columns else "N/A",
            "data_maxima": str(ocorrencias["data_inversa"].max()) if "data_inversa" in ocorrencias.columns else "N/A",
        }

        self.data = ocorrencias
        self.pessoas_data = pessoas
        self.veiculos_data = veiculos
        self.causas_data = causas
        self.quality_summary = quality_summary
        self.filtered_data = ocorrencias
        self.filtered_pessoas = pessoas
        self.filtered_veiculos = veiculos
        self.filtered_causas = causas

        log_memory_checkpoint("Consolidação concluída", start_time=t0)
        return self.data

    def load_local_files(self, data_dir: str, local_files: List[str]) -> Optional[pd.DataFrame]:
        """
        Carrega arquivos da pasta local de forma estritamente incremental:
        Lê e extrai tabelas normalizadas arquivo por arquivo, descartando DataFrames
        brutos imediatamente para respeitar o limite de 1 GB de RAM do Streamlit Cloud.
        """
        if not local_files:
            return None

        all_oc, all_pes, all_veic, all_caus, all_qual = [], [], [], [], []
        progress_bar = st.progress(0, text="Processando arquivos...")
        status_text = st.empty()

        for idx, filename in enumerate(local_files, start=1):
            filepath = os.path.join(data_dir, filename)
            status_text.text(f"Lendo e desduplicando [{idx}/{len(local_files)}]: {filename}...")
            t_file = time.time()
            log_memory_checkpoint(f"Início processamento arquivo: {filename}")

            try:
                if filename.lower().endswith(".parquet"):
                    df = pd.read_parquet(filepath)
                    df["source_file"] = filename
                elif filename.lower().endswith(".csv"):
                    try:
                        df = pd.read_csv(filepath, sep=";", encoding="latin1", low_memory=False)
                    except Exception:
                        df = pd.read_csv(filepath, sep=None, engine="python", encoding="latin1", on_bad_lines="warn")
                    df["source_file"] = filename
                else:
                    continue

                # Processa o arquivo individualmente gerando tabelas compactadas
                oc, pes, veic, caus, qual = process_raw_dataframe(df, source_name=filename, return_relational=True)
                
                # Descarte imediato do DataFrame bruto da memória
                del df
                gc.collect()

                all_oc.append(oc)
                all_pes.append(pes)
                all_veic.append(veic)
                all_caus.append(caus)
                all_qual.append(qual)

                log_memory_checkpoint(f"Concluído arquivo {filename}", start_time=t_file)

            except Exception as e:
                st.error(f"❌ Erro ao processar {filename}: {str(e)}")

            progress_bar.progress(int(idx / len(local_files) * 90))

        status_text.text("Consolidando tabelas relacionais globais...")
        res = self._consolidate_incremental_tables(all_oc, all_pes, all_veic, all_caus, all_qual, ", ".join(local_files))
        progress_bar.progress(100)
        status_text.empty()
        progress_bar.empty()

        if res is not None:
            qual = self.quality_summary
            st.success(
                f"✅ Processamento incremental concluído: {qual['ocorrencias_unicas']:,} ocorrências únicas "
                f"a partir de {qual['registros_brutos']:,} registros brutos ({qual['desdobramentos_consolidados']:,} desdobramentos consolidados)."
            )
        return res

    def load_data(self, files: List[Any]) -> Optional[pd.DataFrame]:
        """
        Carrega arquivos enviados por upload de forma incremental:
        processa arquivo a arquivo e libera os brutos imediatamente da RAM.
        """
        if not files:
            return None

        all_oc, all_pes, all_veic, all_caus, all_qual = [], [], [], [], []
        file_names = []
        progress_bar = st.progress(0, text="Processando arquivos enviados...")

        for idx, file in enumerate(files, start=1):
            filename = getattr(file, "name", f"upload_{idx}")
            file_names.append(filename)
            t_file = time.time()
            log_memory_checkpoint(f"Início upload: {filename}")

            try:
                if filename.lower().endswith(".parquet"):
                    df = pd.read_parquet(file)
                    df["source_file"] = filename
                elif filename.lower().endswith(".csv"):
                    try:
                        df = pd.read_csv(file, sep=";", encoding="latin1", low_memory=False)
                    except Exception:
                        file.seek(0)
                        df = pd.read_csv(file, sep=None, engine="python", encoding="latin1", on_bad_lines="warn")
                    df["source_file"] = filename
                else:
                    continue

                oc, pes, veic, caus, qual = process_raw_dataframe(df, source_name=filename, return_relational=True)
                del df
                gc.collect()

                all_oc.append(oc)
                all_pes.append(pes)
                all_veic.append(veic)
                all_caus.append(caus)
                all_qual.append(qual)
                log_memory_checkpoint(f"Concluído upload {filename}", start_time=t_file)

            except Exception as e:
                st.error(f"❌ Erro ao ler upload {filename}: {str(e)}")

            progress_bar.progress(int(idx / len(files) * 90))

        res = self._consolidate_incremental_tables(all_oc, all_pes, all_veic, all_caus, all_qual, ", ".join(file_names))
        progress_bar.progress(100)
        progress_bar.empty()
        return res

    def apply_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """
        Aplica filtros com consistência estrita em todas as variáveis:
        Ano, UF, BR, Fase do Dia, Condição Meteorológica, Causas,
        Perfil Demográfico (Envolvimento, Sexo, Idade) e Tipo de Veículo.
        
        Garante que, ao filtrar por grupo demográfico, as vítimas de outros
        ocupantes do mesmo sinistro não sejam atribuídas indevidamente ao grupo.
        """
        if df is None or df.empty:
            self.filtered_data = pd.DataFrame()
            self.filtered_pessoas = pd.DataFrame()
            self.filtered_veiculos = pd.DataFrame()
            self.filtered_causas = pd.DataFrame()
            return pd.DataFrame()

        mask = pd.Series(True, index=df.index)

        # Filtro de Anos
        if filters.get("anos") and "ano" in df.columns:
            mask &= df["ano"].isin(filters["anos"])

        # Filtro de UFs (Estados)
        if filters.get("ufs") and "uf" in df.columns:
            mask &= df["uf"].isin(filters["ufs"])

        # Filtro de BRs (Rodovias)
        if filters.get("brs") and "br" in df.columns:
            brs_sel = set(str(b) for b in filters["brs"])
            todas_brs_nominais = set(str(b) for b in df["br"].dropna().unique() if str(b) != "N/A")
            # Se todas as rodovias nominais foram selecionadas no filtro, preserva as ocorrências nacionais
            # sem BR/KM identificado, garantindo a elegibilidade nacional completa.
            if todas_brs_nominais.issubset(brs_sel) or "N/A" in brs_sel:
                pass
            else:
                mask &= df["br"].isin(brs_sel)

        # Filtro de Fase do Dia
        if filters.get("fase_dia") and len(filters["fase_dia"]) > 0:
            if "fase_dia_oficial" in df.columns:
                mask_fase = df["fase_dia_oficial"].isin(filters["fase_dia"])
                if "fase_dia_agrupada" in df.columns:
                    mask_fase |= df["fase_dia_agrupada"].str.lower().isin([str(f).lower() for f in filters["fase_dia"]])
                mask &= mask_fase
            elif "fase_dia" in df.columns:
                mask &= df["fase_dia"].str.lower().isin([str(f).lower() for f in filters["fase_dia"]])

        # Filtro de Condição Meteorológica
        if filters.get("condicao_meteorologica") and "condicao_metereologica" in df.columns:
            mask &= df["condicao_metereologica"].isin(filters["condicao_meteorologica"])

        filtered_df = df if mask.all() else df[mask]
        ids_validos = set(filtered_df["id"]) if "id" in filtered_df.columns else set()

        # Filtrar causas pelos IDs válidos
        if self.causas_data is not None and not self.causas_data.empty and ids_validos:
            if len(filtered_df) == len(df):
                self.filtered_causas = self.causas_data
            else:
                self.filtered_causas = self.causas_data[self.causas_data["id"].isin(ids_validos)]
        else:
            self.filtered_causas = pd.DataFrame()

        # Filtro opcional por causas selecionadas
        if filters.get("causas_selecionadas") and not self.filtered_causas.empty:
            causas_sel = filters["causas_selecionadas"]
            ids_com_causa = set(
                self.filtered_causas[self.filtered_causas["causa_acidente"].isin(causas_sel)]["id"]
            )
            filtered_df = filtered_df[filtered_df["id"].isin(ids_com_causa)]
            self.filtered_causas = self.filtered_causas[self.filtered_causas["id"].isin(ids_com_causa)]
            ids_validos = set(filtered_df["id"])

        # Filtrar pessoas e veículos pelos IDs válidos de ocorrência
        if self.pessoas_data is not None and not self.pessoas_data.empty and ids_validos:
            if len(filtered_df) == len(df):
                self.filtered_pessoas = self.pessoas_data
            else:
                self.filtered_pessoas = self.pessoas_data[self.pessoas_data["id"].isin(ids_validos)]
        else:
            self.filtered_pessoas = pd.DataFrame()

        if self.veiculos_data is not None and not self.veiculos_data.empty and ids_validos:
            if len(filtered_df) == len(df):
                self.filtered_veiculos = self.veiculos_data
            else:
                self.filtered_veiculos = self.veiculos_data[self.veiculos_data["id"].isin(ids_validos)]
        else:
            self.filtered_veiculos = pd.DataFrame()

        # Filtros Demográficos (tipo_envolvido, sexo, faixa_etaria)
        tem_filtro_demografico = False
        if not self.filtered_pessoas.empty:
            mask_pessoas = pd.Series(True, index=self.filtered_pessoas.index)
            if filters.get("tipos_envolvido") and "tipo_envolvido" in self.filtered_pessoas.columns:
                mask_pessoas &= self.filtered_pessoas["tipo_envolvido"].isin(filters["tipos_envolvido"])
                tem_filtro_demografico = True
            if filters.get("sexos") and "sexo" in self.filtered_pessoas.columns:
                mask_pessoas &= self.filtered_pessoas["sexo"].isin(filters["sexos"])
                tem_filtro_demografico = True
            if filters.get("faixas_etarias") and "faixa_etaria" in self.filtered_pessoas.columns:
                mask_pessoas &= self.filtered_pessoas["faixa_etaria"].isin(filters["faixas_etarias"])
                tem_filtro_demografico = True

            if tem_filtro_demografico:
                self.filtered_pessoas = self.filtered_pessoas[mask_pessoas].copy()
                ids_demograficos = set(self.filtered_pessoas["id"])
                filtered_df = filtered_df[filtered_df["id"].isin(ids_demograficos)].copy()
                ids_validos = set(filtered_df["id"])

                # Atualizar vítimas em filtered_df exclusivamente para o grupo filtrado
                grupo_vitimas = (
                    self.filtered_pessoas.groupby("id", observed=True)
                    .agg(
                        mortos=("mortos", "sum"),
                        feridos_graves=("feridos_graves", "sum"),
                        feridos_leves=("feridos_leves", "sum"),
                        ilesos=("ilesos", "sum"),
                    )
                    .reset_index()
                )
                filtered_df["mortos_total_acidente"] = filtered_df["mortos"]
                filtered_df["feridos_total_acidente"] = filtered_df["total_feridos"]

                map_mortos = dict(zip(grupo_vitimas["id"], grupo_vitimas["mortos"]))
                map_graves = dict(zip(grupo_vitimas["id"], grupo_vitimas["feridos_graves"]))
                map_leves = dict(zip(grupo_vitimas["id"], grupo_vitimas["feridos_leves"]))
                map_ilesos = dict(zip(grupo_vitimas["id"], grupo_vitimas["ilesos"]))

                filtered_df["mortos"] = filtered_df["id"].map(map_mortos).fillna(0).astype(int)
                filtered_df["feridos_graves"] = filtered_df["id"].map(map_graves).fillna(0).astype(int)
                filtered_df["feridos_leves"] = filtered_df["id"].map(map_leves).fillna(0).astype(int)
                filtered_df["total_feridos"] = filtered_df["feridos_graves"] + filtered_df["feridos_leves"]
                filtered_df["ilesos"] = filtered_df["id"].map(map_ilesos).fillna(0).astype(int)
                filtered_df["acidente_fatal"] = (filtered_df["mortos"] > 0).astype(int)

                if not self.filtered_causas.empty:
                    self.filtered_causas = self.filtered_causas[self.filtered_causas["id"].isin(ids_validos)].copy()
                if not self.filtered_veiculos.empty:
                    self.filtered_veiculos = self.filtered_veiculos[self.filtered_veiculos["id"].isin(ids_validos)].copy()

        # Filtro de Veículos
        if filters.get("tipos_veiculo") and not self.filtered_veiculos.empty:
            self.filtered_veiculos = self.filtered_veiculos[
                self.filtered_veiculos["tipo_veiculo"].isin(filters["tipos_veiculo"])
            ].copy()
            ids_veic = set(self.filtered_veiculos["id"])
            filtered_df = filtered_df[filtered_df["id"].isin(ids_veic)].copy()
            ids_validos = set(filtered_df["id"])
            if not self.filtered_pessoas.empty:
                self.filtered_pessoas = self.filtered_pessoas[self.filtered_pessoas["id"].isin(ids_validos)].copy()
            if not self.filtered_causas.empty:
                self.filtered_causas = self.filtered_causas[self.filtered_causas["id"].isin(ids_validos)].copy()

        self.filtered_data = filtered_df
        gc.collect()
        return self.filtered_data

    def analyze_top_n(
        self,
        df: pd.DataFrame,
        top_n: int = DEFAULT_TRECHOS_TOP_N,
        comprimento_km: float = DEFAULT_COMPRIMENTO_TRECHO_KM,
        spacing_m: float = DEFAULT_SPACING_M,
        criterio_ranking: str = "iluminacao_solar",
        anos_base: Optional[float] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Segmenta as rodovias em trechos contínuos de 'comprimento_km',
        classifica o Top N de acordo com o score de prioridade para iluminação solar,
        e calcula a viabilidade econômica exclusivamente para os trechos contemplados.
        """
        if df.empty:
            return pd.DataFrame(), {}

        # Determinar anos na base para cálculo de taxa anualizada
        if anos_base is None or anos_base <= 0:
            if "ano" in df.columns and not df["ano"].dropna().empty:
                anos_unicos = df["ano"].dropna().unique()
                anos_base = float(len(anos_unicos))
                # Se houver apenas 2026 e tiver apenas 8 meses, fator é 8/12 = 0.67
                if len(anos_unicos) == 1 and 2026 in anos_unicos and "mes" in df.columns:
                    meses_count = df["mes"].nunique()
                    anos_base = max(meses_count / 12.0, 0.1)
            else:
                anos_base = 1.0

        # Segmentação das rodovias
        segmentos, info_seg = create_road_segments(df, comprimento_km=comprimento_km)
        if segmentos.empty:
            return pd.DataFrame(), {}

        top_df = rank_segments(segmentos, top_n=top_n, criterio=criterio_ranking)

        # Avaliação econômica e financeira completa
        fin_eval = avaliar_viabilidade_economica(
            top_segments_df=top_df,
            n_trechos=len(top_df),
            comprimento_km=comprimento_km,
            espacamento_m=spacing_m,
            anos_base_dados=anos_base,
        )

        # Adicionar métricas financeiras individuais por trecho para exibição na tabela
        # Investimento por trecho: (comprimento_km * 1000 / spacing_m) * custo_poste
        postes_trecho = int(np.ceil((comprimento_km * 1000.0) / spacing_m))
        invest_trecho = postes_trecho * FINANCIAL_PARAMS["custo_poste_solar"]
        top_df["investimento_trecho"] = invest_trecho

        # Economia anual individual do trecho
        taxa_red = EFFECTIVENESS_PARAMS["reducao_acidentes_noturnos"]
        top_df["vidas_salvas_ano_trecho"] = (top_df["mortos_noturno"] / anos_base) * taxa_red
        top_df["graves_evitados_ano_trecho"] = (top_df["feridos_graves_noturno"] / anos_base) * taxa_red
        top_df["leves_evitados_ano_trecho"] = (top_df["feridos_leves_noturno"] / anos_base) * taxa_red

        top_df["economia_anual_trecho"] = (
            top_df["vidas_salvas_ano_trecho"] * ECONOMIC_VALUES["valor_vida_estatistica"] +
            top_df["graves_evitados_ano_trecho"] * ECONOMIC_VALUES["custo_medio_acidente_grave"] +
            top_df["leves_evitados_ano_trecho"] * ECONOMIC_VALUES["custo_medio_acidente_leve"]
        )

        opex_anual_trecho = postes_trecho * FINANCIAL_PARAMS["custo_manutencao_anual_por_poste"]
        beneficio_liq_trecho = top_df["economia_anual_trecho"] - opex_anual_trecho
        top_df["payback_anos"] = np.where(
            beneficio_liq_trecho > 0,
            invest_trecho / beneficio_liq_trecho,
            np.nan
        )

        # ROI 10 anos simples do trecho
        custo_10anos_trecho = invest_trecho + (opex_anual_trecho * 10)
        top_df["roi_10anos"] = np.where(
            custo_10anos_trecho > 0,
            ((top_df["economia_anual_trecho"] * 10 - custo_10anos_trecho) / custo_10anos_trecho) * 100,
            0.0
        )

        # Colunas com nomes esperados pela interface antiga
        top_df["trecho"] = top_df["trecho_id"]
        top_df["n_acidentes"] = top_df["n_acidentes_noturnos"]
        top_df["mortos"] = top_df["mortos_noturno"]
        top_df["total_feridos"] = top_df["total_feridos_noturno"]
        top_df["score_prioridade"] = top_df["score_iluminacao_solar"]
        top_df["acidentes_evitados_ano"] = (top_df["n_acidentes_noturnos"] / anos_base) * taxa_red

        agregados = {
            "top_df": top_df,
            "investimento_total": fin_eval["capex_total"],
            "economia_anual": fin_eval["beneficio_anual_bruto"],
            "economia_liquida_anual": fin_eval["beneficio_anual_liquido"],
            "economia_mortos": fin_eval["beneficios"]["economia_vidas_ano"],
            "economia_graves": fin_eval["beneficios"]["economia_graves_ano"],
            "economia_leves": fin_eval["beneficios"]["economia_leves_ano"],
            "vitimas_evitadas_total": (
                fin_eval["beneficios"]["vidas_salvas_ano"] +
                fin_eval["beneficios"]["graves_evitados_ano"] +
                fin_eval["beneficios"]["leves_evitados_ano"]
            ),
            "vidas_salvas_ano": fin_eval["beneficios"]["vidas_salvas_ano"],
            "graves_evitados_ano": fin_eval["beneficios"]["graves_evitados_ano"],
            "leves_evitados_ano": fin_eval["beneficios"]["leves_evitados_ano"],
            "vpl": fin_eval["vpl"],
            "tir": fin_eval["tir"],
            "payback_simples_anos": fin_eval["payback_simples_anos"],
            "payback_descontado_anos": fin_eval["payback_descontado_anos"],
            "roi_descontado_pct": fin_eval["roi_descontado_pct"],
            "roi_simples_pct": fin_eval["roi_simples_pct"],
            "cenarios": fin_eval["cenarios_sensibilidade"],
            "dimensionamento": fin_eval["dimensionamento"],
            "tabela_fluxo_caixa_df": fin_eval.get("tabela_fluxo_caixa_df"),
            "info_segmentacao": info_seg,
            "anos_base": anos_base,
        }

        self.top_segments = top_df
        self.financial_analysis = agregados

        return top_df, agregados


def calculate_roi(
    total_mortos: float,
    total_feridos_graves: float,
    total_feridos_leves: float,
    comprimento_trecho_km: float = DEFAULT_COMPRIMENTO_TRECHO_KM,
    spacing_m: float = DEFAULT_SPACING_M,
    anos_base: float = 1.0,
) -> Tuple[float, float, float, float, float]:
    """
    Função de compatibilidade que calcula indicadores financeiros
    para um único segmento viário.
    """
    taxa_red = EFFECTIVENESS_PARAMS["reducao_acidentes_noturnos"]
    postes = int(np.ceil((comprimento_trecho_km * 1000.0) / spacing_m))
    investimento = postes * FINANCIAL_PARAMS["custo_poste_solar"]
    opex_anual = postes * FINANCIAL_PARAMS["custo_manutencao_anual_por_poste"]

    fator = max(anos_base, 0.1)
    mortos_ano = (total_mortos / fator) * taxa_red
    graves_ano = (total_feridos_graves / fator) * taxa_red
    leves_ano = (total_feridos_leves / fator) * taxa_red

    economia_anual = (
        mortos_ano * ECONOMIC_VALUES["valor_vida_estatistica"] +
        graves_ano * ECONOMIC_VALUES["custo_medio_acidente_grave"] +
        leves_ano * ECONOMIC_VALUES["custo_medio_acidente_leve"]
    )

    beneficio_liquido_anual = economia_anual - opex_anual
    payback_anos = (investimento / beneficio_liquido_anual) if beneficio_liquido_anual > 0 else float("inf")

    custo_10anos = investimento + (opex_anual * 10)
    roi_10anos = (((economia_anual * 10) - custo_10anos) / custo_10anos * 100) if custo_10anos > 0 else 0.0
    acidentes_evitados_ano = mortos_ano + graves_ano + leves_ano

    return (
        roi_10anos,
        payback_anos,
        investimento,
        economia_anual,
        acidentes_evitados_ano,
    )
