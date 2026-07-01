import dash
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import numpy as np
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

# Derivaciones verticales
df_ventas_melt = df_ventas_raw.melt(id_vars=['Nombre', 'Ciudad'], var_name='Mes', value_name='Ventas').fillna(0)
df_maquilas_melt = df_maquilas_raw.melt(id_vars=['Nombre', 'Ciudad'], var_name='Mes', value_name='Maquilas').fillna(0)

# Filtrar por rango oficial
df_ventas_melt = df_ventas_melt[df_ventas_melt['Mes'].isin(columnas_master)]

# Resúmenes mensuales básicos
df_ventas_mensual = df_ventas_melt.groupby('Mes', as_index=False)['Ventas'].sum()
df_maquilas_mensual = df_maquilas_melt.groupby('Mes', as_index=False)['Maquilas'].sum()

df_compras_reales = df_ventas_melt[df_ventas_melt['Ventas'] > 0].copy()
df_clientes_activos = df_compras_reales.groupby('Mes')['Nombre'].nunique().reset_index(name='Clientes_Mensuales')

df_compras_reales['Mes_Orden'] = df_compras_reales['Mes'].map(posicion_meses)
df_primera_compra = df_compras_reales.sort_values('Mes_Orden').groupby('Nombre')['Mes'].first().reset_index()
df_clientes_nuevos = df_primera_compra.groupby('Mes')['Nombre'].count().reset_index(name='Clientes_Nuevos')

df_final = pd.merge(df_ventas_mensual, df_maquilas_mensual, on='Mes', how='outer')
df_final = pd.merge(df_final, df_clientes_activos, on='Mes', how='left')
df_final = pd.merge(df_final, df_clientes_nuevos, on='Mes', how='left')
df_final['Mes_Orden'] = df_final['Mes'].map(posicion_meses)
df_final = df_final.sort_values('Mes_Orden').drop(columns=['Mes_Orden']).fillna(0)

# CÁLCULOS KPI GENERALES
ventas_totales_global = df_final['Ventas'].sum()
total_clientes_unicos = df_ventas_raw['Nombre'].nunique()

df_ranking_clientes = df_ventas_melt.groupby('Nombre', as_index=False)['Ventas'].sum()
cliente_top_info = df_ranking_clientes.sort_values('Ventas', ascending=False).iloc[0]
cliente_top_nombre = cliente_top_info['Nombre']
cliente_top_ventas = cliente_top_info['Ventas']

df_ranking_ciudades = df_ventas_melt.groupby('Ciudad', as_index=False)['Ventas'].sum()
ciudad_lider_info = df_ranking_ciudades.sort_values('Ventas', ascending=False).iloc[0]
ciudad_lider_nombre = ciudad_lider_info['Ciudad']
ciudad_lider_ventas = ciudad_lider_info['Ventas']

promedio_mensual_por_cliente = (ventas_totales_global / total_clientes_unicos) / len(columnas_master)

# =========================================================
# PREPARACIÓN MATEMÁTICA PARA EL MODELO K-MEANS AVANZADO
# =========================================================
# Calcular métricas requeridas por cliente: Total Anual, Promedio Mensual y Meses Activos
df_perf_km = df_ventas_melt[df_ventas_melt['Ventas'] > 0].groupby('Nombre').agg(
    Total_Anual=('Ventas', 'sum'),
    Promedio_Mensual=('Ventas', 'mean'),
    Meses_Activos=('Mes', 'count')
).reset_index()

# Forzar matriz de datos para clustering
X_km = df_perf_km[['Promedio_Mensual', 'Total_Anual']].values

# Precalcular curvas del método del codo y silueta para los gráficos estadísticos (Rango de K de 2 a 8)
inercias = []
siluetas = []
rango_k = list(range(2, 9))
for k in rango_k:
    km_temp = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X_km)
    inercias.append(km_temp.inertia_)
    siluetas.append(silhouette_score(X_km, km_temp.labels_))

try:
    encoded_image = base64.b64encode(open('logo.png', 'rb').read())
    logo_src = f'data:image/png;base64,{encoded_image.decode()}'
except Exception:
    logo_src = ""

# =========================================================
# 2. CONFIGURACIÓN DEL DASHBOARD INTERACTIVO (DASH)
# =========================================================
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.FLATLY, "https://googleapis.com"],
    title="Dashboard Comercial Avanzado"
)
server = app.server

CARD_STYLE = {"box-shadow": "0 4px 15px rgba(0, 0, 0, 0.05)", "border-radius": "15px", "padding": "25px", "border": "none", "background-color": "#ffffff"}

