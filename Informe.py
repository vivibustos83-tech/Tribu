import dash
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import base64

# =========================================================
# 1. ENLAZAR EXCEL Y PREPARAR DATOS COMERCIALES
# =========================================================
archivo_excel = 'Informe_Tribu.xlsx'

df_ventas_raw = pd.read_excel(archivo_excel, sheet_name='ventas totales')
df_maquilas_raw = pd.read_excel(archivo_excel, sheet_name='maquilas')

meses_ventas = [col for col in df_ventas_raw.columns if col not in ['Nombre', 'Ciudad']]
meses_maquilas = [col for col in df_maquilas_raw.columns if col not in ['Nombre', 'Ciudad']]
columnas_master = meses_ventas 
posicion_meses = {mes: i for i, mes in enumerate(columnas_master)}

# Derivaciones horizontales a verticales
df_ventas_melt = df_ventas_raw.melt(id_vars=['Nombre', 'Ciudad'], var_name='Mes', value_name='Ventas').fillna(0)
df_maquilas_melt = df_maquilas_raw.melt(id_vars=['Nombre', 'Ciudad'], var_name='Mes', value_name='Maquilas').fillna(0)
df_ventas_melt = df_ventas_melt[df_ventas_melt['Mes'].isin(columnas_master)]

# Uniones de tiempo mensuales
df_ventas_mensual = df_ventas_melt.groupby('Mes', as_index=False)['Ventas'].sum()
df_maquilas_mensual = df_maquilas_melt.groupby('Mes', as_index=False)['Maquilas'].sum()

df_compras_reales = df_ventas_melt[df_ventas_melt['Ventas'] > 0].copy()
df_clientes_activos = df_compras_reales.groupby('Mes')['Nombre'].nunique().reset_index(name='Clientes_Mensuales')

df_compras_reales['Mes_Orden'] = df_compras_reales['Mes'].map(posicion_meses)
df_primera_compra = df_compras_reales.sort_values('Mes_Orden').groupby('Nombre')['Mes'].first().reset_index()
df_primera_compra.columns = ['Nombre', 'Mes']
df_clientes_nuevos = df_primera_compra.groupby('Mes')['Nombre'].count().reset_index(name='Clientes_Nuevos')

df_final = pd.merge(df_ventas_mensual, df_maquilas_mensual, on='Mes', how='outer')
df_final = pd.merge(df_final, df_clientes_activos, on='Mes', how='left')
df_final = pd.merge(df_final, df_clientes_nuevos, on='Mes', how='left')
df_final['Mes_Orden'] = df_final['Mes'].map(posicion_meses)
df_final = df_final.sort_values('Mes_Orden').drop(columns=['Mes_Orden']).fillna(0)
df_final = df_final[df_final['Mes'].isin(columnas_master)]

# CÁLCULOS EXCLUSIVOS PARA RECUADROS KPI
ventas_totales_global = df_final['Ventas'].sum()
total_clientes_unicos = df_ventas_raw['Nombre'].nunique()

df_ranking_clientes = df_ventas_melt.groupby('Nombre', as_index=False)['Ventas'].sum()
cliente_top_info = df_ranking_clientes.sort_values('Ventas', ascending=False).iloc[0] # <-- CORREGIDO ÍNDICE [0]
cliente_top_nombre = cliente_top_info['Nombre']
cliente_top_ventas = cliente_top_info['Ventas']

df_ranking_ciudades = df_ventas_melt.groupby('Ciudad', as_index=False)['Ventas'].sum()
ciudad_lider_info = df_ranking_ciudades.sort_values('Ventas', ascending=False).iloc[0] # <-- CORREGIDO ÍNDICE [0]
ciudad_lider_nombre = ciudad_lider_info['Ciudad']
ciudad_lider_ventas = ciudad_lider_info['Ventas']

promedio_mensual_por_cliente = (ventas_totales_global / total_clientes_unicos) / len(columnas_master)

