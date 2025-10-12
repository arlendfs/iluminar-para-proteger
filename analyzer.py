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
    
    @staticmethod
    def _detectar_formato_arquivo(file):
        """Detecta se o arquivo é CSV ou Parquet baseado na extensão."""
        filename = getattr(file, "name", str(file))
        if filename.lower().endswith('.parquet'):
            return 'parquet'
        elif filename.lower().endswith('.csv'):
            return 'csv'
        else:
            return 'unknown'

    @staticmethod
    def _carregar_arquivo_unico(file, chunk_size=None):
        """
        Carrega um único arquivo, detectando automaticamente se é CSV ou Parquet.
        Retorna um DataFrame ou um iterador de chunks (para CSV).
        """
        formato = AccidentAnalyzer._detectar_formato_arquivo(file)
        filename = getattr(file, "name", "uploaded_file")
        
        if formato == 'parquet':
            # Parquet é sempre carregado inteiro (já é eficiente)
            try:
                df = pd.read_parquet(file)
                st.success(f"✅ Arquivo Parquet {filename} carregado com sucesso!")
                return df, 'parquet'
            except Exception as e:
                st.error(f"❌ Erro ao carregar Parquet {filename}: {str(e)}")
                return None, None
                
        elif formato == 'csv':
            try:
                if chunk_size:
                    # Retorna um iterador de chunks
                    csv_reader = pd.read_csv(
                        file,
                        encoding="latin1",
                        sep=None,
                        engine="python",
                        chunksize=chunk_size,
                        on_bad_lines='warn'
                    )
                    return csv_reader, 'csv_chunks'
                else:
                    # Carrega CSV completo
                    df = pd.read_csv(
                        file,
                        encoding="latin1",
                        sep=None,
                        engine="python",
                        on_bad_lines='warn'
                    )
                    st.success(f"✅ Arquivo CSV {filename} carregado com sucesso!")
                    return df, 'csv'
            except Exception as e:
                st.error(f"❌ Erro ao carregar CSV {filename}: {str(e)}")
                return None, None
        else:
            st.error(f"❌ Formato de arquivo não suportado: {filename}. Use CSV ou Parquet.")
            return None, None

    @st.cache_data
    def load_local_files(_self, data_dir, local_files):
        """
        Carrega arquivos CSV ou Parquet da pasta local e marca a origem.
        Detecta automaticamente o formato.
        """
        all_data = []
        for filename in local_files:
            try:
                filepath = os.path.join(data_dir, filename)
                
                # Detectar formato pelo nome do arquivo
                if filename.lower().endswith('.parquet'):
                    df = pd.read_parquet(filepath)
                    df["source_file"] = filename
                    all_data.append(df)
                    st.success(f"✅ Arquivo Parquet {filename} carregado com sucesso!")
                    
                elif filename.lower().endswith('.csv'):
                    try:
                        # Tenta com engine padrão (mais rápido)
                        df = pd.read_csv(
                            filepath,
                            encoding="latin1",
                            low_memory=False
                        )
                    except:
                        # Se falhar, usa python para detectar separador
                        df = pd.read_csv(
                            filepath, 
                            encoding="latin1", 
                            sep=None, 
                            engine="python",
                            on_bad_lines='warn'
                        )
                    
                    df["source_file"] = filename
                    all_data.append(df)
                    st.success(f"✅ Arquivo CSV {filename} carregado com sucesso!")
                    
                else:
                    st.warning(f"⚠️ Arquivo {filename} ignorado (formato não suportado)")
                    continue
                    
            except Exception as e:
                st.error(f"❌ Erro ao carregar {filename}: {str(e)}")
                continue

        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            return _self._preprocess_data(combined_df)
        return None
    
    @st.cache_data
    def load_data(_self, files):
        """
        Carrega e processa dados de arquivos CSV ou Parquet.
        Processa em fila para evitar estouro de memória no Streamlit Cloud (1GB).
        Logs organizados em expander para não poluir a tela.
        """
        combined_df = pd.DataFrame()
        chunk_size = APP_CONFIG.get("chunk_size", 10000)
        
        # Cria um expander para logs detalhados
        with st.expander("📋 Ver detalhes do carregamento", expanded=False):
            for idx, file in enumerate(files, start=1):
                filename = getattr(file, "name", "uploaded_file")
                st.write(f"**[{idx}/{len(files)}]** {filename}")

                # Detectar formato e carregar
                data, formato = _self._carregar_arquivo_unico(file, chunk_size=chunk_size)
                if data is None:
                    continue

                # Caso Parquet
                if formato == 'parquet':
                    data["source_file"] = filename
                    processed_df = _self._preprocess_data(data)
                    if not processed_df.empty:
                        st.success(f"✅ {len(processed_df):,} registros processados")
                        combined_df = pd.concat([combined_df, processed_df], ignore_index=True)
                        del processed_df

                # Caso CSV com chunks
                elif formato == 'csv_chunks':
                    chunk_count = 0
                    total_rows = 0
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for chunk in data:
                        if isinstance(chunk, pd.DataFrame):
                            chunk = chunk.assign(source_file=filename)
                            processed_chunk = _self._preprocess_data(chunk)
                            if not processed_chunk.empty:
                                combined_df = pd.concat([combined_df, processed_chunk], ignore_index=True)
                                chunk_count += 1
                                total_rows += len(processed_chunk)
                                del processed_chunk
                                
                                # Atualiza progresso
                                status_text.text(f"Processados {total_rows:,} registros em {chunk_count} blocos...")
                    
                    progress_bar.progress(100)
                    st.success(f"✅ {total_rows:,} registros em {chunk_count} blocos")

                # Caso CSV completo
                elif formato == 'csv':
                    data["source_file"] = filename
                    processed_df = _self._preprocess_data(data)
                    if not processed_df.empty:
                        st.success(f"✅ {len(processed_df):,} registros processados")
                        combined_df = pd.concat([combined_df, processed_df], ignore_index=True)
                        del processed_df

        if not combined_df.empty:
            return combined_df

        st.warning("⚠️ Nenhum dado foi carregado.")
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
        # Normalizar nomes das colunas ANTES de qualquer processamento
        df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_')

        # Aplicar mapeamento de colunas
        for standard_name, possible_names in COLUMN_MAPPING.items():
            # Adicionar versão normalizada dos nomes possíveis
            normalized_possible_names = [
                name.lower().strip().replace(' ', '_') 
                for name in possible_names
            ]
            
            for possible_name in normalized_possible_names:
                if (
                    possible_name in df.columns
                    and standard_name not in df.columns
                ):
                    df.rename(
                        columns={possible_name: standard_name}, inplace=True
                    )
                    break

        # Processar coluna de data para extrair ano
        date_cols = [c for c in df.columns if "data" in c]
        if date_cols:
            df["ano"] = pd.to_datetime(df[date_cols[0]], errors="coerce").dt.year
        
        # Se uma coluna 'ano' já existe, usar para preencher valores vazios
        if "ano" in df.columns:
            original_ano_numeric = pd.to_numeric(df["ano"], errors='coerce')
            df["ano"] = df["ano"].fillna(original_ano_numeric)

        # Como último recurso, tentar extrair o ano do nome do arquivo
        if "ano" not in df.columns or df["ano"].isnull().all():
            if "source_file" in df.columns:
                df["ano"] = df["source_file"].apply(self._extract_year_from_text)

        # Garantir que a coluna 'ano' final seja do tipo numérico
        if "ano" in df.columns:
            df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
        else:
            st.warning("⚠️ Aviso: Não foi possível determinar a coluna 'ano'.")

        # Processar fase_dia
        if "fase_dia" in df.columns:
            df["fase_dia"] = df["fase_dia"].astype(str).str.lower().str.strip()
            fase_map = {
                var: std_val
                for std_val, variations in VALUE_STANDARDIZATION["fase_dia"].items()
                for var in variations
            }
            df["fase_dia"] = df["fase_dia"].map(fase_map).fillna("diurno")
        else:
            df["fase_dia"] = "Não informado"

        # Processar estado_fisico para contar mortos
        if "estado_fisico" in df.columns:
            df["mortos"] = (
                df["estado_fisico"].astype(str).str.lower().str.strip() == "óbito"
            ).astype(int)

        # Garantir colunas numéricas
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

        # Calcular totais
        df["total_feridos"] = df["feridos_leves"] + df["feridos_graves"]
        df["total_vitimas"] = df["mortos"] + df["total_feridos"]

        # Processar UF
        if "uf" in df.columns:
            df["uf"] = (
                df["uf"]
                .astype(str)
                .str.strip()
                .str.upper()
                .replace({"NAN": None, "NONE": None})
            )
            df.dropna(subset=["uf"], inplace=True)
        else:
            st.warning("⚠️ Coluna 'uf' não encontrada.")

        # Processar BR
        if "br" in df.columns:
            df["br"] = (
                pd.to_numeric(df["br"], errors="coerce")
                .astype("Int64")
                .astype(str)
                .replace("<NA>", "N/A")
            )
        else:
            st.info("ℹ️ Coluna 'br' (rodovia) não encontrada.")

        return df

    def apply_filters(self, df, filters):
        """Aplica filtros aos dados."""
        if df is None or df.empty:
            return pd.DataFrame()
        
        filtered_df = df.copy()
        
        if filters.get("anos") and len(filters["anos"]) > 0 and "ano" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["ano"].isin(filters["anos"])]
        
        if filters.get("ufs") and len(filters["ufs"]) > 0 and "uf" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["uf"].isin(filters["ufs"])]
        
        if filters.get("brs") and len(filters["brs"]) > 0 and "br" in filtered_df.columns:
            filtered_df = filtered_df[
                filtered_df["br"].isin([str(br) for br in filters["brs"]])
            ]
        
        if filters.get("fase_dia") and len(filters["fase_dia"]) > 0 and "fase_dia" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["fase_dia"].isin(filters["fase_dia"])]
        
        if filters.get("condicao_meteorologica") and len(filters["condicao_meteorologica"]) > 0:
            if "condicao_metereologica" in filtered_df.columns:
                filtered_df = filtered_df[
                    filtered_df["condicao_metereologica"].isin(filters["condicao_meteorologica"])
                ]
        
        return filtered_df

    def analyze_top_n(
        self,
        df,
        top_n: int = 100,
        comprimento_km: float = DEFAULT_COMPRIMENTO_TRECHO_KM,
        spacing_m: float = DEFAULT_SPACING_M,
    ):
        if df.empty:
            return pd.DataFrame(), {}

        df_res = df.copy()

        if "mortos" not in df_res.columns: 
            df_res['mortos'] = 0
        if "total_feridos" not in df_res.columns: 
            df_res['total_feridos'] = 0
        
        df_res["score_prioridade"] = df_res["mortos"] * 3 + df_res["total_feridos"]

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
