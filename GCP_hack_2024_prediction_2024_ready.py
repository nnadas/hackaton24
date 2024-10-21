import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
from pandas.tseries.offsets import DateOffset
import numpy as np
import calendar

df = pd.read_csv('input.csv', encoding='windows-1250', sep=';')
#print(df.to_string())


result = df.head(10)
print("First 10 rows of the DataFrame:")
print(result)

# Odstranění času
df['DATUM'] = df['DATUM'].str.split().str[0]

# převedeme sloupec na datum
df['DATUM'] = pd.to_datetime(df['DATUM'], format='%d.%m.%Y', errors='coerce')

df['DATUM'].isnull().sum()
print(df.isnull().sum())

# Filtrace dat od listopadu 2022
df_filtered = df[df['DATUM'] >= '2022-11-01']

# Groupby
df_daily = df.groupby(['DATUM', 'NAZEV_SLUZBY']).agg({'PRICHOZI_HOVORY': 'sum'}).reset_index()

services = df_daily['NAZEV_SLUZBY'].unique()


# predikceSARIMA
def forecast_service(df, service_name):
  
    # ŽP x NŽP
    df_service = df[df['NAZEV_SLUZBY'] == service_name].set_index('DATUM')
    
  
    # odstranění NaN
    df_service = df_service.asfreq('D').fillna(0)  

    # Trénování 
    model = SARIMAX(df_service['PRICHOZI_HOVORY'], order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
    model_fit = model.fit(disp=False)

    # datumy
    future_dates = pd.date_range(start='2024-11-01', end='2024-11-30', freq='D')
    
    # predikce
    forecast = model_fit.get_forecast(steps=len(future_dates)).predicted_mean

    # df
    forecast_df = pd.DataFrame({
        'DATUM': future_dates,
        'POCET_PRICHOZICH_HOVORU': forecast,
        'NAZEV_SLUZBY': service_name
    })
    
    return forecast_df

# žp + nžp
all_forecasts = pd.DataFrame()

for service in services:
    forecast_df = forecast_service(df_daily, service)
    all_forecasts = pd.concat([all_forecasts, forecast_df])

# sloupce
all_forecasts['DEN'] = all_forecasts['DATUM'].dt.day_name(locale='cs_CZ')  
all_forecasts['TYDEN'] = all_forecasts['DATUM'].dt.isocalendar().week
all_forecasts['MESIC'] = all_forecasts['DATUM'].dt.month
all_forecasts['ROK'] = all_forecasts['DATUM'].dt.year

# ošetření státních svátků
svatky = ['2024-11-17']
all_forecasts.loc[all_forecasts['DATUM'].isin(pd.to_datetime(svatky)), 'POCET_PRICHOZICH_HOVORU'] = 0


# ŽP je mimo provoz o víkendech
print(all_forecasts['DEN'].unique())

# Ujistíme se, že sloupce mají správný formát (např. všechna písmena malá)
all_forecasts['DEN'] = all_forecasts['DEN'].str.lower()

# Definujeme víkendové dny
weekend_days = ['sobota', 'neděle']

# Nastavení počtu hovorů na 0 pro ŽP o víkendech
all_forecasts.loc[(all_forecasts['DEN'].isin(weekend_days)) & (all_forecasts['NAZEV_SLUZBY'] == 'ŽP'), 'POCET_PRICHOZICH_HOVORU'] = 0

# export
all_forecasts.to_excel('hackaton_output_file_NRU_8.xlsx', index=False, engine='openpyxl')

print("Done.")