app.layout = dbc.Container([
    # Encabezado Corporativo Izquierdo
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Img(src=logo_src, style={'height': '60px', 'margin-bottom': '5px'}) if logo_src else html.Div(),
                html.H6("ASPM - CANAL B2B", className="text-muted fw-bold", style={'font-size': '11px', 'letter-spacing': '1.5px', 'margin': '0'})
            ], style={'display': 'flex', 'flex-direction': 'column', 'align-items': 'flex-start'})
        ], width=4, className="d-flex align-items-center pt-3"),
        
        dbc.Col([
            html.H3("Panel Analítico Comercial Inteligente", className="fw-bold text-end text-dark m-0 w-100")
        ], width=8, className="d-flex align-items-center justify-content-end pt-3")
    ], className="mb-3 border-bottom pb-3"),
    
    # Sistema de Pestañas con Nombres Oficiales solicitados
    dcc.Tabs(id="tabs-navegacion", value='tab-principal', children=[
        dcc.Tab(label='📌 Resumen', value='tab-principal'),
        dcc.Tab(label='🌡️ Heatmap & Pearson', value='tab-pearson'),
        dcc.Tab(label='🔵 K-Means', value='tab-kmeans'),
    ], className="mb-4", style={'font-family': 'Inter, sans-serif', 'font-weight': '600'}),
    
    html.Div(id='contenido-pestana')
], fluid=True)

# =========================================================
# 3. LÓGICA DE PROCESAMIENTO DINÁMICO DE PESTAÑAS
# =========================================================
@app.callback(
    Output('contenido-pestana', 'children'),
    [Input('tabs-navegacion', 'value')]
)
def alternar_pestanas(tab_seleccionada):
    if tab_seleccionada == 'tab-principal':
        # Gráfico 1: Evolución Temporal
        fig_comercial = px.line(df_final, x='Mes', y=['Ventas', 'Maquilas'], labels={'value': 'Monto ($)', 'variable': 'Métrica'}, template="plotly_white", color_discrete_sequence=["#0d6efd", "#ffc107"])
        fig_comercial.update_layout(margin=dict(l=20, r=20, t=10, b=20), legend=dict(orientation="h", y=1.1))
        
        # CORRECCIÓN PASTEL: Limpiar líneas externas y mover nombres a leyenda lateral limpia
        df_ciudades = df_ventas_melt.groupby('Ciudad', as_index=False)['Ventas'].sum()
        fig_pastel = px.pie(df_ciudades, values='Ventas', names='Ciudad', title="Participación de Ventas por Ciudad", hole=0.4, template="plotly_white")
        fig_pastel.update_traces(textinfo='percent', textposition='inside') # Remueve etiquetas externas
        fig_pastel.update_layout(showlegend=True, legend=dict(orientation="v", align="left"))
        
        # CORRECCIÓN TOP 10 CLIENTES: Mostrar valores limpios frente a cada barra horizontal
        df_top_10 = df_ranking_clientes.sort_values('Ventas', ascending=False).head(10)
        fig_top_10 = px.bar(
            df_top_10, x='Ventas', y='Nombre', orientation='h',
            template="plotly_white", color='Ventas', color_continuous_scale="Blues", text_auto='.2s'
        )
        fig_top_10.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False, coloraxis_showscale=False, margin=dict(l=20, r=20, t=10, b=20))
        fig_top_10.update_traces(textposition='outside', cliponaxis=False) # Valores limpios fuera de la barra
        
        fig_clientes = px.bar(df_final, x='Mes', y=['Clientes_Mensuales', 'Clientes_Nuevos'], barmode='group', template="plotly_white", color_discrete_sequence=["#198754", "#0dcaf0"])
        fig_clientes.update_layout(margin=dict(l=20, r=20, t=10, b=20), legend=dict(orientation="h", y=1.1))
        
        return html.Div([
            # 4 Recuadros Grandes estilo Compañero
            dbc.Row([
                dbc.Col(dbc.Card([html.H6("1. DESEMPEÑO GLOBAL COMERCIAL", className="text-muted small fw-bold mb-2"), html.H3(f"${ventas_totales_global:,.2f}", className="text-primary fw-bold mb-1"), html.P(f"Clientes Activos Totales: {total_clientes_unicos}", className="text-secondary small m-0 fw-medium")], style=CARD_STYLE), width=3),
                dbc.Col(dbc.Card([html.H6("2. CLIENTE TOP MUNDIAL", className="text-muted small fw-bold mb-2"), html.H5(f"{cliente_top_nombre}", className="text-dark fw-bold text-truncate mb-1"), html.P(f"Total de Compra: ${cliente_top_ventas:,.2f}", className="text-success small m-0 fw-medium")], style=CARD_STYLE), width=3),
                dbc.Col(dbc.Card([html.H6("3. CIUDAD LÍDER EN MERCADO", className="text-muted small fw-bold mb-2"), html.H3(f"{ciudad_lider_nombre}", className="text-warning fw-bold mb-1"), html.P(f"Aporte Región: ${ciudad_lider_ventas:,.2f}", className="text-secondary small m-0 fw-medium")], style=CARD_STYLE), width=3),
                dbc.Col(dbc.Card([html.H6("4. PROMEDIO MENSUAL POR CLIENTE", className="text-muted small fw-bold mb-2"), html.H3(f"${promedio_mensual_por_cliente:,.2f}", className="text-info fw-bold mb-1"), html.P("Cálculo medio ponderado", className="text-secondary small m-0")], style=CARD_STYLE), width=3),
            ], className="g-3 mb-4"),
            
            dbc.Row([
