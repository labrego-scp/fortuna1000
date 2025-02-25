import numpy as np
import os
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.ticker as mticker
from tkinter import filedialog
from scipy.stats import norm
import base64
import io

def teste_z(z,min_crit_orc,max_crit_orc,min_crit_hh,max_crit_hh):
    # Define parâmetros
    significancia = {1.96: 0.05, 2.57: 0.01, 2.8: 0.005}
    tol_sup_orc = max_crit_orc
    tol_inf_orc = min_crit_orc
    tol_sup_hh = max_crit_hh
    tol_inf_hh = min_crit_hh

    
    file_path_orc = 'outputs\output_orc.csv'
    file_path_hh = 'outputs\output_hh.csv'

    df_frames_orc = pd.read_csv(file_path_orc).T
    df_frames_orc = df_frames_orc.drop(index='Cenário')
    df_frames_hh = pd.read_csv(file_path_hh).T
    df_frames_hh = df_frames_hh.drop(index='Cenário')

    # Contar o número de observações em cada linha que estão entre os limites de tolerância
    count_in_range_orc = ((df_frames_orc > tol_inf_orc) & (df_frames_orc < tol_sup_orc)).sum(axis=1)
    count_in_range_hh = ((df_frames_hh > tol_inf_hh) & (df_frames_hh < tol_sup_hh)).sum(axis=1)

    # Calcular a proporção de observações em cada linha que estão nesse intervalo
    n = df_frames_orc.shape[1]  # Total de colunas (observações) em cada linha
    proportion_in_range_orc = count_in_range_orc / n
    proportion_in_range_hh = count_in_range_hh / n

    # Criar um novo DataFrame com 1 coluna e i (cenários) linhas
    df_orc = pd.DataFrame(proportion_in_range_orc, columns=['rOrc'])
    df_hh = pd.DataFrame(proportion_in_range_hh, columns=['rHH'])

    # Calcula a probabilidade de menor risco
    p_orc = df_orc['rOrc'].max()
    p_hh = df_hh['rHH'].max()

    # Define a coluna do teste Z
    df_orc['pooled_proportion'] = (df_orc['rOrc']+p_orc)/2
    df_orc['Teste Z'] = (p_orc-df_orc['rOrc'])/np.sqrt(df_orc['pooled_proportion']*(1-df_orc['pooled_proportion'])*(1/n + 1/n))

    df_hh['pooled_proportion'] = (df_hh['rHH']+p_hh)/2
    df_hh['Teste Z'] = (p_hh-df_hh['rHH'])/np.sqrt(df_hh['pooled_proportion']*(1-df_hh['pooled_proportion'])*(1/n + 1/n))

    # Calcula o IC
    delta_ic_orc = z * np.sqrt(p_orc * (1 - p_orc) / n)
    delta_ic_hh = z * np.sqrt(p_hh * (1 - p_hh) / n)

    # Define os limites do IC para cada carteira
    df_orc['lim inf ic'] = df_orc['rOrc'] - delta_ic_orc
    df_orc['lim sup ic'] = df_orc['rOrc'] + delta_ic_orc

    df_hh['lim inf ic'] = df_hh['rHH'] - delta_ic_hh
    df_hh['lim sup ic'] = df_hh['rHH'] + delta_ic_hh

    df_orc['errors'] = (df_orc['lim sup ic'] - df_orc['lim inf ic']) / 2
    df_hh['errors'] = (df_hh['lim sup ic'] - df_hh['lim inf ic']) / 2

    df_orc.index = df_orc.index.to_series().str.replace('Carteira ', '', regex=False)
    df_hh.index = df_hh.index.to_series().str.replace('Carteira ', '', regex=False)

    # Encontre o índice do valor máximo de rGlobal
    max_index_orc = df_orc['rOrc'].idxmax()
    max_index_hh = df_hh['rHH'].idxmax()

    # Selecione as x carteiras anteriores e as x carteiras posteriores
    start_index_orc = int(max(float(max_index_orc) - 8, 0))  # Garante que o índice inicial não seja menor que 0
    end_index_orc = int(min(float(max_index_orc) + 8, len(df_orc) - 1))  # Garante que o índice final não seja maior que o total de linhas

    start_index_hh = int(max(float(max_index_hh) - 8, 0))  # Garante que o índice inicial não seja menor que 0
    end_index_hh = int(min(float(max_index_hh) + 8, len(df_hh) - 1))  # Garante que o índice final não seja maior que o total de linhas

    # Subconjunto do DataFrame para plotagem
    df_subset_orc = df_orc.iloc[start_index_orc:end_index_orc + 1]
    df_subset_hh = df_hh.iloc[start_index_hh:end_index_hh + 1]

    x_orc = df_subset_orc.index
    y_orc = df_subset_orc['rOrc']
    errors_orc = df_subset_orc['errors']

    x_hh = df_subset_hh.index
    y_hh = df_subset_hh['rHH']
    errors_hh = df_subset_hh['errors']

    # Obtenha os índices das linhas com os valores máximos e mínimos das colunas
    max_index_lim_sup_ic_orc = df_subset_orc['lim sup ic'].idxmax()
    max_index_lim_inf_ic_orc = df_subset_orc['lim inf ic'].idxmax()

    max_index_lim_sup_ic_hh = df_subset_hh['lim sup ic'].idxmax()
    max_index_lim_inf_ic_hh = df_subset_hh['lim inf ic'].idxmax()

    # Adicione as linhas de referência
    linha_ref_inf_orc = df_subset_orc.loc[max_index_lim_inf_ic_orc, 'lim inf ic']
    linha_ref_sup_orc = df_subset_orc.loc[max_index_lim_sup_ic_orc, 'lim sup ic']

    linha_ref_inf_hh = df_subset_hh.loc[max_index_lim_inf_ic_hh, 'lim inf ic']
    linha_ref_sup_hh = df_subset_hh.loc[max_index_lim_sup_ic_hh, 'lim sup ic']

    # Crie arrays com o mesmo tamanho que 'x' preenchidos com os valores máximos e mínimos
    linha_ref_inf_orc = np.full(len(x_orc), linha_ref_inf_orc, dtype=float)
    linha_ref_sup_orc = np.full(len(x_orc), linha_ref_sup_orc, dtype=float)

    linha_ref_inf_hh = np.full(len(x_hh), linha_ref_inf_hh, dtype=float)
    linha_ref_sup_hh = np.full(len(x_hh), linha_ref_sup_hh, dtype=float)

    ##### Construção do IC Global #####
    df = pd.DataFrame()
    df['rGlobal'] = df_orc['rOrc'] * df_hh['rHH']
    df['orc_mean'] = df_frames_orc.T.mean().to_list()
    df['hh_mean'] = df_frames_hh.T.mean().to_list()
    df['orc_var'] = (df_orc['rOrc']*(1-df_orc['rOrc']))/n
    df['hh_var'] = (df_hh['rHH']*(1-df_hh['rHH']))/n
    df['rGlobal_var'] = (df['orc_mean']**2)*df['hh_var']+(df['hh_mean']**2)*df['orc_var']+df['orc_var']*df['hh_var']
    df['rGlobal_sd'] = np.sqrt(df['rGlobal_var'])
    df['rGlobal_ic_sup'] = df['rGlobal'] + z*df['rGlobal_sd']
    df['rGlobal_ic_inf'] = df['rGlobal'] - z*df['rGlobal_sd']
    df['rGlobal_ic'] = z*df['rGlobal_sd']
    print(df['rGlobal_ic'][27])
    print(df)
    df = df[['rGlobal','rGlobal_ic','rGlobal_ic_inf','rGlobal_ic_sup','rGlobal_var']]

    ##### Teste Z #####
    max_index_global = df['rGlobal'].idxmax()
    df['Teste_Z'] = (df['rGlobal'][max_index_global]-df['rGlobal'])/np.sqrt(df['rGlobal_var'][max_index_global]+df['rGlobal_var'])
    # Cálculo do p-valor. 
    # Se o p-valor for menor que o nível de significância (geralmente 0,05),
    # você rejeita a hipótese nula e conclui que há uma diferença estatisticamente
    # significativa entre os produtos das proporções das carteiras.
    # Se o p-valor for maior, você não tem evidências suficientes para rejeitar a hipótese nula.
    df['p-valor'] = 2 * (1 - norm.cdf(abs(df['Teste_Z'])))

    ##### GRÁFICO #####

    # Selecione as x carteiras anteriores e as x carteiras posteriores
    start_index = int(max(float(max_index_global) - 8, 0))  # Garante que o índice inicial não seja menor que 0
    end_index = int(min(float(max_index_global) + 8, len(df) - 1))  # Garante que o índice final não seja maior que o total de linhas

    # Subconjunto do DataFrame para plotagem
    df_subset = df.iloc[start_index:end_index + 1]

    x = df_subset.index
    y = df_subset['rGlobal']
    errors = df_subset['rGlobal_ic']

    # Adicione as linhas de referência
    linha_ref_inf = df_subset.loc[max_index_global, 'rGlobal_ic_inf']
    linha_ref_sup = df_subset.loc[max_index_global, 'rGlobal_ic_sup']

    # Crie arrays com o mesmo tamanho que 'x' preenchidos com os valores máximos e mínimos
    linha_ref_inf = np.full(len(x), linha_ref_inf, dtype=float)
    linha_ref_sup = np.full(len(x), linha_ref_sup, dtype=float)

    # Adicione as linhas de referência
    plt.plot(x, linha_ref_inf, color='gray', linestyle='--')
    plt.plot(x, linha_ref_sup, color='gray', linestyle='--')

    # Preencha a área entre as linhas de referência
    plt.fill_between(x, linha_ref_inf, linha_ref_sup, color='gray', alpha=0.15)

    # Cria variáveis para armazenar as legendas
    legend_handles = []
    legend_labels = []

    # Inclui as dispersões com cores condicionais
    for i, (xi, yi, ei) in enumerate(zip(x, y, errors)):
        # Verifica se a barra de erro intercepta a área cinza
        if df_subset.loc[xi, 'p-valor'] > significancia[z]:
            color = 'blue'  # ponto fora da área cinza com teste p-valor maior que a significância do modelo
            label = f'Estatisticamente igual à melhor solução ao nível de significância de {significancia[z]*100}%'
            plt.text(i + 0.1, yi-0.05, f'{yi * 100:.1f}%', fontsize=8, ha='center', va='center', color='blue', fontweight='bold')
            # Adiciona a legenda manualmente apenas uma vez
            if label not in legend_labels:
                legend_handles.append(plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='blue', markersize=8))
                legend_labels.append(label)
        else:
            color = 'lightgray'  # ponto fora da zona cinza
            label = f'Estatisticamente diferente da melhor solução ao nível de significância de {significancia[z]*100}%'
            if label not in legend_labels:
                legend_handles.append(plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='lightgray', markersize=8))
                legend_labels.append(label)

        
        plt.errorbar(xi, yi, yerr=ei, fmt='o', ecolor=color, color=color, capsize=3)

    plt.xlabel('Carteira')
    plt.ylabel('Proporção $r_{global}$ (%)')
    plt.gca().yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=0))

    # Adiciona as legendas ao gráfico
    plt.legend(legend_handles, legend_labels, loc='lower center', bbox_to_anchor=(0.5, -0.15), ncol=1)

    # Salva o gráfico no caminho especificado
    #output_path = os.path.join('outputs', 'grafico_ic.png')
    #plt.savefig(output_path, bbox_inches='tight')  # Salva o gráfico e ajusta o espaço ao redor
    output = io.BytesIO()
    plt.savefig(output, format='png')
    plt.close()  # Fechando a figura explicitamente
    output.seek(0)
    output_base64 = base64.b64encode(output.getvalue()).decode('utf-8')

    return output_base64