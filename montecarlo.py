import numpy as np
import matplotlib.pyplot as plt
import os

# Define a função de custo que calcula as incertezas internamente
def cost_function(estimativa, faixas, probs, n, disponivel):
    
    """ 
    estimativa se refere à etimativa de custo de cada projeto, vem da lista de projetos
    faixas_p se refere às faixas de variação histórica entre a estimativa preliminar e o valor final do projeto
    probs_p se refere à probabilidade de cada faixa variação histórica entre a estimativa preliminar
        e o valor final do projeto
    faixas_o se refere às faixas de variação histórica entre o valor final do projeto e o valor final da obra
    probs_o se refere à probabilidade de cada faixa variação histórica entre o valor final do projeto 
        e o valor final da obra
    faixas_d se refere refere às faixas de variação histórica de orçamento disponível para execução 
        das obras referentes aos projetos da carteira
    probs_d se refere à probabilidade de cada faixa variação histórica de orçamento disponível para execução 
        das obras referentes aos projetos da carteira
    n é a quantidade de projetos da carteira, vem da lista de projetos
    disponível é a expectativa de orçamento disponível para a execução das obras referentes
        aos projetos da carteira para o ano em análise
    """
    
    # Gera um único valor para 'delta_d'
    delta_d = np.random.choice(faixas['orc_disponivel'], 1, p=probs['orc_disponivel'])
    
    # Verificações iniciais
    if disponivel == 0:
        raise ValueError("Erro: 'disponivel' é zero.")
    if delta_d == -1:
        raise ValueError("Erro: 'delta_d' tem valor -1, o que causaria divisão por zero.")
    
    cost_rate = 0
    for i in range(n):
        # Gere um único valor para 'delta_p' e 'delta_o'
        delta_p = np.random.choice(faixas['projeto'], 1, p=probs['projeto'])
        delta_o = np.random.choice(faixas['obra'], 1, p=probs['obra'])
        
        if np.isnan(estimativa[i]):
            raise ValueError(f"Erro: 'estimativa' no índice {i} é NaN.")
        
        cost_rate += (estimativa[i] * (1 + delta_p) * (1 + delta_o))
    cost_rate = cost_rate/(disponivel * (1 + delta_d)) 
    
    # Retorna uma lista de escalares
    return {"cost_rate": cost_rate}

def time_function(estimativa_hh, faixas, probs, n, hh_disponivel):
    """ 
    estimativa_hh se refere à etimativa de homem-hora que se gastará por projeto, vem da lista de projetos
    faixas_mo se refere às faixas de variação histórica de mão de obra efetivamente gasta para elabração de projetos
    probs_mo se refere à probabilidade de cada faixa variação histórica de mão de obra efetivamente gasta para elabração de projetos
    faixas_hd se refere refere às faixas de variação histórica de mão de obra disponível para elabração dos projetos da carteira
    probs_hd se refere à probabilidade de cada faixa variação histórica de mão de obra disponível para elabração dos projetos da carteira
    n é a quantidade de projetos da carteira, vem da lista de projetos
    hh_disponível é a expectativa de hh disponível para elabração dos projetos da carteira para o ano em análise
    """

    # Gera um único valor para 'delta_d'
    delta_hd = np.random.choice(faixas['hh_disponivel'], 1, p=probs['hh_disponivel'])
    
    # Verificações iniciais
    if hh_disponivel == 0:
        raise ValueError("Erro: 'disponivel' é zero.")
    if delta_hd == -1:
        raise ValueError("Erro: 'delta_d' tem valor -1, o que causaria divisão por zero.")
    
    time_rate = 0
    for i in range(n):
        # Gera um único valor para 'delta_mo'
        delta_mo = np.random.choice(faixas['mao_de_obra'], 1, p=probs['mao_de_obra'])
        
        if np.isnan(estimativa_hh[i]):
            raise ValueError(f"Erro: 'estimativa' no índice {i} é NaN.")
        
        time_rate += (estimativa_hh[i] * (1 + delta_mo))
    time_rate =  time_rate/(hh_disponivel * (1 + delta_hd)) 
    
    # Retorna uma lista de escalares
    return {"time_rate": time_rate}


def montecarlo_orc(estimativa, faixas, probs, n, disponivel, nrep, min_crit, max_crit):
    # Lista para armazenar os resultados
    results = []

    # Executa a simulação de Monte Carlo
    for _ in range(nrep):
        results.append(cost_function(estimativa, faixas, probs, n, disponivel)["cost_rate"])

    # Converte os resultados em um array para análise
    frame = np.array(results)

    # Imprime o frame para visualização dos resultados
    #print(frame)

    # Verifica quantos cenários percentualmente atenderam ao critério de aceitação (entre 100% e 120%)
    in_crit = np.sum((frame >= min_crit) & (frame <= max_crit)) / len(frame)
    #print(in_crit)
    return in_crit, frame

def montecarlo_hh(estimativa_hh, faixas, probs, n, hh_disponivel, nrep, min_crit, max_crit):
    # Lista para armazenar os resultados
    results_hh = []

    # Executa a simulação de Monte Carlo
    for _ in range(nrep):
        results_hh.append(time_function(estimativa_hh, faixas, probs, n, hh_disponivel)["time_rate"])

    # Converte os resultados em um array para análise
    frame_hh = np.array(results_hh)

    # Imprime o frame para visualização dos resultados
    #print(frame_hh)

    # Verifica quantos cenários percentualmente atenderam ao critério de aceitação (entre 100% e 120%)
    in_crit_hh = np.sum((frame_hh >= min_crit) & (frame_hh <= max_crit)) / len(frame_hh)
    #print(in_crit_hh)
    return in_crit_hh, frame_hh
