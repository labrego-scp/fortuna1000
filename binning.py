import pandas as pd
import numpy as np
from scipy.stats import iqr

def freedman(df):

    # Calculando a largura do bin usando a regra de Freedman-Diaconis
    n = len(df['VARIAÇÃO'])
    bin_width = 2 * iqr(df['VARIAÇÃO']) / np.cbrt(n)

    # Calculando o número de bins
    bins = int(np.ceil((df['VARIAÇÃO'].max() - df['VARIAÇÃO'].min()) / bin_width))

    # Criando os bins
    df['bin'] = pd.cut(df['VARIAÇÃO'], bins=bins)

    # Calculando a média de cada bin
    df_grouped = df.groupby('bin')['VARIAÇÃO'].mean().reset_index()

    return(df_grouped)

def calculate_probabilities(df, df_grouped):
    # Calculando o número total de pontos de dados
    total_points = len(df)

    # Calculando a probabilidade de cada bin
    df_grouped['probability'] = df_grouped['bin'].apply(lambda x: len(df[df['bin'] == x]) / total_points)

    return df_grouped

def calculate_counts(df, df_grouped):
    # Calculando o número de observações em cada bin
    df_grouped['count'] = df_grouped['bin'].apply(lambda x: len(df[df['bin'] == x]))

    return df_grouped

# def main():
    
#     # Carregando os dados do Excel
#     df = pd.read_excel('projeto_x_obra.xlsx')

#     df_grouped = freedman(df)

#     df_grouped = calculate_probabilities(df, df_grouped)

#     df_grouped = calculate_counts(df, df_grouped)

#     print(df_grouped['probability'])

# main()


