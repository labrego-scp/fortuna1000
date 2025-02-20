from flask import Flask, request, render_template, send_from_directory, abort
import pandas as pd
import re
import os
from werkzeug.utils import secure_filename
from binning import freedman, calculate_probabilities, calculate_counts
from montecarlo import montecarlo, montecarlo_hh
from helpers import create_histogram, create_scatter, clean_numeric, custom_formatter_id, custom_formatter_prior
import time
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import base64
import io

app = Flask(__name__)

MODELS_FOLDER = 'models'

@app.route('/', methods=['GET', 'POST'])
def principal():
    if request.method == 'POST':
        start_time = time.time()  # Registrando o tempo no início do processamento
        file_p = request.files['file_p'] # Variação histórica entre valor da estimativa do projeto e do ETPE
        file_o = request.files['file_o'] # Variação histórica entre valor da estimativa do projeto e da obra
        file_d = request.files['file_d'] # Variação histórica do orçamento
        file_mo = request.files['file_mo'] # Variação histórica entre a expectativa de homem-hora que seria gasta por projeto versus a realmente gasta
        file_hd = request.files['file_hd'] # Variação histórica da homem-hora disponível
        file_estimativa = request.files['file_estimativa'] # Lista de projetos da carteira a ser analisada com estimativas
        disponivel = request.form['disponivel'] # Expectativa de orçamento
        hh_disponivel = request.form['hh_disponivel'] # Expectativa de homem-hora disponível
        nrep = request.form['nrep'] # Definição do número de repetições
        #bins_hist = request.form['bins_hist'] # Definição do número de faixas do histograma de saída
        min_crit_orc = request.form['min_crit_orc'] # Definição do limite inferior do intervalo de confiança
        max_crit_orc = request.form['max_crit_orc'] # Definição do limite superior do intervalo de confiança
        min_crit_hh = request.form['min_crit_hh'] # Definição do limite inferior do intervalo de confiança
        max_crit_hh = request.form['max_crit_hh'] # Definição do limite superior do intervalo de confiança

        # Convertendo disponivel, nrep, min_crit e max_crit para float e integer
        try:
            disponivel = float(clean_numeric(disponivel))
        except ValueError:
            return '<p>Erro: Expectativa de crédito deve ser um número.</p>'
        
        try:
            hh_disponivel = int(re.sub(r'[^\d]', '', hh_disponivel))
        except ValueError:
            return '<p>Erro: Expectativa de homem-hora (mão-de-obra) deve ser um número inteiro.</p>'
        
        try:
            nrep = int(re.sub(r'[^\d]', '', nrep))
        except ValueError:
            return '<p>Erro: Número de reptições deve ser um número inteiro.</p>'
        
        '''try:
            bins_hist = int(re.sub(r'[^\d]', '', bins_hist))
        except ValueError:
            return '<p>Erro: Número de faixas do histograma de saída deve ser um número inteiro.</p>'''
        
        try:
            min_crit_orc = float(clean_numeric(min_crit_orc))
            min_crit_orc = min_crit_orc/100
        except ValueError:
            return '<p>Erro: Limite inferior do intervalo de confiança deve ser um número.</p>'
        
        try:
            max_crit_orc = float(clean_numeric(max_crit_orc))
            max_crit_orc = max_crit_orc/100
        except ValueError:
            return '<p>Erro: Limite superior do intervalo de confiança deve ser um número.</p>'
        
        try:
            min_crit_hh = float(clean_numeric(min_crit_hh))
            min_crit_hh = min_crit_hh/100
        except ValueError:
            return '<p>Erro: Limite inferior do intervalo de confiança deve ser um número.</p>'
        
        try:
            max_crit_hh = float(clean_numeric(max_crit_hh))
            max_crit_hh = max_crit_hh/100
        except ValueError:
            return '<p>Erro: Limite superior do intervalo de confiança deve ser um número.</p>'
        
        filename_p = secure_filename(file_p.filename)
        filename_o = secure_filename(file_o.filename)
        filename_d = secure_filename(file_d.filename)
        filename_mo = secure_filename(file_mo.filename)
        filename_hd = secure_filename(file_hd.filename)
        filename_estimativa = secure_filename(file_estimativa.filename)
        file_p.save(filename_p)
        file_o.save(filename_o)
        file_d.save(filename_d)
        file_mo.save(filename_mo)
        file_hd.save(filename_hd)
        file_estimativa.save(filename_estimativa)

        # Carregando os dados do Excel
        df_p = pd.read_excel(filename_p).dropna() # Dataframe da fariação histórica entre valor da estimativa do projeto e do ETPE
        df_o = pd.read_excel(filename_o).dropna() # Dataframe da variação histórica entre valor da estimativa do projeto e da obra
        df_d = pd.read_excel(filename_d).dropna() # Dataframe da variação histórica do orçamento
        df_mo = pd.read_excel(filename_mo).dropna() # Dataframe da variação histórica entre homem-hora estimado e o realmente gasto por projeto
        df_hd = pd.read_excel(filename_hd).dropna() # Dataframe da variação histórica da qtde de homem-hora disponível
        df_estimativa = pd.read_excel(filename_estimativa).dropna() # Dataframe da lista de projetos da carteira a ser analisada com estimativas

        # Cria o dataframe com as faixas e as probabilidades
        df_grouped_p = freedman(df_p)
        df_grouped_p = calculate_probabilities(df_p, df_grouped_p)
        df_grouped_p = calculate_counts(df_p, df_grouped_p)

        df_grouped_o = freedman(df_o)
        df_grouped_o = calculate_probabilities(df_o, df_grouped_o)
        df_grouped_o = calculate_counts(df_o, df_grouped_o)

        df_grouped_d = freedman(df_d)
        df_grouped_d = calculate_probabilities(df_d, df_grouped_d)
        df_grouped_d = calculate_counts(df_d, df_grouped_d)

        df_grouped_mo = freedman(df_mo)
        df_grouped_mo = calculate_probabilities(df_mo, df_grouped_mo)
        df_grouped_mo = calculate_counts(df_mo, df_grouped_mo)

        df_grouped_hd = freedman(df_hd)
        df_grouped_hd = calculate_probabilities(df_hd, df_grouped_hd)
        df_grouped_hd = calculate_counts(df_hd, df_grouped_hd)

        # Criando os histogramas e convertendo para base64
        hist_p = create_histogram(df_p['VARIAÇÃO']*100, 'Histograma: Variação histórica entre estimativa preliminar de custo e valor do projeto')
        hist_o = create_histogram(df_o['VARIAÇÃO']*100, 'Histograma: Variação histórica entre o valor da obra e do projeto')
        hist_d = create_histogram(df_d['VARIAÇÃO']*100, 'Histograma: Variação histórica de orçamento disponível')
        hist_mo = create_histogram(df_mo['VARIAÇÃO']*100, 'Histograma: Variação histórica entre os recursos humanos previstos e os realmente gastos')
        hist_hd = create_histogram(df_hd['VARIAÇÃO']*100, 'Histograma: Variação histórica dos recursos humanos disponíveis')

        # Removendo os arquivos .xlsx do servidor
        os.remove(filename_p)
        os.remove(filename_o)
        os.remove(filename_d)
        os.remove(filename_mo)
        os.remove(filename_hd)
        os.remove(filename_estimativa)

        # Criando as listas a partir dos dataframes
        #estimativa = df_estimativa['VALOR ESTIMATIVA (R$)'].tolist()
        faixas_p = df_grouped_p['VARIAÇÃO'].tolist()
        probs_p = df_grouped_p['probability'].tolist()
        faixas_o = df_grouped_o['VARIAÇÃO'].tolist()
        probs_o = df_grouped_o['probability'].tolist()
        faixas_d = df_grouped_d['VARIAÇÃO'].tolist()
        probs_d = df_grouped_d['probability'].tolist()
        faixas_mo = df_grouped_mo['VARIAÇÃO'].tolist()
        probs_mo = df_grouped_mo['probability'].tolist()
        faixas_hd = df_grouped_hd['VARIAÇÃO'].tolist()
        probs_hd = df_grouped_hd['probability'].tolist()

        # Calcula o número de projetos na carteira
        n = len(df_estimativa)
        df_in_crit_orc = pd.DataFrame(columns=['ID-PW', 'In Crit Orc'])
        df_in_crit_hh = pd.DataFrame(columns=['ID-PW', 'In Crit HH'])
        frames_orc = pd.DataFrame()
        frames_hh = pd.DataFrame()
                
        #---------------------------MC ORÇAMENTO--------------------------------#

        # Loop para ver qual carteira é a de menor risco orçamentário
        for i in range (1, len(df_estimativa) + 1):
            estimativa = df_estimativa['VALOR ESTIMATIVA (R$)'].tolist()[:i]
            n = len(estimativa)
            in_crit, frame = montecarlo(estimativa, faixas_p, probs_p, faixas_o, probs_o, faixas_d, probs_d, n, disponivel, nrep, min_crit_orc, max_crit_orc)
            id_pw = df_estimativa.loc[i - 1, 'ID-PW']
            newline = pd.DataFrame({'ID-PW': id_pw, 'In Crit Orc': in_crit},index=[len(df_in_crit_orc)])
            df_in_crit_orc = pd.concat([df_in_crit_orc,newline])
            print(f'{id_pw}: {in_crit}')
            #print(frame)
            frames_orc[f'Carteira {i}'] = frame.flatten()

        frames_orc.insert(0, 'Cenário', range(1, len(frames_orc) + 1))
        output_file = os.path.join('outputs/output_orc.csv')
        frames_orc.to_csv(output_file, index=False)
        
        # Encontrando o maior in_crit e os IDs associados
        i_max_crit = df_in_crit_orc['In Crit Orc'].idxmax()
        ids_associados_orc = df_in_crit_orc.loc[i_max_crit,'ID-PW']
        max_in_crit_orc = df_in_crit_orc.loc[i_max_crit,'In Crit Orc']
        prioridade_associada_orc = df_estimativa.loc[df_estimativa['ID-PW']==ids_associados_orc]['PRIORIDADE'].values[0]
        
        # Exibição dos valores
        print(df_in_crit_orc)

        # Cria o gráfico de dispersão        
        title = "Monte Carlo Orçamento - Dispersão dos Projetos"
        scatter_base64_orc = create_scatter(range(1, len(df_in_crit_orc) + 1), df_in_crit_orc['In Crit Orc'], title, n, highlight_index=prioridade_associada_orc)

        df_estimativa_resume_orc=df_estimativa[['PRIORIDADE','ID-PW']]
        df_estimativa_resume_orc['ID'] = df_estimativa_resume_orc.apply(custom_formatter_id, axis=1, prioridade_associada=prioridade_associada_orc)
        df_estimativa_resume_orc['PRIORIDADE'] = df_estimativa_resume_orc['PRIORIDADE'].apply(custom_formatter_prior, prioridade_associada=prioridade_associada_orc)
        
        # Converter a tabela para HTML
        df_estimativa_resume_orc = df_estimativa_resume_orc[['PRIORIDADE','ID']].to_html(index=False, classes='table table-striped', escape=False)
        
        #---------------------------MC HOMEM-HORA--------------------------------#

        # Loop para ver qual carteira é a de menor risco de homem-hora
        for i in range (1, len(df_estimativa) + 1):
            estimativa_hh = df_estimativa['ESTIMATIVA H/H DU'].tolist()[:i]
            n = len(estimativa_hh)
            in_crit_hh, frame_hh = montecarlo_hh(estimativa_hh,
                                       faixas_mo, probs_mo,
                                       faixas_hd, probs_hd,
                                       n, hh_disponivel, nrep,
                                       min_crit_hh, max_crit_hh)
            id_pw = df_estimativa.loc[i - 1, 'ID-PW']
            newline = pd.DataFrame({'ID-PW': id_pw, 'In Crit HH': in_crit_hh},index=[len(df_in_crit_hh)])
            df_in_crit_hh = pd.concat([df_in_crit_hh,newline])
            frames_hh[f'Carteira {i}'] = frame_hh.flatten()
        
        frames_hh.insert(0, 'Cenário', range(1, len(frames_hh) + 1))
        output_file = os.path.join('outputs/output_hh.csv')
        frames_hh.to_csv(output_file, index=False)

        # Encontrando o maior in_crit e os IDs associados
        i_max_crit = df_in_crit_hh['In Crit HH'].idxmax()
        ids_associados_hh = df_in_crit_hh.loc[i_max_crit,'ID-PW']
        max_in_crit_hh = df_in_crit_hh.loc[i_max_crit,'In Crit HH']
        prioridade_associada_hh = df_estimativa.loc[df_estimativa['ID-PW']==ids_associados_hh]['PRIORIDADE'].values[0]
                
        # Exibição dos valores
        print(df_in_crit_hh)

        # Cria o gráfico de dispersão    
        title = "Monte Carlo Mão-de-obra - Dispersão dos Projetos"
        scatter_base64_hh = create_scatter(range(1, len(df_in_crit_hh) + 1), df_in_crit_hh['In Crit HH'], title, n, highlight_index=prioridade_associada_hh)
        #scatter_base64_hh = create_scatter(df_in_crit_hh['ID-PW'], df_in_crit_hh['In Crit HH'], title, n)

        df_estimativa_resume_hh=df_estimativa[['PRIORIDADE','ID-PW']]
        df_estimativa_resume_hh['ID'] = df_estimativa_resume_hh.apply(custom_formatter_id, axis=1, prioridade_associada=prioridade_associada_hh)
        df_estimativa_resume_hh['PRIORIDADE'] = df_estimativa_resume_hh['PRIORIDADE'].apply(custom_formatter_prior, prioridade_associada=prioridade_associada_hh)
        
        # Converter a tabela para HTML
        df_estimativa_resume_hh = df_estimativa_resume_hh[['PRIORIDADE','ID']].to_html(index=False, classes='table table-striped', escape=False)

        # Exibição dos valores
        # print('Saída orçamento')
        # for id_pw, in_crit in in_crit_list.items():
        #     print(f'ID-PW: {id_pw}, In Crit: {in_crit}')
        # print('Saída homem-hora')
        # for id_pw_hh, in_crit_hh in in_crit_list_hh.items():
        #     print(f'ID-PW: {id_pw_hh}, In Crit: {in_crit_hh}')


        #------------------------------MC GLOBAL-----------------------------#
        # Cria um data-frame com todos os in_crits
        df_in_crit = pd.merge(df_in_crit_orc, df_in_crit_hh, on='ID-PW')

        
        df_in_crit['In Crit'] = df_in_crit['In Crit Orc']*df_in_crit['In Crit HH']

        print(df_in_crit)

        i_max_crit = df_in_crit['In Crit'].idxmax()
        ids_associados = df_in_crit.loc[i_max_crit,'ID-PW']
        max_in_crit = df_in_crit.loc[i_max_crit,'In Crit']
        prioridade_associada = df_estimativa.loc[df_estimativa['ID-PW']==ids_associados]['PRIORIDADE'].values[0]
        
        # Cria o gráfico de dispersão global    
        title = "Monte Carlo Global - Dispersão dos Projetos"
        scatter_base64 = create_scatter(range(1, len(df_in_crit) + 1), df_in_crit['In Crit'], title, n, highlight_index=prioridade_associada)

        df_estimativa_resume=df_estimativa[['PRIORIDADE','ID-PW']]
        #df_estimativa_resume['formatted'] = df_estimativa_resume.apply(custom_formatter, axis=1, prioridade_associada=prioridade_associada)
        #df_estimativa_resume['PRIORITY'] = df_estimativa_resume.apply(custom_formatter_prior, axis=1, prioridade_associada=prioridade_associada)
        #df_estimativa_resume['ID'] = df_estimativa_resume['ID-PW'].apply(custom_formatter_id, prioridade_associada=prioridade_associada)
        df_estimativa_resume['ID'] = df_estimativa_resume.apply(custom_formatter_id, axis=1, prioridade_associada=prioridade_associada)
        df_estimativa_resume['PRIORIDADE'] = df_estimativa_resume['PRIORIDADE'].apply(custom_formatter_prior, prioridade_associada=prioridade_associada)
        
        # Converter a tabela para HTML
        df_estimativa_resume = df_estimativa_resume[['PRIORIDADE','ID']].to_html(index=False, classes='table table-striped', escape=False)
        #-----------------------------------------------------------------------#
        
        elapsed_time = time.time() - start_time  # Calculando o tempo decorrido
        print(f'Tempo decorrido: {elapsed_time}')

        return render_template('resultados.html',
                               elapsed_time=round(elapsed_time,0),
                               hist_p=hist_p,
                               hist_o=hist_o,
                               hist_d=hist_d,
                               hist_mo=hist_mo,
                               hist_hd=hist_hd,
                               df_estimativa=df_estimativa.to_html(index=False, classes='table table-striped'),
                               disponivel=disponivel,
                               max_in_crit = round(max_in_crit*100,2),
                               ids_associados = ids_associados,
                               scatter_base64=scatter_base64,
                               df_estimativa_resume=df_estimativa_resume,
                               max_in_crit_orc=round(max_in_crit_orc*100,2),
                               ids_associados_orc=ids_associados_orc,
                               scatter_base64_orc=scatter_base64_orc,
                               df_estimativa_resume_orc=df_estimativa_resume_orc,
                               hh_disponivel=hh_disponivel,
                               max_in_crit_hh=round(max_in_crit_hh*100,2),
                               ids_associados_hh=ids_associados_hh,
                               scatter_base64_hh=scatter_base64_hh,
                               df_estimativa_resume_hh=df_estimativa_resume_hh,
                               min_crit_orc=min_crit_orc,
                               max_crit_orc=max_crit_orc,
                               min_crit_hh=min_crit_hh,
                               max_crit_hh=max_crit_hh)
        

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
