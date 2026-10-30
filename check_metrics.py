import pandas as pd
from metrics import compute_period_metrics
from data_loader import process_raw_dataframe

df25 = pd.read_csv('data/acidentes2025_todas_causas_tipos.csv', sep=';', encoding='latin1', low_memory=False)
df26 = pd.read_csv('data/acidentes2026_todas_causas_tipos.csv', sep=';', encoding='latin1', low_memory=False)
occ, _, _ = process_raw_dataframe(pd.concat([df25, df26], ignore_index=True), '2025_2026')
metrics = compute_period_metrics(occ, 'fase_dia_oficial')
for _, r in metrics.iterrows():
    print(r['fase_dia_oficial'], '| Acid:', r['n_acidentes'], '| Mortos:', r['total_mortos'], '| Mortos/100:', f"{r['mortos_por_100_acidentes']:.2f}", '| % Fatais:', f"{r['prop_acidentes_fatais_pct']:.2f}%")

