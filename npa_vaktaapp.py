import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

fridagar_2025 = [
    "2025-01-01", "2025-03-20", "2025-04-18", "2025-04-20", "2025-04-21",
    "2025-05-01", "2025-05-29", "2025-06-01", "2025-06-17", "2025-08-04",
    "2025-12-24", "2025-12-25", "2025-12-26", "2025-12-31"
]
fridagar_2025 = set(pd.to_datetime(fridagar_2025))

def reikna_alaeg(kl, dagur, dagsetning):
    if dagur == 0 and 0 <= kl < 8 and dagsetning not in fridagar_2025:
        return 'alag_65'
    if dagsetning in fridagar_2025:
        if 0 <= kl < 8:
            return 'alag_75_fridagur'
        elif 8 <= kl < 24:
            return 'alag_55_fridagur'

    if dagur in [0, 1, 2, 3]:
        if 17 <= kl < 24:
            return 'alag_33_33'
    elif dagur == 4:
        if 17 <= kl < 24:
            return 'alag_55'
        elif 0 <= kl < 8:
            return 'alag_65'
    elif dagur == 5 or dagur == 6:
        if 0 <= kl < 8:
            return 'alag_75'
        elif 8 <= kl < 24:
            return 'alag_55'
    elif dagur == 0 and kl < 8:
        return 'alag_75'
    if 0 <= kl < 8 and dagur in [1, 2, 3, 4]:
        return 'alag_65'
    return 'dagvinna'

def vinnutimar(stimplanir):
    try:
        byrjun, endir = stimplanir.split('-')
        t1 = datetime.strptime(byrjun.strip(), "%H:%M")
        t2 = datetime.strptime(endir.strip(), "%H:%M")
        if t2 < t1:
            t2 += timedelta(days=1)
        return (t2 - t1).seconds / 3600
    except:
        return 0

def sundurlida_alaeg(stimplanir, dagsetning):
    try:
        byrjun, endir = stimplanir.split('-')
        t1 = datetime.strptime(byrjun.strip(), "%H:%M")
        t2 = datetime.strptime(endir.strip(), "%H:%M")
        if t2 < t1:
            t2 += timedelta(days=1)

        times = {}
        curr = t1
        while curr < t2:
            vikudagur = dagsetning.weekday()
            alaeg = reikna_alaeg(curr.hour + curr.minute / 60, vikudagur, dagsetning)
            next_step = min(t2, curr + timedelta(minutes=15))
            delta = (next_step - curr).seconds / 3600
            times[alaeg] = times.get(alaeg, 0) + delta
            curr = next_step
        return times
    except:
        return {}

def reikna_launatimabil(d):
    byrjun = datetime(d.year, d.month, 21)
    if d.day < 21:
        byrjun -= pd.DateOffset(months=1)
    endir = byrjun + pd.DateOffset(months=1) - timedelta(days=1)
    return f"{byrjun.strftime('%Y.%m.%d')}-{endir.strftime('%Y.%m.%d')}"

st.title("NPA – Álagsútreikningur úr Sling skrá")
uploaded_file = st.file_uploader("Veldu Sling .csv skrá", type="csv")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    df = df[df['DATE'].notna()].copy()
    df['Dagsetning'] = pd.to_datetime(df['DATE'], format="%d %b %Y", errors='coerce')
    df = df[df['Dagsetning'].notna()].copy()

    df['Stimplanir'] = df['SCH.\nSHIFT START'].str.strip() + "-" + df['SCH.\nSHIFT END'].str.strip()
    df['A_ID'] = df['EMPLOYEE'].str.strip()
    df['Launatímabil'] = df['Dagsetning'].apply(reikna_launatimabil)
    df['Tags'] = df['TAGS'] if 'TAGS' in df.columns else ''
    df['akstur'] = ''
    df['dagp'] = ''
    df['Heildartími'] = df['Stimplanir'].apply(vinnutimar)

    allar_nidur = []
    for idx, row in df.iterrows():
        alag = sundurlida_alaeg(row['Stimplanir'], row['Dagsetning'])
        for teg, magn in alag.items():
            allar_nidur.append({
                'A_ID': row['A_ID'],
                'Launatímabil': row['Launatímabil'],
                'Dagur': row['Dagsetning'].strftime('%a'),
                'Dagsetning': row['Dagsetning'].strftime('%Y.%m.%d'),
                'Stimplanir': row['Stimplanir'],
                'Tegund': teg,
                'Klst': magn
            ,
                'akstur': row.get('akstur', ''),
                'dagp': row.get('dagp', ''),
                'Tags': row.get('Tags', '')
            })

    df_nidur = pd.DataFrame(allar_nidur)

    dagtaflan = df_nidur.pivot_table(
        index=['A_ID', 'Launatímabil', 'Dagur', 'Dagsetning', 'Stimplanir', 'akstur', 'dagp'],
        columns='Tegund',
        values='Klst',
        aggfunc='sum',
        fill_value=0
    ).reset_index()
    dagtaflan['A_ID_sort'] = dagtaflan['A_ID'].str.extract(r'(\d+)').astype(int)
    dagtaflan['Dagsetning_sort'] = pd.to_datetime(dagtaflan['Dagsetning'], format='%Y.%m.%d')
    dagtaflan = dagtaflan.sort_values(by=['A_ID_sort', 'Dagsetning_sort']).drop(columns=['A_ID_sort', 'Dagsetning_sort'])

    


    

    export_file_name = "vaktayfirlit_daglegt.xlsx"
    dagtaflan.to_excel(export_file_name, index=False)

    st.write("\n### 1. Sundurliðun eftir degi")
    cols = [col for col in dagtaflan.columns]
    from itertools import cycle

    litir = {
        'alag_33_33': '#ffd9b3',
        'alag_55': '#ffb3b3',
        'alag_65': '#ff9999',
        'alag_75': '#ff8080',
        'alag_55_fridagur': '#ff6666',
        'alag_75_fridagur': '#ff4d4d',
        'dagvinna': '#d9ffcc'
    }
    def litun(gildi, dálkur):
            if isinstance(gildi, (int, float)) and gildi > 0:
                return f'background-color: {litir.get(dálkur, "#eeeeee")}'
            return ''
    st.dataframe(
        dagtaflan.style.apply(
            lambda col: [litun(val, col.name) for val in col],
            subset=dagtaflan.filter(regex='alag|dagvinna').columns
        )
    )

    with open(export_file_name, "rb") as f:
        st.download_button("Sækja daglega sundurliðun", data=f, file_name=export_file_name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
