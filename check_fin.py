import pandas as pd
from analyzer import AccidentAnalyzer
from data_loader import process_raw_dataframe

analyzer = AccidentAnalyzer()
df25 = pd.read_csv('data/acidentes2025_todas_causas_tipos.csv', sep=';', encoding='latin1', low_memory=False)
df26 = pd.read_csv('data/acidentes2026_todas_causas_tipos.csv', sep=';', encoding='latin1', low_memory=False)
df_raw = pd.concat([df25, df26], ignore_index=True)

occ, causas, quality = process_raw_dataframe(df_raw, '2025_2026')
analyzer.data = occ
analyzer.causas_data = causas
analyzer.quality_summary = quality
analyzer.filtered_data = occ
analyzer.filtered_causas = causas

top_df, agregados = analyzer.analyze_top_n(occ, top_n=100, comprimento_km=2.0, spacing_m=50)

print('=== FINANCIAL AGGREGATES ===')
print('Investimento total (CAPEX): R$', f"{agregados['investimento_total']:,.2f}")
print('Economia anual bruta: R$', f"{agregados['economia_anual']:,.2f}")
print('Economia anual liquida: R$', f"{agregados['economia_liquida_anual']:,.2f}")
print('Vidas salvas ano:', f"{agregados['vidas_salvas_ano']:.1f}")
print('Graves evitados ano:', f"{agregados['graves_evitados_ano']:.1f}")
print('Leves evitados ano:', f"{agregados['leves_evitados_ano']:.1f}")
print('VPL: R$', f"{agregados['vpl']:,.2f}")
tir = agregados['tir']
print('TIR:', f"{tir*100:.2f}%" if tir else 'N/A')
print('Payback simples:', f"{agregados['payback_simples_anos']:.2f} anos")
pb_desc = agregados['payback_descontado_anos']
print('Payback descontado:', f"{pb_desc:.2f} anos" if pb_desc else 'N/A')
print('ROI descontado (%):', f"{agregados['roi_descontado_pct']:.2f}%")
print('Anos base fator:', agregados['anos_base'])
print('\nTop 100 mortos_noturno sum:', top_df['mortos_noturno'].sum())
print('Top 100 feridos_graves_noturno sum:', top_df['feridos_graves_noturno'].sum())
print('Top 100 feridos_leves_noturno sum:', top_df['feridos_leves_noturno'].sum())

