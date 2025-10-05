import streamlit as st
import pandas as pd
import os
import re
from pandas import DataFrame
from typing import Optional
from config import (
    APP_CONFIG,
    FINANCIAL_PARAMS,
    EFFECTIVENESS_PARAMS,
    ECONOMIC_VALUES,
    DEFAULT_SPACING_M,
    DEFAULT_COMPRIMENTO_TRECHO_KM,
    COLUMN_MAPPING,
    VALUE_STANDARDIZATION,
)


class AccidentAnalyzer:
    def __init__(self):
        self.data = None
        self.filtered_data: Optional[DataFrame] = None

    @st.cache_data
    def load_local_files(_self, data_dir, local_files):
        """Carrega arquivos CSV da pasta local e marca a origem."""
        all_data = []
        for filename in local_files:
            try:
                filepath = os.path.join(data_dir, filename)

                df = pd.read_csv(
                    filepath, encoding="latin1", sep=None, engine="python"
                )
                df["source_file"] = filename
                all_data.append(df)
                st.success(f"Arquivo {filename} carregado com sucesso!")
            except Exception as e:
                st.error(f"Erro ao carregar {filename}: {str(e)}")
                continue

        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            return _self._preprocess_data(combined_df)
        return None

    @st.cache_data
    def load_data(_self, files):
        """Carrega e processa dados em chunks para economizar memória."""
        chunk_list = []
        
        # Pega o tamanho do chunk da configuração
        chunk_size = APP_CONFIG.get("chunk_size", 10000)

        for file in files:
            try:
                filename = getattr(file, "name", "uploaded_file")
                st.write(f"Processando {filename} em blocos de {chunk_size:,} linhas...")
                
                # Cria um leitor de chunks
                csv_reader = pd.read_csv(
                    file,
                    encoding="latin1",
                    sep=None,
                    engine="python",
                    chunksize=chunk_size
                )
                
                # Processa cada chunk individualmente
                for chunk in csv_reader:
                    chunk["source_file"] = filename
                    processed_chunk = _self._preprocess_data(chunk)
                    chunk_list.append(processed_chunk)

                st.success(f"Arquivo {filename} carregado com sucesso!")

            except Exception as e:
                st.error(f"Erro ao carregar {filename}: {str(e)}")
                continue

        if chunk_list:
            # Concatena todos os chunks processados no final
            combined_df = pd.concat(chunk_list, ignore_index=True)
            return combined_df
            
        return None

    def _extract_year_from_text(self, text):
        """Procura um ano (2000-2099) em uma string."""
        if pd.isna(text):
            return None
        s = str(text)
        m = re.search(r"(20[0-9]{2})", s)
        if m:
            try:
                return int(m.group(1))
            except (ValueError, IndexError):
                return None
        return None

    def _preprocess_data(self, df):
        """Preprocessa os dados para análise."""
        df.columns = df.columns.str.lower().str.strip()

        for standard_name, possible_names in COLUMN_MAPPING.items():
            for possible_name in possible_names:
                if (
                    possible_name in df.columns
                    and standard_name not in df.columns
                ):
                    df.rename(
                        columns={possible_name: standard_name}, inplace=True
                    )
                    break

        date_cols = [c for c in df.columns if "data" in c] # Procura por colunas como 'data' ou 'data_inversa'
        if date_cols:
            # Usa a primeira coluna de data encontrada
            df["ano"] = pd.to_datetime(df[date_cols[0]], errors="coerce").dt.year
        
        # Se uma coluna 'ano' já existe e pode preencher valores que a coluna de data não conseguiu
        if "ano" in df.columns and "ano" in df.columns:
             # Converte a coluna 'ano' original para numérico, tratando erros
            original_ano_numeric = pd.to_numeric(df["ano"], errors='coerce')
            # Preenche os valores que ainda estão vazios na nova coluna 'ano'
            if "ano" in df:
                df["ano"] = df["ano"].fillna(original_ano_numeric)
            else:
                df["ano"] = original_ano_numeric

        # Como último recurso, tenta extrair o ano do nome do arquivo
        if "ano" not in df or df["ano"].isnull().all():
            if "source_file" in df.columns:
                df["ano"] = df["source_file"].apply(self._extract_year_from_text)

        # Garante que a coluna 'ano' final seja do tipo numérico para os filtros funcionarem
        if "ano" in df.columns:
            df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype(
                "Int64"
            )
        else:
            st.warning("Aviso: Não foi possível determinar a coluna 'ano'.")

        if "fase_dia" in df.columns:
            df["fase_dia"] = df["fase_dia"].astype(str).str.lower().str.strip()
            fase_map = {
                var: std_val
                for std_val, variations in VALUE_STANDARDIZATION[
                    "fase_dia"
                ].items()
                for var in variations
            }
            df["fase_dia"] = df["fase_dia"].map(fase_map).fillna("diurno")
        else:
            df["fase_dia"] = "Não informado"

        if "estado_fisico" in df.columns:
            df["mortos"] = (
                df["estado_fisico"].astype(str).str.lower().str.strip()
                == "óbito"
            ).astype(int)

        numeric_cols = [
            "mortos",
            "feridos_leves",
            "feridos_graves",
            "ileso",
            "km",
            "latitude",
            "longitude",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            else:
                df[col] = 0

        df["total_feridos"] = df["feridos_leves"] + df["feridos_graves"]
        df["total_vitimas"] = df["mortos"] + df["total_feridos"]

        if "uf" in df.columns:
            df["uf"] = (
                df["uf"]
                .astype(str)
                .str.strip()
                .str.upper()
                .replace({"NAN": None})
            )
            df.dropna(subset=["uf"], inplace=True)
        else:
            st.warning("Coluna 'uf' não encontrada.")

        if "br" in df.columns:
            df["br"] = (
                pd.to_numeric(df["br"], errors="coerce")
                .astype("Int64")
                .astype(str)
                .replace("<NA>", "N/A")
            )
        else:
            st.info("Coluna 'br' (rodovia) não encontrada.")

        return df

    def apply_filters(self, df, filters):
        """Aplica filtros aos dados."""
        if df is None:
            return pd.DataFrame()
        filtered_df = df.copy()
        if filters.get("anos") and "ano" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["ano"].isin(filters["anos"])]
        if filters.get("ufs"):
            filtered_df = filtered_df[filtered_df["uf"].isin(filters["ufs"])]
        if filters.get("brs"):
            filtered_df = filtered_df[
                filtered_df["br"].isin([str(br) for br in filters["brs"]])
            ]
        return filtered_df

    def analyze_top_n(
        self,
        df,
        top_n: int = 100,
        comprimento_km: float = DEFAULT_COMPRIMENTO_TRECHO_KM,
        spacing_m: float = DEFAULT_SPACING_M,
    ):
        """Analisa os top N trechos prioritários e calcula métricas financeiras."""
        if df.empty:
            return pd.DataFrame(), {}

        df_res = df.copy()

        roi_results = df_res.apply(
            lambda row: calculate_roi(
                total_mortos=row.get("mortos", 0),
                total_feridos_graves=row.get("feridos_graves", 0),
                total_feridos_leves=row.get("feridos_leves", 0),
                comprimento_trecho_km=comprimento_km,
                spacing_m=spacing_m,
            ),
            axis=1,
            result_type="expand",
        )
        roi_results.columns = [
            "roi_10anos",
            "payback_anos",
            "investimento_trecho",
            "economia_anual_trecho",
            "acidentes_evitados_ano",
        ]

        df_res = pd.concat([df_res, roi_results], axis=1)

        df_res = df_res.sort_values("score_prioridade", ascending=False)
        top_df = df_res.head(top_n)

        reducao = EFFECTIVENESS_PARAMS["reducao_acidentes_noturnos"]
        economia_mortos = (top_df["mortos"].sum() * reducao) * ECONOMIC_VALUES[
            "valor_vida_estatistica"
        ]
        economia_graves = (
            top_df["feridos_graves"].sum() * reducao
        ) * ECONOMIC_VALUES["custo_medio_acidente_grave"]
        economia_leves = (
            top_df["feridos_leves"].sum() * reducao
        ) * ECONOMIC_VALUES["custo_medio_acidente_leve"]

        agregados = {
            "top_df": top_df,
            "investimento_total": float(top_df["investimento_trecho"].sum()),
            "economia_anual": float(top_df["economia_anual_trecho"].sum()),
            "economia_mortos": float(economia_mortos),
            "economia_graves": float(economia_graves),
            "economia_leves": float(economia_leves),
            "vitimas_evitadas_total": float(
                top_df["acidentes_evitados_ano"].sum()
            ),
        }
        return df_res, agregados
    