# =========================================================
# PRE-CALCULAR TODOS LOS GRÁFICOS (MÁXIMA VELOCIDAD PARA NUBE)
# =========================================================

# --- GRÁFICOS PESTAÑA RESUMEN ---
fig_comercial = px.line(df_final, x='Mes', y=['Ventas', 'Maquilas'], labels={'value': 'Monto ($)', 'variable': 'Métrica'}, template="plotly_white", color_discrete_sequence=["#0d6efd", "#ffc107"])
fig_comercial.update_layout(margin=dict(l=20, r=20, t=10, b=20), legend=dict(orientation="h", y=1.1))

df_ciudades = df_ventas_melt.groupby('Ciudad', as_index=False)['Ventas'].sum()
fig_pastel = px.pie(df_ciudades, values='Ventas', names='Ciudad', title="Participación de Ventas por Ciudad", hole=0.4, template="plotly_white")
fig_pastel.update_traces(textinfo='percent', textposition='inside')
fig_pastel.update_layout(showlegend=True, legend=dict(orientation="v", align="left"))

df_top_10 = df_ranking_clientes.sort_values('Ventas', ascending=False).head(10)
fig_top_10 = px.bar(df_top_10, x='Ventas', y='Nombre', orientation='h', template="plotly_white", color='Ventas', color_continuous_scale="Blues", text_auto='.2s')
fig_top_10.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False, coloraxis_showscale=False, margin=dict(l=20, r=20, t=10, b=20))
fig_top_10.update_traces(textposition='outside', cliponaxis=False)

fig_clientes = px.bar(df_final, x='Mes', y=['Clientes_Mensuales', 'Clientes_Nuevos'], barmode='group', template="plotly_white", color_discrete_sequence=["#198754", "#0dcaf0"])
fig_clientes.update_layout(margin=dict(l=20, r=20, t=10, b=20), legend=dict(orientation="h", y=1.1))

# --- GRÁFICOS PESTAÑA HEATMAP ---
df_heatmap_data = df_ventas_melt.pivot_table(index='Ciudad', columns='Mes', values='Ventas', aggfunc='sum').fillna(0)
df_heatmap_data = df_heatmap_data[columnas_master]
fig_real_heatmap = px.imshow(df_heatmap_data.values, x=df_heatmap_data.columns, y=df_heatmap_data.index, text_auto=".2s", color_continuous_scale="Viridis", aspect="auto")
fig_real_heatmap.update_layout(title_text='Mapa de Calor: Distribución de Ventas por Ciudad y Mes', title_x=0.5, margin=dict(t=50, b=20))

# --- GRÁFICOS PESTAÑA K-MEANS ---
df_perf_km = df_ventas_melt[df_ventas_melt['Ventas'] > 0].groupby('Nombre').agg(Total_Anual=('Ventas', 'sum'), Promedio_Mensual=('Ventas', 'mean'), Meses_Activos=('Mes', 'count')).reset_index()
X_km = df_perf_km[['Promedio_Mensual', 'Total_Anual']].values

inercias, siluetas, rango_k = [], [], list(range(2, 9))
for k in rango_k:
    km_temp = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X_km)
    inercias.append(km_temp.inertia_)
    siluetas.append(silhouette_score(X_km, km_temp.labels_))

fig_eval = go.Figure()
fig_eval.add_trace(go.Scatter(x=rango_k, y=inercias, name="Inercia (Codo)", mode='lines+markers', yaxis='y1', line=dict(color='#0d6efd', width=3)))
fig_eval.add_trace(go.Scatter(x=rango_k, y=siluetas, name="Silueta", mode='lines+markers', yaxis='y2', line=dict(color='#198754', width=3, dash='dash')))
fig_eval.update_layout(title="Método del Codo + Silueta", template="plotly_white", xaxis=dict(title="Número de Clusters (K)"), yaxis=dict(title="Inercia", titlefont=dict(color="#0d6efd"), tickfont=dict(color="#0d6efd")), yaxis2=dict(title="Score Silueta", titlefont=dict(color="#198754"), tickfont=dict(color="#198754"), overlaying='y', side='right'), legend=dict(orientation="h", y=1.1))

