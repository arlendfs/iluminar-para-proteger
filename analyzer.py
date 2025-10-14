import streamlit as st
import pandas as pd
import os
import re
import gc
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
            try:
                # Carregar arquivo completo
                df = pd.read_parquet(file, columns=None)
                
                # OTIMIZAÇÃO: Converter tipos de dados para economizar memória
                df = AccidentAnalyzer._otimizar_tipos_dados(df)
                
                st.success(f"✅ {filename}: {len(df):,} registros ({df.memory_usage(deep=True).sum() / 1024**2:.1f} MB)")
                return df, 'parquet'
            except Exception as e:
                st.error(f"❌ Erro ao carregar Parquet {filename}: {str(e)}")
                return None, None
                
        elif formato == 'csv':
            try:
                if chunk_size:
                    csv_reader = pd.read_csv(
                        file,
                        encoding="latin1",
                        sep=None,
                        engine="python",
                        chunksize=chunk_size,
                        on_bad_lines='warn',
                        low_memory=True
                    )
                    return csv_reader, 'csv_chunks'
                else:
                    df = pd.read_csv(
                        file,
                        encoding="latin1",
                        sep=None,
                        engine="python",
                        on_bad_lines='warn',
                        low_memory=True
                    )
                    df = AccidentAnalyzer._otimizar_tipos_dados(df)
                    st.success(f"✅ {filename}: {len(df):,} registros ({df.memory_usage(deep=True).sum() / 1024**2:.1f} MB)")
                    return df, 'csv'
            except Exception as e:
                st.error(f"❌ Erro ao carregar CSV {filename}: {str(e)}")
                return None, None
        else:
            st.error(f"❌ Formato não suportado: {filename}")
            return None, None

    @staticmethod
    def _otimizar_tipos_dados(df):
        """
        OTIMIZAÇÃO CRÍTICA: Converte tipos de dados para reduzir uso de memória
        """
        # Strings para category (economiza muito em colunas repetitivas)
        for col in df.select_dtypes(include=['object']).columns:
            num_unique = df[col].nunique()
            num_total = len(df[col])
            # Se menos de 50% dos valores são únicos, converte para category
            if num_unique / num_total < 0.5:
                df[col] = df[col].astype('category')
        
        # Otimizar colunas numéricas
        for col in df.select_dtypes(include=['int']).columns:
            if df[col].min() >= 0:
                if df[col].max() < 255:
                    df[col] = df[col].astype('uint8')
                elif df[col].max() < 65535:
                    df[col] = df[col].astype('uint16')
                elif df[col].max() < 4294967295:
                    df[col] = df[col].astype('uint32')
            else:
                if df[col].max() < 127 and df[col].min() > -128:
                    df[col] = df[col].astype('int8')
                elif df[col].max() < 32767 and df[col].min() > -32768:
                    df[col] = df[col].astype('int16')
        
        # Float32 ao invés de Float64 para coordenadas
        for col in ['latitude', 'longitude']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('float32')
        
        return df

    # Remover cache ou usar cache com key único
    def load_local_files(self, data_dir, local_files):
        """
        Carrega arquivos locais com gestão eficiente de memória.
        SEM cache para evitar reutilizar dados antigos.
        """
        all_data = []
        total_memory_mb = 0
        
        st.info(f"📁 Carregando {len(local_files)} arquivo(s) da pasta /data...")
        
        for idx, filename in enumerate(local_files, start=1):
            try:
                filepath = os.path.join(data_dir, filename)
                progress = idx / len(local_files)
                
                if filename.lower().endswith('.parquet'):
                    df = pd.read_parquet(filepath)
                    df["source_file"] = filename
                    df = self._otimizar_tipos_dados(df)
                    memory_mb = df.memory_usage(deep=True).sum() / 1024**2
                    total_memory_mb += memory_mb
                    all_data.append(df)
                    st.success(f"✅ [{idx}/{len(local_files)}] {filename}: {len(df):,} registros ({memory_mb:.1f} MB)")
                    
                elif filename.lower().endswith('.csv'):
                    try:
                        df = pd.read_csv(filepath, encoding="latin1", low_memory=True)
                    except:
                        df = pd.read_csv(
                            filepath, 
                            encoding="latin1", 
                            sep=None, 
                            engine="python",
                            on_bad_lines='warn'
                        )
                    
                    df["source_file"] = filename
                    df = self._otimizar_tipos_dados(df)
                    memory_mb = df.memory_usage(deep=True).sum() / 1024**2
                    total_memory_mb += memory_mb
                    all_data.append(df)
                    st.success(f"✅ [{idx}/{len(local_files)}] {filename}: {len(df):,} registros ({memory_mb:.1f} MB)")
                    
                else:
                    st.warning(f"⚠️ {filename} ignorado (formato não suportado)")
                    continue
                    
                # Liberar memória a cada arquivo
                gc.collect()
                    
            except Exception as e:
                st.error(f"❌ Erro ao carregar {filename}: {str(e)}")
                continue

        if all_data:
            st.info(f"💾 Memória total antes do concat: {total_memory_mb:.1f} MB")
            combined_df = pd.concat(all_data, ignore_index=True)
            
            # Limpar lista intermediária
            del all_data
            gc.collect()
            
            # Processar e otimizar resultado final
            processed_df = self._preprocess_data(combined_df)
            del combined_df
            gc.collect()
            
            final_memory_mb = processed_df.memory_usage(deep=True).sum() / 1024**2
            st.success(f"✅ Total processado: {len(processed_df):,} registros ({final_memory_mb:.1f} MB)")
            
            return processed_df
        return None
    
    # Remover cache para upload de arquivos
    def load_data(self, files):
        """
        Carrega com gestão de memória e processamento incremental.
        SEM cache para upload de arquivos (dados podem variar).
        """
        combined_df = pd.DataFrame()
        chunk_size = APP_CONFIG.get("chunk_size", 10000)
        total_memory_mb = 0
        
        with st.expander("📋 Ver detalhes do carregamento", expanded=False):
            for idx, file in enumerate(files, start=1):
                filename = getattr(file, "name", "uploaded_file")
                st.write(f"**[{idx}/{len(files)}]** {filename}")

                data, formato = self._carregar_arquivo_unico(file, chunk_size=chunk_size)
                if data is None:
                    continue

                # Parquet: processar diretamente
                if formato == 'parquet':
                    data["source_file"] = filename
                    processed_df = self._preprocess_data(data)
                    if not processed_df.empty:
                        memory_mb = processed_df.memory_usage(deep=True).sum() / 1024**2
                        total_memory_mb += memory_mb
                        st.success(f"✅ {len(processed_df):,} registros ({memory_mb:.1f} MB)")
                        combined_df = pd.concat([combined_df, processed_df], ignore_index=True)
                        del processed_df
                        gc.collect()

                # CSV chunks: processar por partes
                elif formato == 'csv_chunks':
                    chunk_count = 0
                    total_rows = 0
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Agregar chunks antes de concatenar
                    chunk_buffer = []
                    buffer_size_limit = 100000  # Processa em lotes de 100k registros
                    
                    for chunk in data:
                        if isinstance(chunk, pd.DataFrame):
                            chunk = chunk.assign(source_file=filename)
                            processed_chunk = self._preprocess_data(chunk)
                            
                            if not processed_chunk.empty:
                                chunk_buffer.append(processed_chunk)
                                chunk_count += 1
                                total_rows += len(processed_chunk)
                                
                                # Quando buffer atingir limite, concatenar e limpar
                                if total_rows >= buffer_size_limit:
                                    buffer_df = pd.concat(chunk_buffer, ignore_index=True)
                                    combined_df = pd.concat([combined_df, buffer_df], ignore_index=True)
                                    chunk_buffer = []
                                    gc.collect()
                                
                                status_text.text(f"Processados {total_rows:,} registros...")
                    
                    # Processar chunks restantes no buffer
                    if chunk_buffer:
                        buffer_df = pd.concat(chunk_buffer, ignore_index=True)
                        combined_df = pd.concat([combined_df, buffer_df], ignore_index=True)
                        del chunk_buffer, buffer_df
                        gc.collect()
                    
                    progress_bar.progress(100)
                    st.success(f"✅ {total_rows:,} registros em {chunk_count} blocos")

                # CSV completo
                elif formato == 'csv':
                    data["source_file"] = filename
                    processed_df = self._preprocess_data(data)
                    if not processed_df.empty:
                        st.success(f"✅ {len(processed_df):,} registros processados")
                        combined_df = pd.concat([combined_df, processed_df], ignore_index=True)
                        del processed_df
                        gc.collect()
                
                # Liberar memória após cada arquivo
                gc.collect()

        if not combined_df.empty:
            # Otimização final
            combined_df = self._otimizar_tipos_dados(combined_df)
            final_memory_mb = combined_df.memory_usage(deep=True).sum() / 1024**2
            st.info(f"💾 Memória total: {final_memory_mb:.1f} MB | {len(combined_df):,} registros")
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
        """OTIMIZADO: Preprocessa com economia de memória"""
        # Normalizar colunas
        df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_')

        # Mapear colunas
        for standard_name, possible_names in COLUMN_MAPPING.items():
            normalized_possible_names = [
                name.lower().strip().replace(' ', '_') 
                for name in possible_names
            ]
            
            for possible_name in normalized_possible_names:
                if possible_name in df.columns and standard_name not in df.columns:
                    df.rename(columns={possible_name: standard_name}, inplace=True)
                    break

        # Processar data para extrair ano (OTIMIZADO)
        date_cols = [c for c in df.columns if "data" in c]
        if date_cols and "ano" not in df.columns:
            df["ano"] = pd.to_datetime(df[date_cols[0]], errors="coerce").dt.year.astype('Int16')
        
        # Usar ano do arquivo se necessário
        if "ano" not in df.columns or df["ano"].isnull().all():
            if "source_file" in df.columns:
                df["ano"] = df["source_file"].apply(self._extract_year_from_text).astype('Int16')

        # Processar fase_dia (category para economizar memória)
        if "fase_dia" in df.columns:
            df["fase_dia"] = df["fase_dia"].astype(str).str.lower().str.strip()
            fase_map = {
                var: std_val
                for std_val, variations in VALUE_STANDARDIZATION["fase_dia"].items()
                for var in variations
            }
            df["fase_dia"] = df["fase_dia"].map(fase_map).fillna("diurno").astype('category')
        else:
            df["fase_dia"] = pd.Categorical(["Não informado"] * len(df))

        # Processar estado_fisico para mortos
        if "estado_fisico" in df.columns:
            df["mortos"] = (df["estado_fisico"].astype(str).str.lower().str.strip() == "óbito").astype('uint8')

        # Garantir colunas numéricas (tipos otimizados)
        numeric_cols = {
            "mortos": 'uint8',
            "feridos_leves": 'uint16',
            "feridos_graves": 'uint16',
            "ileso": 'uint16',
            "km": 'float32',
            "latitude": 'float32',
            "longitude": 'float32',
        }
        
        for col, dtype in numeric_cols.items():
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(dtype)
            else:
                df[col] = pd.array([0] * len(df), dtype=dtype)

        # Calcular totais
        df["total_feridos"] = (df["feridos_leves"] + df["feridos_graves"]).astype('uint16')
        df["total_vitimas"] = (df["mortos"] + df["total_feridos"]).astype('uint16')

        # Processar UF (category)
        if "uf" in df.columns:
            df["uf"] = df["uf"].astype(str).str.strip().str.upper().replace({"NAN": None, "NONE": None})
            df.dropna(subset=["uf"], inplace=True)
            df["uf"] = df["uf"].astype('category')

        # Processar BR (category)
        if "br" in df.columns:
            df["br"] = pd.to_numeric(df["br"], errors="coerce").astype('Int16').astype(str).replace("<NA>", "N/A")
            df["br"] = df["br"].astype('category')

        return df

    def apply_filters(self, df, filters):
        """Aplica filtros de forma eficiente"""
        if df is None or df.empty:
            return pd.DataFrame()
        
        # Filtrar sem criar cópias desnecessárias
        mask = pd.Series([True] * len(df), index=df.index)
        
        if filters.get("anos") and len(filters["anos"]) > 0 and "ano" in df.columns:
            mask &= df["ano"].isin(filters["anos"])
        
        if filters.get("ufs") and len(filters["ufs"]) > 0 and "uf" in df.columns:
            mask &= df["uf"].isin(filters["ufs"])
        
        if filters.get("brs") and len(filters["brs"]) > 0 and "br" in df.columns:
            mask &= df["br"].isin([str(br) for br in filters["brs"]])
        
        if filters.get("fase_dia") and len(filters["fase_dia"]) > 0 and "fase_dia" in df.columns:
            mask &= df["fase_dia"].isin(filters["fase_dia"])
        
        if filters.get("condicao_meteorologica") and len(filters["condicao_meteorologica"]) > 0:
            if "condicao_metereologica" in df.columns:
                mask &= df["condicao_metereologica"].isin(filters["condicao_meteorologica"])
        
        filtered_df = df[mask].copy()
        gc.collect()
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
        economia_mortos = (top_df["mortos"].sum() * reducao) * ECONOMIC_VALUES["valor_vida_estatistica"]
        economia_graves = (top_df["feridos_graves"].sum() * reducao) * ECONOMIC_VALUES["custo_medio_acidente_grave"]
        economia_leves = (top_df["feridos_leves"].sum() * reducao) * ECONOMIC_VALUES["custo_medio_acidente_leve"]

        agregados = {
            "top_df": top_df,
            "investimento_total": float(top_df["investimento_trecho"].sum()),
            "economia_anual": float(top_df["economia_anual_trecho"].sum()),
            "economia_mortos": float(economia_mortos),
            "economia_graves": float(economia_graves),
            "economia_leves": float(economia_leves),
            "vitimas_evitadas_total": float(top_df["acidentes_evitados_ano"].sum()),
        }
        
        # Limpar memória
        del df_res, roi_results
        gc.collect()
        
        return top_df, agregados


