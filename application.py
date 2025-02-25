from flask import Flask, request, render_template, send_from_directory, abort
import pandas as pd
import re
import os
from werkzeug.utils import secure_filename
from binning import freedman, calculate_probabilities, calculate_counts
from montecarlo import montecarlo_orc, montecarlo_hh
from grafico_ic import teste_z
from helpers import create_histogram, create_scatter, clean_numeric, custom_formatter_id, custom_formatter_prior
import time
import matplotlib
matplotlib.use('Agg')



app = Flask(__name__)

MODELS_FOLDER = 'models'

@app.route('/', methods=['GET', 'POST'])
def principal():
    if request.method == 'POST':
        start_time = time.time()  # Registrando o tempo no início do processamento
        file = {}
        file["projeto"] = request.files['file_p'] # Variação histórica entre valor da estimativa do projeto e do ETPE
        file["obra"] = request.files['file_o'] # Variação histórica entre valor da estimativa do projeto e da obra
        file["orc_disponivel"] = request.files['file_d'] # Variação histórica do orçamento
        file["mao_de_obra"] = request.files['file_mo'] # Variação histórica entre a expectativa de homem-hora que seria gasta por projeto versus a realmente gasta
        file["hh_disponivel"] = request.files['file_hd'] # Variação histórica da homem-hora disponível
        file["estimativa"] = request.files['file_estimativa'] # Lista de projetos da carteira a ser analisada com estimativas
        input = {}
        input["orc_disponivel"] = request.form['disponivel'] # Expectativa de orçamento
        input["hh_disponivel"] = request.form['hh_disponivel'] # Expectativa de homem-hora disponível
        input["nrep"] = request.form['nrep'] # Definição do número de repetições
        limits = {}
        limits["min_crit_orc"] = request.form['min_crit_orc'] # Definição do limite inferior do intervalo de confiança
        limits["max_crit_orc"] = request.form['max_crit_orc'] # Definição do limite superior do intervalo de confiança
        limits["min_crit_hh"] = request.form['min_crit_hh'] # Definição do limite inferior do intervalo de confiança
        limits["max_crit_hh"] = request.form['max_crit_hh'] # Definição do limite superior do intervalo de confiança

        # Convertendo disponivel, nrep, min_crit e max_crit para float e integer
        try:
            input["orc_disponivel"] = float(clean_numeric(input["orc_disponivel"]))
        except ValueError:
            return '<p>Erro: Expectativa de crédito deve ser um número.</p>'
        
        try:
            input["hh_disponivel"] = int(re.sub(r'[^\d]', '', input["hh_disponivel"]))
        except ValueError:
            return '<p>Erro: Expectativa de homem-hora (mão-de-obra) deve ser um número inteiro.</p>'
        
        try:
            input["nrep"] = int(re.sub(r'[^\d]', '', input["nrep"]))
        except ValueError:
            return '<p>Erro: Número de reptições deve ser um número inteiro.</p>'
                
        for key, value in limits.items():
            try:
                limits[key] = float(clean_numeric(value))
                limits[key] = limits[key]/100
            except ValueError:
                return '<p>Erro: Limite inferior ou superior do intervalo de confiança deve ser um número.</p>'

        # Salvando os arquivos em um dicionário
        filename = {}
        for key, value in file.items():
            filename[key] = secure_filename(value.filename)
            value.save(filename[key])


        # Carregando os dados do Excel
        df ={}

        for key, value in filename.items():
            df[key] = pd.read_excel(value).dropna()
        
        # Cria o dataframe com as faixas e as probabilidades
        df_grouped = {}

        for key, value in df.items():
            if 'VARIAÇÃO' in value.columns:
                df_grouped[key] = freedman(value)
                df_grouped[key] = calculate_probabilities(value, df_grouped[key])
                df_grouped[key] = calculate_counts(value, df_grouped[key])

        # Criando os histogramas e convertendo para base64        
        hist_p = create_histogram(df["projeto"]['VARIAÇÃO']*100, 'Histograma: Variação histórica entre estimativa preliminar de custo e valor do projeto')
        hist_o = create_histogram(df["obra"]['VARIAÇÃO']*100, 'Histograma: Variação histórica entre o valor da obra e do projeto')
        hist_d = create_histogram(df["orc_disponivel"]['VARIAÇÃO']*100, 'Histograma: Variação histórica de orçamento disponível')
        hist_mo = create_histogram(df["mao_de_obra"]['VARIAÇÃO']*100, 'Histograma: Variação histórica entre os recursos humanos previstos e os realmente gastos')
        hist_hd = create_histogram(df["hh_disponivel"]['VARIAÇÃO']*100, 'Histograma: Variação histórica dos recursos humanos disponíveis')

        # Removendo os arquivos .xlsx do servidor
        
        for key, value in filename.items():
            os.remove(value)


        # Criando as listas a partir dos dataframes
        
        faixas = {}
        probs = {}

        for key, value in df_grouped.items():
            faixas[key] = df_grouped[key]['VARIAÇÃO'].tolist()
            probs[key] = df_grouped[key]['probability'].tolist()

        # Calcula o número de projetos na carteira
        n = len(df['estimativa']['ID-PW'].unique())
        
        df_in_crit = {}
        df_in_crit["orc"] = pd.DataFrame(columns=['ID-PW', 'In Crit Orc'])
        df_in_crit["hh"] = pd.DataFrame(columns=['ID-PW', 'In Crit HH'])

        frames = {}
        frames["orc"] = pd.DataFrame()
        frames["hh"] = pd.DataFrame()
                
        #---------------------------MC ORÇAMENTO--------------------------------#

        # Loop para ver qual carteira é a de menor risco orçamentário
        for i in range (1, len(df['estimativa']) + 1):
            estimativa = df["estimativa"]['VALOR ESTIMATIVA (R$)'].tolist()[:i]
            n = len(estimativa)
            in_crit, frame = montecarlo_orc(estimativa, faixas, probs, n, input["orc_disponivel"], input["nrep"], limits['min_crit_orc'], limits['max_crit_orc']) # Calcula o in_crit e o frame rodando a simulação de Monte-Carlo
            id_pw = df['estimativa'].loc[i - 1, 'ID-PW']
            newline = pd.DataFrame({'ID-PW': id_pw, 'In Crit Orc': in_crit},index=[len(df_in_crit['orc'])])
            df_in_crit['orc'] = pd.concat([df_in_crit['orc'],newline])
            print(f'{id_pw}: {in_crit}')
            frames['orc'][f'Carteira {i}'] = frame.flatten()

        frames['orc'].insert(0, 'Cenário', range(1, len(frames['orc']) + 1))
        output_file = os.path.join('outputs/output_orc.csv')
        frames['orc'].to_csv(output_file, index=False)
        
        # Encontrando o maior in_crit e os IDs associados
        i_max_crit = df_in_crit['orc']['In Crit Orc'].idxmax()
        ids_associados_orc = df_in_crit['orc'].loc[i_max_crit,'ID-PW']
        max_in_crit_orc = df_in_crit['orc'].loc[i_max_crit,'In Crit Orc']
        prioridade_associada_orc = df['estimativa'].loc[df['estimativa']['ID-PW']==ids_associados_orc]['PRIORIDADE'].values[0]
        
        # Exibição dos valores
        print(df_in_crit['orc'])

        # Cria o gráfico de dispersão        
        title = "Monte Carlo Orçamento - Dispersão dos Projetos"
        scatter_base64_orc = create_scatter(range(1, len(df_in_crit['orc']) + 1), df_in_crit['orc']['In Crit Orc'], title, n, highlight_index=prioridade_associada_orc)

        df_estimativa_resume_orc=df['estimativa'][['PRIORIDADE','ID-PW']]
        df_estimativa_resume_orc['ID'] = df_estimativa_resume_orc.apply(custom_formatter_id, axis=1, prioridade_associada=prioridade_associada_orc)
        df_estimativa_resume_orc['PRIORIDADE'] = df_estimativa_resume_orc['PRIORIDADE'].apply(custom_formatter_prior, prioridade_associada=prioridade_associada_orc)
        
        # Converter a tabela para HTML
        df_estimativa_resume_orc = df_estimativa_resume_orc[['PRIORIDADE','ID']].to_html(index=False, classes='table table-striped', escape=False)
        
        #---------------------------MC HOMEM-HORA--------------------------------#

        # Loop para ver qual carteira é a de menor risco de homem-hora
        for i in range (1, len(df['estimativa']) + 1):
            estimativa_hh = df['estimativa']['ESTIMATIVA H/H DU'].tolist()[:i]
            n = len(estimativa_hh)
            in_crit_hh, frame_hh = montecarlo_hh(estimativa_hh,
                                       faixas, probs, n, input["hh_disponivel"], input["nrep"], limits['min_crit_hh'], limits['max_crit_hh']) # Calcula o in_crit e o frame rodando a simulação de Monte-Carlo
            id_pw = df['estimativa'].loc[i - 1, 'ID-PW']
            newline = pd.DataFrame({'ID-PW': id_pw, 'In Crit HH': in_crit_hh},index=[len(df_in_crit['hh'])])
            df_in_crit['hh'] = pd.concat([df_in_crit['hh'],newline])
            frames['hh'][f'Carteira {i}'] = frame_hh.flatten()
        
        frames['hh'].insert(0, 'Cenário', range(1, len(frames['hh']) + 1))
        output_file = os.path.join('outputs/output_hh.csv')
        frames['hh'].to_csv(output_file, index=False)

        # Encontrando o maior in_crit e os IDs associados
        i_max_crit = df_in_crit['hh']['In Crit HH'].idxmax()
        ids_associados_hh = df_in_crit['hh'].loc[i_max_crit,'ID-PW']
        max_in_crit_hh = df_in_crit['hh'].loc[i_max_crit,'In Crit HH']
        prioridade_associada_hh = df['estimativa'].loc[df['estimativa']['ID-PW']==ids_associados_hh]['PRIORIDADE'].values[0]
                
        # Exibição dos valores
        print(df_in_crit['hh'])

        # Cria o gráfico de dispersão    
        title = "Monte Carlo Mão-de-obra - Dispersão dos Projetos"
        scatter_base64_hh = create_scatter(range(1, len(df_in_crit['hh']) + 1), df_in_crit['hh']['In Crit HH'], title, n, highlight_index=prioridade_associada_hh)
        
        df_estimativa_resume_hh=df['estimativa'][['PRIORIDADE','ID-PW']]
        df_estimativa_resume_hh['ID'] = df_estimativa_resume_hh.apply(custom_formatter_id, axis=1, prioridade_associada=prioridade_associada_hh)
        df_estimativa_resume_hh['PRIORIDADE'] = df_estimativa_resume_hh['PRIORIDADE'].apply(custom_formatter_prior, prioridade_associada=prioridade_associada_hh)
        
        # Converter a tabela para HTML
        df_estimativa_resume_hh = df_estimativa_resume_hh[['PRIORIDADE','ID']].to_html(index=False, classes='table table-striped', escape=False)

        
        #------------------------------MC GLOBAL-----------------------------#
        # Cria um data-frame com todos os in_crits
        df_in_crit = pd.merge(df_in_crit['orc'], df_in_crit['hh'], on='ID-PW')

        
        df_in_crit['In Crit'] = df_in_crit['In Crit Orc']*df_in_crit['In Crit HH']

        print(df_in_crit)

        i_max_crit = df_in_crit['In Crit'].idxmax()
        ids_associados = df_in_crit.loc[i_max_crit,'ID-PW']
        max_in_crit = df_in_crit.loc[i_max_crit,'In Crit']
        prioridade_associada = df['estimativa'].loc[df['estimativa']['ID-PW']==ids_associados]['PRIORIDADE'].values[0]
        
        # Cria o gráfico de dispersão global    
        title = "Monte Carlo Global - Dispersão dos Projetos"
        scatter_base64 = create_scatter(range(1, len(df_in_crit) + 1), df_in_crit['In Crit'], title, n, highlight_index=prioridade_associada)

        df_estimativa_resume=df['estimativa'][['PRIORIDADE','ID-PW']]
        df_estimativa_resume['ID'] = df_estimativa_resume.apply(custom_formatter_id, axis=1, prioridade_associada=prioridade_associada)
        df_estimativa_resume['PRIORIDADE'] = df_estimativa_resume['PRIORIDADE'].apply(custom_formatter_prior, prioridade_associada=prioridade_associada)
        
        # Converter a tabela para HTML
        df_estimativa_resume = df_estimativa_resume[['PRIORIDADE','ID']].to_html(index=False, classes='table table-striped', escape=False)
        
        #-----------------------------------------------------------------------#
        
        # Criar gráfico com intervalos de confiança e destacando as soluções cuja hipóetese nula do teste-Z não foi rejeitada
        z=1.96 # Valor crítico para 95% de confiança
        caminho_grafico = teste_z(z,limits["min_crit_orc"],limits['max_crit_orc'],limits['min_crit_hh'],limits['max_crit_hh'])
        
        
        elapsed_time = time.time() - start_time  # Calculando o tempo decorrido
        print(f'Tempo decorrido: {elapsed_time}')

        return render_template('resultados.html',
                               elapsed_time=round(elapsed_time,0),
                               hist_p=hist_p,
                               hist_o=hist_o,
                               hist_d=hist_d,
                               hist_mo=hist_mo,
                               hist_hd=hist_hd,
                               df_estimativa=df['estimativa'].to_html(index=False, classes='table table-striped'),
                               disponivel=input['orc_disponivel'],
                               max_in_crit = round(max_in_crit*100,2),
                               ids_associados = ids_associados,
                               scatter_base64=scatter_base64,
                               df_estimativa_resume=df_estimativa_resume,
                               max_in_crit_orc=round(max_in_crit_orc*100,2),
                               ids_associados_orc=ids_associados_orc,
                               scatter_base64_orc=scatter_base64_orc,
                               df_estimativa_resume_orc=df_estimativa_resume_orc,
                               hh_disponivel=input['hh_disponivel'],
                               max_in_crit_hh=round(max_in_crit_hh*100,2),
                               ids_associados_hh=ids_associados_hh,
                               scatter_base64_hh=scatter_base64_hh,
                               df_estimativa_resume_hh=df_estimativa_resume_hh,
                               min_crit_orc=limits['min_crit_orc'],
                               max_crit_orc=limits['max_crit_orc'],
                               min_crit_hh=limits['min_crit_hh'],
                               max_crit_hh=limits['max_crit_hh'],
                               z=z,
                               caminho_grafico=caminho_grafico)
        

    return render_template('index.html')

@app.route('/modelos', methods=['GET'])
def modelos():
    description = ['Histórico da variação entre a estimatva preliminar e o valor do projeto',
                   'Histórico da variação entre o valor do projeto e o valor da obra',
                   'Histórico da variação do orçamento disponível',
                   'Histórico da variação entre os recursos humanos previstos e os realmente gastos',
                   'Histórico da variação dos recursos humanos',
                   'Lista de projetos a ser analisada']
    try:
        files = os.listdir(MODELS_FOLDER)
        files = [f for f in files if os.path.isfile(os.path.join(MODELS_FOLDER, f))]
    except Exception as e:
        files = []
    return render_template('modelos.html', files=files, description=description)

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_from_directory(MODELS_FOLDER, filename, as_attachment=True)
    except FileNotFoundError:
        abort(404)

if __name__ == '__main__':
    app.run(debug=True)