km_final = KMeans(n_clusters=3, random_state=42, n_init=10).fit(X_km)
df_perf_km['Cluster'] = km_final.labels_
fig_cluster_scatter = px.scatter(df_perf_km, x='Promedio_Mensual', y='Total_Anual', color=df_perf_km['Cluster'].astype(str), size='Total_Anual', hover_data=['Nombre'], labels={'Promedio_Mensual': 'Promedio mensual ($)', 'Total_Anual': 'Total anual ($)'}, title="Clusters K=3 — Promedio mensual vs Total anual", template="plotly_white")
fig_cluster_scatter.update_layout(margin=dict(l=20, r=20, t=40, b=20))

resumen_clusters = df_perf_km.groupby('Cluster').agg(N_empresas=('Nombre', 'count'), Total_Anual_Sum=('Total_Anual', 'sum'), Promedio_Mensual_Mean=('Promedio_Mensual', 'mean'), Meses_Activos_Mean=('Meses_Activos', 'mean')).reset_index()
tabla_data = []
for _, row in resumen_clusters.iterrows():
    tabla_data.append({
        'Cluster': f"Cluster {int(row['Cluster'])}", 'N_empresas': int(row['N_empresas']),
        'Total_Anual': f"${row['Total_Anual_Sum']:,.1f}M" if row['Total_Anual_Sum'] >= 1e6 else f"${row['Total_Anual_Sum']:,.0f}K",
        'Promedio_Mensual': f"${row['Promedio_Mensual_Mean']:,.1f}M" if row['Promedio_Mensual_Mean'] >= 1e6 else f"${row['Promedio_Mensual_Mean']:,.0f}K",
        'Meses_Activos': f"{row['Meses_Activos_Mean']:.2f}"
    })

try:
    encoded_image = base64.b64encode(open('logo.png', 'rb').read())
    logo_src = f'data:image/png;base64,{encoded_image.decode()}'
except Exception:
    logo_src = ""

# =========================================================
# 2. CONFIGURACIÓN E INTERFAZ (DASH)
# =========================================================
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY, "https://googleapis.com"], title="Dashboard Comercial Avanzado")
server = app.server

CARD_STYLE = {"box-shadow": "0 4px 15px rgba(0, 0, 0, 0.05)", "border-radius": "15px", "padding": "25px", "border": "none", "background-color": "#ffffff"}

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Img(src=logo_src, style={'height': '60px', 'margin-bottom': '5px'}) if logo_src else html.Div(),
                html.H6("ASPM - CANAL B2B", className="text-muted fw-bold", style={'font-size': '11px', 'letter-spacing': '1.5px', 'margin': '0'})
            ], style={'display': 'flex', 'flex-direction': 'column', 'align-items': 'flex-start'})
        ], width=4, className="d-flex align-items-center pt-3"),
        dbc.Col([html.H3("Panel Analítico Comercial", className="fw-bold text-end text-dark m-0 w-100")], width=8, className="d-flex align-items-center justify-content-end pt-3")
    ], className="mb-3 border-bottom pb-3"),
    
    dcc.Tabs(id="tabs-navegacion", value='tab-principal', children=[
        dcc.Tab(label='📌 Resumen', value='tab-principal'),
        dcc.Tab(label='🌡️ Heatmap & Pearson', value='tab-pearson'),
        dcc.Tab(label='🔵 K-Means', value='tab-kmeans'),
    ], className="mb-4", style={'font-family': 'Inter, sans-serif', 'font-weight': '600'}),
    
    html.Div(id='contenido-pestana')
], fluid=True)

# =========================================================
# 3. INTERRUPTOR DE PESTAÑAS (MUESTRA PRECALCULADOS)

