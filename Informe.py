import dash
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px

# =========================================================
# 1. ENLAZAR EXCEL Y PREPARAR DATOS
# =========================================================
archivo_excel = "Informe_Tribu.xlsx"

# Leer las hojas del archivo Excel
df_ventas_raw = pd.read_excel(archivo_excel, sheet_name='ventas totales')
df_maquilas_raw = pd.read_excel(archivo_excel, sheet_name='maquilas')

# Capturar las columnas de meses en su orden original de Excel
columnas_meses = [col for col in df_ventas_raw.columns if col not in ['Nombre', 'Ciudad']]

# A. Desenrollar VENTAS a formato vertical
df_ventas_melt = df_ventas_raw.melt(id_vars=['Nombre', 'Ciudad'], var_name='Mes', value_name='Ventas')
df_ventas_melt['Ventas'] = df_ventas_melt['Ventas'].fillna(0)

# B. LÓGICA DE CLIENTES (A partir de compras reales)
df_compras_reales = df_ventas_melt[df_ventas_melt['Ventas'] > 0].copy()

# Clientes Mensuales Activos
df_clientes_activos = df_compras_reales.groupby('Mes')['Nombre'].nunique().reset_index()
df_clientes_activos.columns = ['Mes', 'Clientes_Mensuales']

# Clientes Nuevos
posicion_meses = {mes: i for i, mes in enumerate(columnas_meses)}
df_compras_reales['Mes_Orden'] = df_compras_reales['Mes'].map(posicion_meses)
df_primera_compra = df_compras_reales.sort_values('Mes_Orden').groupby('Nombre')['Mes'].first().reset_index()
df_primera_compra.columns = ['Nombre', 'Mes']
df_clientes_nuevos = df_primera_compra.groupby('Mes')['Nombre'].count().reset_index()
df_clientes_nuevos.columns = ['Mes', 'Clientes_Nuevos']

# C. Desenrollar MAQUILAS a formato vertical
df_maquilas_melt = df_maquilas_raw.melt(id_vars=['Nombre', 'Ciudad'], var_name='Mes', value_name='Maquilas')
df_maquilas_mensual = df_maquilas_melt.groupby('Mes', as_index=False)['Maquilas'].sum()

# D. Sumar Ventas totales mensuales
df_ventas_mensual = df_ventas_melt.groupby('Mes', as_index=False)['Ventas'].sum()

# E. UNIÓN FINAL EN TABLA MAESTRA
df_final = pd.merge(df_ventas_mensual, df_maquilas_mensual, on='Mes', how='outer')
df_final = pd.merge(df_final, df_clientes_activos, on='Mes', how='left')
df_final = pd.merge(df_final, df_clientes_nuevos, on='Mes', how='left')

# F. ORDENAR CRONOLÓGICAMENTE SEGÚN TU EXCEL
df_final['Mes_Orden'] = df_final['Mes'].map(posicion_meses)
df_final = df_final.sort_values('Mes_Orden').drop(columns=['Mes_Orden']).fillna(0)

# G. DATOS ADICIONALES PARA CIUDADES, PEARSON Y K-MEANS
df_ciudades = df_ventas_melt.groupby('Ciudad', as_index=False)['Ventas'].sum()

# =========================================================
# GENERACIÓN DE GRÁFICOS ESTÁTICOS INICIALES (EVITA ERRORES EN NUBE)
# =========================================================
fig_comercial = px.line(
    df_final, x='Mes', y=['Ventas', 'Maquilas'],
    labels={'value': 'Monto / Cantidad', 'variable': 'Métrica'},
    template="plotly_white", color_discrete_sequence=["#0d6efd", "#ffc107"]
)
fig_comercial.update_layout(margin=dict(l=20, r=20, t=10, b=20), legend=dict(orientation="h", y=1.1))

fig_ciudades = px.bar(
    df_ciudades, x='Ciudad', y='Ventas', 
    title="Ventas Consolidadas por Ciudad", template="plotly_white", color='Ciudad'
)

# =========================================================
# 2. CONFIGURACIÓN DEL DASHBOARD (DASH)
# =========================================================
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.FLATLY, "https://googleapis.com"],
    title="Dashboard EDA — Ventas"
)
server = app.server  # Enlace crucial para Render

CARD_STYLE = {"box-shadow": "0 4px 6px rgba(0, 0, 0, 0.05)", "border-radius": "12px", "padding": "20px", "border": "none"}

# Layout directo con los gráficos precargados (Soluciona la pantalla blanca)
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H2("Dashboard de Control Comercial", className="fw-bold my-4 text-dark"), width=12)
    ]),
    
    # Fila de Tarjetas (Resumen Histórico Total)
    dbc.Row([
        dbc.Col(dbc.Card([
            html.H6("VENTAS TOTALES HISTÓRICAS", className="text-muted small fw-bold"),
            html.H3(f"${df_final['Ventas'].sum():,.2f}", className="text-primary fw-bold m-0")
        ], style=CARD_STYLE), width=4),
        
        dbc.Col(dbc.Card([
            html.H6("TOTAL CLIENTES NUEVOS", className="text-muted small fw-bold"),
            html.H3(f"+{int(df_final['Clientes_Nuevos'].sum())}", className="text-info fw-bold m-0")
        ], style=CARD_STYLE), width=4),
        
        dbc.Col(dbc.Card([
            html.H6("TOTAL MAQUILAS GENERADAS", className="text-muted small fw-bold"),
            html.H3(f"{int(df_final['Maquilas'].sum()):,}", className="text-warning fw-bold m-0")
        ], style=CARD_STYLE), width=4),
    ], className="g-3 mb-4"),
    
    # Fila de Gráficos de la pestaña principal
    dbc.Row([
        dbc.Col(dbc.Card([
            html.H5("Evolución Mensual Financiera", className="fw-bold text-secondary mb-3"),
            dcc.Graph(figure=fig_comercial) # <--- Cargado directamente
        ], style=CARD_STYLE), width=6),
        
        dbc.Col(dbc.Card([
            html.H5("Distribución Comercial por Región", className="fw-bold text-secondary mb-3"),
            dcc.Graph(figure=fig_ciudades) # <--- Cargado directamente
        ], style=CARD_STYLE), width=6),
    ], className="g-3 mb-4"),

    # Fila de Tabla
    dbc.Row([
        dbc.Col(dbc.Card([
            html.H5("Consolidado Mensual de Datos", className="fw-bold text-secondary mb-3"),
            dash_table.DataTable(
                data=df_final.to_dict('records'),
                columns=[
                    {"name": "Mes", "id": "Mes"},
                    {"name": "Ventas ($)", "id": "Ventas", "type": "numeric", "format": {"specifier": "$,.2f"}},
                    {"name": "Maquilas (Cant)", "id": "Maquilas", "type": "numeric"},
                    {"name": "Clientes Activos", "id": "Clientes_Mensuales", "type": "numeric"},
                    {"name": "Clientes Nuevos", "id": "Clientes_Nuevos", "type": "numeric"}
                ],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'center', 'font-family': 'Inter, sans-serif', 'padding': '12px'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold', 'borderBottom': '2px solid #dee2e6'}
            )
        ], style=CARD_STYLE), width=12)
    ], className="mb-5")
], fluid=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
