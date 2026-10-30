import pandas as pd
from data_loader import process_raw_dataframe

df25 = pd.read_csv('data/acidentes2025_todas_causas_tipos.csv', sep=';', encoding='latin1', low_memory=False)
df26 = pd.read_csv('data/acidentes2026_todas_causas_tipos.csv', sep=';', encoding='latin1', low_memory=False)
occ, causas, _ = process_raw_dataframe(pd.concat([df25, df26], ignore_index=True), '2025_2026')

# Merge unique (id, causa) with occurrence attributes
causas_uniq = causas[['id', 'causa_acidente']].drop_duplicates()
merged = occ.merge(causas_uniq, on='id', how='inner')

target_causes = [
    'Reação tardia ou ineficiente do condutor',
    'Ausência de reação do condutor',
    'Condutor Dormindo',
    'Ultrapassagem Indevida',
    'Velocidade Incompatível',
    'Ingestão de Álcool pelo condutor'
]

print('=== CAUSAS POR FASE DO DIA ===')
for c in target_causes:
    sub = merged[merged['causa_acidente'].str.contains(c, case=False, na=False)]
    print(f"\n--- {c} (Total Acid: {len(sub):,}, Mortos: {sub['mortos'].sum():,}) ---")
    grp = sub.groupby('fase_dia_oficial').agg(
        acid=('id', 'count'),
        mortos=('mortos', 'sum'),
        fatais=('acidente_fatal', 'sum')
    )
    grp['mortos_100'] = (grp['mortos'] / grp['acid'] * 100).round(2)
    grp['pct_fatais'] = (grp['fatais'] / grp['acid'] * 100).round(2)
    for idx, r in grp.iterrows():
        print(f"  {idx}: {r['acid']} acidentes | {r['mortos']} mortos | {r['mortos_100']:.2f} mortos/100 | {r['pct_fatais']:.2f}% fatais")

