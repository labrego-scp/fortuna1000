import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import base64
import io
import re

def create_histogram(data, title):
    plt.figure(figsize=(8, 5))
    plt.hist(data, bins='auto', alpha=0.7, rwidth=0.85, color='black')
    plt.title(title)
    plt.xlabel('Variação percentual')
    plt.ylabel('Frequência absoluta')
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()  # Fechando a figura explicitamente
    buf.seek(0)
    img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    plt.close()
    return img_base64


def create_scatter(x, y, title, n, highlight_index=None):
    plt.figure(figsize=(8, 5))

    # Definindo as cores: azul escuro para o ponto destacado, cinza claro para os outros
    colors = ['lightgray'] * len(x)  # Todos os pontos inicialmente em cinza claro

    if highlight_index is not None:
        colors[highlight_index - 1] = 'darkblue'  # Destaca o ponto específico em azul escuro

    plt.scatter(x, y*100, color=colors)
    plt.xlabel('Qtde de Projetos')
    plt.ylabel('Percentual que atendeu ao critério')
    plt.xticks(range(1, n + 1, 5))  # Ajuste dos rótulos do eixo x
    plt.title(title)
    scatter_img = io.BytesIO()
    plt.savefig(scatter_img, format='png')
    plt.close()  # Fechando a figura explicitamente
    scatter_img.seek(0)
    scatter_base64 = base64.b64encode(scatter_img.getvalue()).decode('utf-8')
    return scatter_base64


# Função para remover caracteres não numéricos
def clean_numeric(value):
    return re.sub(r'[^\d,]', '', value).replace(',', '.')

# Formata a linha para exibição da tabela destcando os projetos da carteira ótima
def custom_formatter_id(row, prioridade_associada):
    # Verifica se o ID-PW da linha atual está na lista de ids_associados
     # Verifica se o valor atual está na lista de prioridades associadas
    if row['PRIORIDADE'] <= prioridade_associada:
        # Se estiver, retorna HTML com a classe de destaque para toda a linha
        #return [f'<span class="highlight">{cell}</span>' for cell in row]
        #return ''.join([f'<span class="highlight">{cell}</span>' for cell in row])
        return f'<span class="highlight">{row[1]}</span>'
    else:
        # Se não estiver, retorna o valor original convertido para string
        #return [str(cell) for cell in row]
        #return ''.join([f'<span class="downlight">{row[1]}</span>' for cell in row])
        return f'<span class="downlight">{row[1]}</span>'

def custom_formatter_prior(value, prioridade_associada):
    # Verifica se o ID-PW da linha atual está na lista de ids_associados
     # Verifica se o valor atual está na lista de prioridades associadas
    if value <= prioridade_associada:
        # Se estiver, retorna HTML com a classe de destaque para o valor
        return f'<span class="highlight">{value}</span>'
    else:
        # Se não estiver, retorna o valor original convertido para string
        return f'<span class="downlight">{value}</span>'
    