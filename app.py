# app.py
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# -----------------------
# Generación sintética de iniciativas
# -----------------------
def generar_iniciativa(tipo, costo_fijo_cat, costo_var_cat, ingreso_speed, impacto_cat, total_meses=37):
    meses = np.arange(total_meses)
    
    # COSTOS FIJOS
    cf_map = {'bajo': 1.0, 'medio': 2.0, 'alto': 4.0}
    base_cf = cf_map[costo_fijo_cat] * (0.95 if tipo == 'disruptivo' else 1.0)
    costos_fijos = np.full(total_meses, base_cf * 2.0)

    # COSTOS VARIABLES
    def gauss(x, center, amplitude, width=2.0):
        return amplitude * np.exp(-0.5*((x - center)/width)**2)
    
    if costo_var_cat == 'pico1':
        costos_variables = gauss(meses, 5, 3.0, 2.0)
    else:
        costos_variables = gauss(meses, 4, 2.5, 2.0) + gauss(meses, 12, 3.5, 2.0)
    
    if tipo == 'disruptivo':
        costos_variables *= 0.95
    
    # INGRESOS + AHORROS
    speed_map = {'rapido': (6,12), 'medio': (10,20), 'lento': (12,24)}
    start_i, peak_i = speed_map[ingreso_speed]

    impact_map = {'bajo': 0.6, 'medio': 1.0, 'alto': 1.4}
    impact_factor = impact_map[impacto_cat] * (1.1 if tipo == 'disruptivo' else 1.0)

    ingresos = np.zeros(total_meses)
    peak_val = 12.0 * impact_factor

    def p_poly(t):
        return t**2

    for i in range(total_meses):
        if i >= start_i:
            t = i - start_i
            if i <= peak_i:
                ingresos[i] = peak_val * (p_poly(t) / p_poly(peak_i - start_i + 1)) 
            else:
                ingresos[i] = peak_val

    # BENEFICIO NETO
    bn_mensual = ingresos - (costos_fijos + costos_variables)
    bn_acum = np.cumsum(bn_mensual)

    return {
        'tipo': tipo,
        'costos_fijos': costos_fijos,
        'costos_variables': costos_variables,
        'ingresos': ingresos,
        'bn_mensual': bn_mensual,
        'bn_acum': bn_acum
    }

# -----------------------
# Streamlit App
# -----------------------
def main():
    # Información Autor
    st.sidebar.markdown("## Autor")
    st.sidebar.markdown("[Roberto Moraga-Diaz](https://www.linkedin.com/in/robertomoragad/)")
    st.sidebar.markdown("[GitHub](https://github.com/robertomoragad/)")
    st.sidebar.markdown("[Artículo completo](https://www.linkedin.com/posts/tata-consultancy-services-latam_whitepaper-portafoliodigital-v103pdf-activity-7323032704143323136-8QsJ?utm_source=share&utm_medium=member_desktop&rcm=ACoAAAFVpicBG_Fz3DOf6nB8fJBPCA5mmCWY9qo)")

    st.title("Prototipo para Priorizar un Portafolio de Iniciativas (Clásico vs Disruptivo)")

    st.markdown("""
    Este prototipo permite a los usuarios definir y priorizar iniciativas digitales con diferentes perfiles de costos (fijos y variables), ingresos y velocidad de monetización. Cada iniciativa puede clasificarse como clásica o disruptiva, definiendo escenarios específicos para simular y evaluar cómo maximizar el Beneficio Neto Acumulado (BNA) al mes seleccionado.
    """)

    # Parámetros Globales
    st.subheader("Configuración Inicial")
    num_iniciativas = st.number_input("Número de iniciativas en Backlog", 1, 100, 10)
    horizon_mes = st.number_input("Mes para evaluar BNA (Beneficio Neto Acumulado)", 1, 36, 24)

    # Construcción Backlog
    df_backlog = []

    for i in range(num_iniciativas):
        st.markdown(f"### Parámetros para Iniciativa {i+1}")
        tipo_opt = st.selectbox("Tipo", ['clasico', 'disruptivo'], key=f"tipo_{i}")
        cf_opt = st.selectbox("Costos Fijos", ['bajo', 'medio', 'alto'], key=f"cf_{i}")
        cv_opt = st.selectbox("Costos Variables", ['pico1', 'pico2'], key=f"cv_{i}")
        ing_opt = st.selectbox("Velocidad Ingresos/Ahorros", ['rapido', 'medio', 'lento'], key=f"ing_{i}")
        imp_opt = st.selectbox("Impacto", ['bajo', 'medio', 'alto'], key=f"imp_{i}")

        data = generar_iniciativa(tipo_opt, cf_opt, cv_opt, ing_opt, imp_opt, total_meses=37)
        bnX = data['bn_acum'][horizon_mes]

        df_backlog.append({
            'ID': i+1,
            'Tipo': tipo_opt,
            'CF': cf_opt,
            'CV': cv_opt,
            'Ingr-Speed': ing_opt,
            'Impacto': imp_opt,
            f'BNA @ mes{horizon_mes}': round(bnX, 2),
            'data': data
        })

    st.subheader("Backlog Actual (simplificado)")
    backlog_table = pd.DataFrame(df_backlog).drop('data', axis=1)
    st.dataframe(backlog_table.set_index('ID'))

    # Selección de proyectos
    st.subheader("Selección y Prioridad")
    num_ejecutar = st.slider("Número de proyectos a ejecutar (priorizados por BNA)", 1, num_iniciativas, min(num_iniciativas,5))

    # Ordenar y elegir top proyectos
    df_sorted = sorted(df_backlog, key=lambda x: x[f'BNA @ mes{horizon_mes}'], reverse=True)
    chosen = df_sorted[:num_ejecutar]

    chosen_table = pd.DataFrame(chosen).drop('data', axis=1)
    chosen_table.insert(0, 'Ranking', range(1, len(chosen_table) + 1))
    st.write(f"Seleccionamos los {num_ejecutar} proyectos con mayor BNA al mes {horizon_mes}.")
    st.dataframe(chosen_table.set_index('Ranking'))

    # Curva Agregada BNA
    st.subheader("Curva Agregada del Portafolio Seleccionado")
    curve_sum = np.zeros(37)

    for proj in chosen:
        curve_sum += proj['data']['bn_acum']

    final_bnX = curve_sum[horizon_mes]

    fig, ax = plt.subplots(figsize=(10,5))
    ax.plot(np.arange(37), curve_sum, label='BNA Agregado', color='blue')
    ax.axhline(0, color='black', linestyle='--')
    ax.axvline(horizon_mes, color='red', linestyle='--')
    ax.axhline(final_bnX, color='green', linestyle='--')
    ax.scatter(horizon_mes, final_bnX, color='purple', zorder=5)

    ax.set_xlim(0, 36)
    ax.set_title('Curva Global de Monetización (BNA)')
    ax.set_xlabel('Mes')
    ax.set_ylabel('BNA (Unidades)')
    ax.grid(True)
    ax.legend()

    st.pyplot(fig)
    st.write(f"**Beneficio Neto Acumulado del Portafolio al mes {horizon_mes}: {final_bnX:.2f}**")

if __name__ == "__main__":
    main()