def calculate_roi(
    total_mortos,
    total_feridos_graves,
    total_feridos_leves,
    comprimento_trecho_km: float,
    spacing_m: float,
):
    reducao_estimada = EFFECTIVENESS_PARAMS["reducao_acidentes_noturnos"]

    posts_por_trecho = (1000 / spacing_m) * comprimento_trecho_km
    investimento_total_trecho = posts_por_trecho * FINANCIAL_PARAMS["custo_poste_solar"]

    economia_mortos = (total_mortos * reducao_estimada) * ECONOMIC_VALUES["valor_vida_estatistica"]
    economia_graves = (total_feridos_graves * reducao_estimada) * ECONOMIC_VALUES["custo_medio_acidente_grave"]
    economia_leves = (total_feridos_leves * reducao_estimada) * ECONOMIC_VALUES["custo_medio_acidente_leve"]
    valor_economizado_ano = economia_mortos + economia_graves + economia_leves

    payback_anos = (
        investimento_total_trecho / valor_economizado_ano
        if valor_economizado_ano > 0
        else float("inf")
    )

    custo_manutencao_anual_total = posts_por_trecho * FINANCIAL_PARAMS.get("custo_manutencao_anual_por_poste", 0)
    investimento_e_manutencao_10_anos = investimento_total_trecho + (custo_manutencao_anual_total * 10)

    if investimento_e_manutencao_10_anos > 0:
        economia_total_10_anos = valor_economizado_ano * 10
        roi_10_anos = ((economia_total_10_anos - investimento_e_manutencao_10_anos) / investimento_e_manutencao_10_anos) * 100
    else:
        roi_10_anos = 0.0

    acidentes_evitados_ano = (total_mortos + total_feridos_graves + total_feridos_leves) * reducao_estimada

    return (
        roi_10_anos,
        payback_anos,
        investimento_total_trecho,
        valor_economizado_ano,
        acidentes_evitados_ano,
    )