def calculate_roi(
    total_mortos,
    total_feridos_graves,
    total_feridos_leves,
    comprimento_trecho_km: float,
    spacing_m: float,
):
    """
    Calcula o ROI e outras métricas financeiras para um único trecho.
    """
    reducao_estimada = EFFECTIVENESS_PARAMS["reducao_acidentes_noturnos"]

    posts_por_trecho = (1000 / spacing_m) * comprimento_trecho_km
    investimento_total_trecho = (
        posts_por_trecho * FINANCIAL_PARAMS["custo_poste_solar"]
    )

    economia_mortos = (total_mortos * reducao_estimada) * ECONOMIC_VALUES[
        "valor_vida_estatistica"
    ]
    economia_graves = (
        total_feridos_graves * reducao_estimada
    ) * ECONOMIC_VALUES["custo_medio_acidente_grave"]
    economia_leves = (
        total_feridos_leves * reducao_estimada
    ) * ECONOMIC_VALUES["custo_medio_acidente_leve"]
    valor_economizado_ano = economia_mortos + economia_graves + economia_leves

    payback_anos = (
        investimento_total_trecho / valor_economizado_ano
        if valor_economizado_ano > 0
        else float("inf")
    )

    custo_manutencao_anual_total = posts_por_trecho * FINANCIAL_PARAMS.get(
        "custo_manutencao_anual_por_poste", 0
    )
    investimento_e_manutencao_10_anos = investimento_total_trecho + (
        custo_manutencao_anual_total * 10
    )

    if investimento_e_manutencao_10_anos > 0:
        economia_total_10_anos = valor_economizado_ano * 10
        roi_10_anos = (
            (economia_total_10_anos - investimento_e_manutencao_10_anos)
            / investimento_e_manutencao_10_anos
        ) * 100
    else:
        roi_10_anos = 0.0

    acidentes_evitados_ano = (
        total_mortos + total_feridos_graves + total_feridos_leves
    ) * reducao_estimada

    return (
        roi_10_anos,
        payback_anos,
        investimento_total_trecho,
        valor_economizado_ano,
        acidentes_evitados_ano,
    )
