from os import getlogin
user = getlogin()

def requisicao(type, surveyId, reportId, inicio, fim):
    import requests
    import pandas as pd
    import os
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    url = "https://smartpanel.lumisay.com/reactor-webapp/pt/lumi_say/pn/lumicompass/api/get_data"

    file_path = f'C:/Users/{user}/Numerator International/BKO - Documents/Report/Elegibilidade OOH/projeto_ooh/datalake/temp/base.csv'
    

    if type == 'rt':
        inicio = inicio + ' 00:00:00'
        fim = 'getdate()'
    else:
        inicio = inicio + ' 00:00:00'
        fim = fim + ' 23:59:59'
        
    data = {
        'user_name': 'luiz.farias@wp.numerator.com',
        'password': 'Alr1sha.Lopeti',
        'survey_id': surveyId,
        'report_id': reportId,
        'start_time': inicio,
        'end_time': '',
        'report_format': 'csv'
    }
    response = requests.post(url, data=data, verify=False)


    if response.status_code == 200:
       

        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            csvfile.write(response.text)

    dados = pd.read_csv(file_path)

    return dados, inicio

def report_info():
    import pandas as pd
    path = (f'C:/Users/{user}/Numerator International/BKO - Documents/Report/Elegibilidade OOH/projeto_ooh/datalake/report_info/')

    df = pd.read_csv(path + 'report_info.csv', sep = ';',encoding ='latin1')

    return df, path

def df_charge(type, inicio, fim):
    list_df = {}

    df,_ = report_info()
    for _, row in df.iterrows():
        
        df_temp, init = requisicao(type, row['surveyId'], row['reportId'], inicio , fim)
        nm_df = f'qmob_project{row['surveyId']}_report{row['reportId']}_{row['nmReport']}'
        df_temp['dmProject'] = row['surveyId']
        df_temp['reportId'] = row['reportId']
        df_temp['nmReport'] = row['nmReport']
        list_df[nm_df] = df_temp
        

    
    
    return list_df, init

def masterfile_data(csv_str):
    import pandas as pd
    _, path = report_info()


    dados_masterfile = pd.read_csv(csv_str, encoding='latin1', sep=';')
    dados_masterfile.CodBarra = dados_masterfile.CodBarra.astype(str)

    return dados_masterfile

def conjunto_principal(list_df,barcodes,reprocessing : bool, csv_path : str):
    """
    Função que amarra a requisição de dados e geração do conjunto principal master
    Chamadas de função: 2 (report_info e df_charge como subchamada, invoca a requisicao)
    """

    import pandas as pd
    if reprocessing == True:
        
        df_final = pd.read_csv(csv_path, sep=',', encoding='latin1')
        df_final.StartTime = pd.to_datetime(df_final.StartTime).dt.date
        print(f"dados pré - processados históricos do qmob de {df_final.StartTime.min()} ate {df_final.StartTime.max()} ")
        return df_final
        
    else:
        df_final = pd.concat([list_df['qmob_project39026_report67317_Report2'], 
                              list_df['qmob_project40150_report70591_Reporte2'], 
                              list_df['qmob_project41470_report76923_Report2_Inc'],
                              list_df['qmob_project41815_report78932_Report_cfdl']], 
                              ignore_index = True)
        
        '''df_final = pd.concat([
                              list_df['qmob_project41815_report104185_Report_cfdl']], 
                              ignore_index = True)'''
        master = df_final.merge(barcodes, left_on='pScanner', right_on='CodBarra', how='left')
        aux = master.loc[~(master["Entry Type"].isin(['paused','incomplete']))].copy()
        
        return aux

def transform(df):

    df = df.copy()
    import pandas as pd
    aux = {
        'Entry ID' : 'EntryID',
        'Entry Type' : 'EntryType',
        'Start time' : 'StartTime'
    }

    df.rename(columns=aux, inplace=True)

    # Retirar os usuários de teste
    df = df[~df['Username'].isin(['brhansel', '55000016'])]

    # Transformação
    df.loc[:, 'StartTime'] = pd.to_datetime(df.StartTime, format='%d.%m.%Y %H:%M:%S').dt.date
    df.loc[:, 'WeekNumber'] = 'Semana' + df['StartTime'].apply(lambda x: str(x.isocalendar()[1]))
    df.loc[:, 'ATO'] = None
    df.loc[:, 'DNC'] = None

    return df

def transform_w(df):

    df = df.copy()
    import pandas as pd
    aux = {
        'Entry ID' : 'EntryID',
        'Entry Type' : 'EntryType',
        'Start time' : 'StartTime'
    }

    df.rename(columns=aux, inplace=True)

    # Retirar os usuários de teste
    df = df[~df['Username'].isin(['brhansel', '55000016'])]

    # Transformação
    df.loc[:, 'StartTime'] = pd.to_datetime(df.StartTime, format='%d.%m.%Y %H:%M:%S').dt.date
    df.loc[:, 'WeekNumber'] = df['StartTime'].apply(lambda x: str(x.isocalendar()[1]))
    df.loc[:, 'ATO'] = None
    df.loc[:, 'DNC'] = None

    return df

def determina_ato_dnc(df):
  import pandas as pd

  # Identifica as colunas que começam com 'p'
  colunas_p = [col for col in df.columns if ((col != 'pScanner') and (col.startswith('p') or col.startswith('pCat')))]


  """# Itera sobre as colunas e verifica se estão preenchidas
  for coluna in colunas_p:
      # Verifica se a coluna não está vazia (contém pelo menos um valor não nulo)
      if df[coluna].notna().any():
          #print(f"A coluna '{coluna}' possui valores preenchidos.")
          # Exemplo: contando valores não nulos na coluna
          print(f"Número de valores não nulos em '{coluna}': {df[coluna].notna().sum()}")
      else:
          print(f"A coluna '{coluna}' não possui valores preenchidos.")"""


  # Identifica as colunas que começam com 'p'
  colunas_p = [col for col in df.columns if ((col != 'pScanner') and (col.startswith('p') or col.startswith('pCat')))]


  for index, row in df.iterrows():
      # Verifica se pelo menos uma das colunas 'p' na linha atual está preenchida

      if pd.notna(row['CodBarra']):
        df.loc[index, 'DNC'] = None
        df.loc[index, 'ATO'] = 2
      elif row['pMeioPedido'] == 'Não fiz compras na semana':
        df.loc[index, 'DNC'] = 1
        df.loc[index, 'ATO'] = None
      elif row[colunas_p].notna().any():
        df.loc[index, 'DNC'] = None
        df.loc[index, 'ATO'] = 2
      else:
        df.loc[index, 'DNC'] = None
        df.loc[index, 'ATO'] = None
  return df

def estruct_analise(df):
    df = df.copy()
    import pandas as pd
    # Crie uma nova coluna que represente o status (ATO, DNC ou None)
    # Priorize DNC sobre ATO se ambos existirem na mesma semana para o mesmo usuário
    def get_status(row):
        if pd.notna(row['DNC']):
            return '1'
        elif pd.notna(row['ATO']):
            return '2'
        else:
            return None

    df['Status'] = df.apply(get_status, axis=1)

    # Crie a crosstable
    crosstable = pd.pivot_table(df,
                                index='Username',
                                columns='WeekNumber',
                                values='Status',
                                aggfunc=lambda x: ', '.join(x.dropna()) if x.dropna().any() else None,
                                # fill_value='None' # Opcional: preencher valores ausentes com 'None'
                            ).reset_index()
    
    crosstable['Elegível'] = None
    crosstable['Desc'] = None
    crosstable['ProgressoIndividuo'] = 'Sem Registro'

    crosstable.columns.name = None
    
    return crosstable.reset_index(drop=True)

def propor_semana_limpeza(df):

  # Inicializa as novas colunas de proporção
  colunas_semana_df = [col for col in df.columns if col.startswith('Semana')]
  colunas_semana_df.sort() # Garante a ordem por semana

  for semana_col in colunas_semana_df:
      # Extrai o número da semana do nome da coluna (ex: 'Semana27' -> '27')
      numero_semana = semana_col.replace('Semana', '')
      df.loc[:, f'Sem{numero_semana}PropDNC'] = None
      df.loc[:, f'Sem{numero_semana}PropATO'] = None

  # Itera sobre as linhas do DataFrame df para calcular proporções e simplificar valores
  for index, row in df.iterrows():
      for semana_col in colunas_semana_df:
          status_semana = df.loc[index, semana_col] # Use .loc para acessar o valor

          if isinstance(status_semana, str):
              status_list = [s.strip() for s in status_semana.split(',') if s.strip()]

              if status_list:
                  count_1 = status_list.count('1')
                  count_2 = status_list.count('2')
                  total_count = len(status_list)

                  # Calcula as proporções em porcentagem
                  proportion_1 = (count_1 / total_count) * 100
                  proportion_2 = (count_2 / total_count) * 100

                  # Preenche as novas colunas de proporção usando .loc com o novo nome
                  numero_semana = semana_col.replace('Semana', '')
                  df.loc[index, f'Sem{numero_semana}PropDNC'] = f'{proportion_1:.2f}%'
                  df.loc[index, f'Sem{numero_semana}PropATO'] = f'{proportion_2:.2f}%'

                  # Aplica a lógica de limpeza e simplificação ao valor original usando .loc
                  if count_2 > 0:
                      df.loc[index, semana_col] = '2'
                  elif count_1 > 0 and count_2 == 0:
                      df.loc[index, semana_col] = '1'
                  # Células sem '1' ou '2' permanecem como estão (None ou o valor original se não for string)
              # Se status_list estiver vazia, as proporções permanecem None
          # Se status_semana for None, as proporções e o valor original permanecem None


  # Reordena as colunas para ter semana, proporção DNC, proporção ATO, etc.
  novas_colunas_ordenadas = ['Username']
  # Atualiza a lista de colunas ordenadas com os novos nomes de proporção
  for semana_col in colunas_semana_df:
      numero_semana = semana_col.replace('Semana', '')
      novas_colunas_ordenadas.append(semana_col)
      novas_colunas_ordenadas.append(f'Sem{numero_semana}PropDNC')
      novas_colunas_ordenadas.append(f'Sem{numero_semana}PropATO')

  # Inclui as colunas originais que não são semanas, Elegível ou desc
  outras_colunas_originais = [col for col in df.columns if col not in novas_colunas_ordenadas and col not in ['Username', 'Elegível', 'Desc'] and (not col.startswith('Sem') or ('PropDNC' not in col and 'PropATO' not in col))]
  novas_colunas_ordenadas.extend(outras_colunas_originais)
  novas_colunas_ordenadas.extend(['Elegível', 'Desc'])


  df = df.loc[:, novas_colunas_ordenadas]

def process_desc_index(df):
  import pandas as pd
  # Itera sobre as linhas do DataFrame df
  for index, row in df.iterrows():
      username = row['Username']
      # Identifica e ordena as colunas de semana
      colunas_semana = [col for col in df.columns if col.startswith('Semana')]
      colunas_semana.sort() # Garante a ordem por semana

      # Obtém os valores das colunas de semana para a linha atual
      week_values = row[colunas_semana].tolist()

      # Substitui nan por 0 e converte todos os valores para string
      processed_values = [str(int(x)) if pd.notna(x) and isinstance(x, (int, float)) else ('0' if pd.isna(x) else str(x)) for x in week_values]


      # Junta os valores processados em uma string separada por vírgulas
      desc_string = ','.join(processed_values)

      # Atribui a string resultante à coluna 'desc' da linha atual
      df.loc[index, 'Desc'] = desc_string

def determina_elegibilidade(df):
  
  # Itera sobre as linhas do DataFrame df para determinar a elegibilidade
  for index, row in df.iterrows():
      desc_values_str = row['Desc'] # Obtém a string da coluna 'desc'

      if isinstance(desc_values_str, str):
          # Divide a string em uma lista de valores, removendo espaços em branco
          desc_list = [s.strip() for s in desc_values_str.split(',') if s.strip()]

          # Conta as ocorrências de '1' e '2' na lista
          count_1 = desc_list.count('1')
          count_2 = desc_list.count('2')

          # Aplica as regras de elegibilidade
          if count_2 >= 2:
              df.loc[index, 'Elegível'] = True
          elif count_1 >= 3:
              df.loc[index, 'Elegível'] = True
          elif count_1 >= 2 and count_2 >= 1:
              df.loc[index, 'Elegível'] = True
          elif count_1 >= 1 and count_2 >= 2:
              df.loc[index, 'Elegível'] = True
          else:
              df.loc[index, 'Elegível'] = False

def determina_progresso_indiv(df):
  for index, row in df.iterrows():
      desc_values_str = row['Desc'] # Obtém a string da coluna 'desc'

      if isinstance(desc_values_str, str):
          # Divide a string em uma lista de valores, removendo espaços em branco
          desc_list = [s.strip() for s in desc_values_str.split(',') if s.strip()]

          # Conta as ocorrências de '1' e '2' na lista
          count_1 = desc_list.count('1')
          count_2 = desc_list.count('2')

          if count_2 >= 2 or count_1 >= 3:
              df.loc[index, 'ProgressoIndividuo'] = "já É um elegível"
          elif count_2 == 1 and count_1 == 2:
              df.loc[index, 'ProgressoIndividuo'] = "já É um elegível"
          elif count_2 == 1 and count_1 == 1:
              df.loc[index, 'ProgressoIndividuo'] = "Falta 1 ATO"
          elif count_1 == 0 and count_2 == 0:
              df.loc[index, 'ProgressoIndividuo'] = "Sem registro/Falta 3 DNC ou 2 ATO"
          elif count_2 == 1 and count_1 == 1:
              df.loc[index, 'ProgressoIndividuo'] = "Falta 1 ATO"
          elif count_2 == 1:
              df.loc[index, 'ProgressoIndividuo'] = "Falta 1 ATO"
          elif count_1 == 1:
              df.loc[index, 'ProgressoIndividuo'] = "1 DNC"
          elif count_1 == 2:
              df.loc[index, 'ProgressoIndividuo'] = "Falta 1 ATO"

def amostra_base(csv):
    import pandas as pd
    #_,path =report_info()

    dados_amostraviva = pd.read_excel(csv)

    dados_amostraviva.rename(columns={'Alias' : 'IndividuoOOH'}, inplace=True)

    '''dados_amostraviva.drop(columns={
        #'Elegibilidad',
        'Data Entrada',
        'Data Saida',
        'idDomicilio',
        'idIndividuo'

    }, inplace = True)'''

    return dados_amostraviva

def carrega_individuos(str):
    import pandas as pd
    #_,path =report_info()

    ext = str.lower().split('.')[-1]

    if ext == 'csv':
        indiv = pd.read_csv(str, sep=';', encoding='latin1')
    elif ext in ['xlsx', 'xls']:
        indiv = pd.read_excel(str, sheet_name='Planilha1')
    else:
        raise ValueError(f'Formato de arquivo não suportado: {ext}')
    
    indiv.rename(columns={'Alias' : 'IndividuoOOH'}, inplace=True)

    '''indiv.drop(columns=[
        'idPainel',
        'Semanas',
        'Semanas con actos',
        'Elegibilidad',
        'Actos'

    ], inplace = True)'''

    return indiv

def mortalidade_individuo(df_vivos, indiv):
    import pandas as pd
    df_vivos = pd.merge(df_vivos, indiv, on='IndividuoOOH', how='left')

    return df_vivos

def limpeza_final(aux):
    import pandas as pd

    df_vivos = aux.copy()

    df_vivos["dt_fim"] = pd.to_datetime(df_vivos["dt_fim"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
    df_vivos["dt_fim"] = df_vivos["dt_fim"].dt.date
    df_vivos["semana_num"] = df_vivos['dt_fim']

    df_vivos['semana_num'] = df_vivos['semana_num'].apply(lambda x: str(x.isocalendar()[1]))

    to_keep = [
        'IndividuoOOH',
        'dt_inicio',
        'idPainel',
        'dt_inicio',
        'dt_fim',
        'data_entrada',
        'Data Saida',
        'idDomicilio',
        'idIndividuo',
        'Username',
        'Elegível',
        'Desc',
        'Status',
        'ProgressoIndividuo',
        'semana_num'
    ]
    
    #df_vivos.ProgressoIndividuo.fillna("Sem Registro", inplace=True)

    df_vivos.fillna({'ProgressoIndividuo': 'Sem Registro'}, inplace=True)

    #df_vivos.loc[:, 'Status'] = ['Vivo' if not(pd.notna(x)) else 'Morto' for x in df_vivos['Data Saida']]

    to_drop = [col for col in df_vivos.columns if col not in to_keep]
    df_vivos.drop(columns=to_drop, inplace=True)

    print('\n limpeza final realizada')

    return df_vivos

def salvar_csv_sharepoint(dados):

    import pandas as pd
    from datetime import datetime

    init = pd.to_datetime(dados.StartTime.min()).date()

    
    path = f'C:/Users/{user}/Numerator International/BKO - Documents/Report/Elegibilidade OOH/projeto_ooh/datalake/actos_qmob/survey_{init}.csv'
    path_xlsb = f'C:/Users/{user}/Numerator International/BKO - Documents/Report/Elegibilidade OOH/projeto_ooh/datalake/actos_qmob/survey_{init}.xlsx'


    """
    Salva (sobrescreve) um DataFrame como CSV na pasta sincronizada do SharePoint.
    
    Parâmetros:
    - dados: pd.DataFrame -> o dataframe a ser salvo
    - pasta_sharepoint: str -> caminho da pasta local sincronizada com o SharePoint
    - nome_arquivo: str -> nome do arquivo CSV (default: 'atualizacao.csv')
    """
    dados.to_excel(path_xlsb, index=False)
    dados.to_csv(path, index=False, sep= ';',encoding="utf-8")
    print(f"[{datetime.now()}] Arquivo sobrescrito em: {path}")

def dados_finais(df_transformed, df_estruct, df_vivos, df_individuos,reprocessing :bool):
    import pandas as pd
    from datetime import datetime

    hora_atual = datetime.now().strftime("%H-%M-%S")

    df_vivos = df_vivos.merge(df_estruct, right_on='Username', left_on='IndividuoOOH', how='left')
    final = pd.to_datetime(df_transformed.StartTime.max()).date()
    inicio = pd.to_datetime(df_transformed.StartTime.min()).date()

    df_vivos['dt_inicio'] = inicio
    df_vivos['dt_fim'] = final

    sharepoint_path = f'C:/Users/{user}/Numerator International/BKO - Documents/Report/Elegibilidade OOH/projeto_ooh/datalake/historico_eelegibilidade'
    excel_filename = f'{sharepoint_path}/Elegibilidade_OOH_{inicio}_A_{final}.xlsx'

    if reprocessing == True:
        print("dados de qmob_master não foram alterados")
    else:
        salvar_csv_sharepoint(df_transformed)

    df_vivos = df_vivos.merge(df_individuos, on='IndividuoOOH', how='left')
    df_vivos = limpeza_final(df_vivos)

    origin_ids = pd.read_excel(f'C:/Users/{user}/Numerator International/BKO - Documents/Report/Elegibilidade OOH/projeto_ooh/datalake/egj_ids/1000_Preallocated_OOH_28112025.xlsx')

    df_vivos['origin_egj'] = 'Amostra Anterior'
    df_vivos.loc[
        df_vivos['IndividuoOOH'].isin(origin_ids['ALIAS']),
        'origin_egj'
    ] = 'Ana Rissia'

   
    
    group_1 = (
        df_vivos.
        groupby("dt_fim", as_index=False)
        .agg(
            Elegível=("Elegível", "sum")
        )
    )

    group_2 = (
        df_vivos.loc[df_vivos.origin_egj == 'Ana Rissia'].
        groupby("dt_fim", as_index=False)
        .agg(
            Elegível=("Elegível", "sum")
        )
    )    

    with pd.ExcelWriter(excel_filename) as writer:

        df_vivos.to_excel(writer, sheet_name='Amostra_Viva_Elegibilidade', index=False)
        df_estruct.to_excel(writer, sheet_name='Estruct',index = False), 
        df_individuos.to_excel(writer, sheet_name='individuos_detallhe',index = False)

    print(f"Arquivo Excel '{excel_filename}' criado com sucesso! Saldo na pasta sincronizada do SharePoint")

    return group_1, group_2

def reprocessing_month(str_master_qmob, str_amostra_correspondente, str_individuos_correspondente,str_barcodes, inicio, fim):
    import wp_ooh_atm_amostra_viva_ooh.functions as functions
    from datetime import datetime
    import pandas as pd
    masterfile = pd.read_csv(str_barcodes, sep = ';', encoding='latin1')
    master = functions.conjunto_principal(list_df = False,barcodes = masterfile,reprocessing=True, csv_path=str_master_qmob) # Requisição não está respeitando o filtro de data
    print('\n dados carregados \n')
    # A API não respeita os limites de data, então preciso fazer um filtro no pós-normalização
    master_transformed = master


    # Filtro de data
    inicio = datetime.strptime(inicio, '%Y-%m-%d')
    fim = datetime.strptime(fim, '%Y-%m-%d')

    master_transformed['StartTime'] = pd.to_datetime(
    master_transformed['StartTime'], errors='coerce', format='%Y-%m-%d %H:%M:%S'
)
    
    #master_transformed = master_transformed.loc[(master_transformed.StartTime >= init)]
    master_transformed = master_transformed.loc[(master_transformed.StartTime >= inicio) & (master_transformed.StartTime <=fim)]
    
    print(f'\n periodo da analise com base histórica filtrada de {inicio} a {fim} \n')

    # Principal Processamento
    master_transformed = functions.determina_ato_dnc(master_transformed)
    estruct_analise = functions.estruct_analise(master_transformed)

    print('\n determinação de atos concluída \n')


    # Carregamento dos dados de amostra viva
    amostra_viva = functions.amostra_base(str_amostra_correspondente)

    # pós-processamento
    functions.propor_semana_limpeza(estruct_analise)
    functions.propor_semana_limpeza(estruct_analise)
    functions.process_desc_index(estruct_analise)
    functions.determina_elegibilidade(estruct_analise)
    functions.determina_progresso_indiv(estruct_analise)

    print('\n pós processamento finalizadoS\n')

    individuos = functions.carrega_individuos(str_individuos_correspondente)
    print('\n obtenção da mortalidade')

    # Geração da basefinal
    functions.dados_finais(master_transformed,estruct_analise,amostra_viva, individuos,reprocessing=True)

#NOVAS REGRAS

def final_ams(df, dt_inicio, dt_fim):
    
    from openpyxl import load_workbook
    from openpyxl.styles import PatternFill
    from openpyxl.formatting.rule import FormulaRule
    from openpyxl.utils import get_column_letter
    from datetime import datetime
    import pandas as pd

   

    sharepoint_path = f'C:/Users/{user}/Numerator International/BKO - Documents/Report/Elegibilidade OOH/projeto_ooh/datalake/historico_eelegibilidade'
    excel_filename = f'{sharepoint_path}/Elegibilidade_NR_OOH_{dt_inicio}_A_{dt_fim}.xlsx'

    df['dt_fim'] = pd.to_datetime(df['dt_fim'])

    # Salva primeiro
    df.to_excel(excel_filename, index=False)

    # Abre o arquivo salvo
    wb = load_workbook(excel_filename)
    ws = wb.active

    # Define cores
    verde_claro = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    amarelo_claro = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")

    # Descobre colunas dinamicamente
    colunas = list(df.columns)

    for idx, col in enumerate(colunas, start=1):
        
        if col.startswith("ATO_W") or col.startswith("DNC_W"):
            
            col_letter = get_column_letter(idx)
            range_col = f"{col_letter}2:{col_letter}{ws.max_row}"

            # Fórmula: célula > 0
            formula = f"{col_letter}2>0"

            if col.startswith("ATO_W"):
                rule = FormulaRule(formula=[formula], fill=verde_claro)
            else:
                rule = FormulaRule(formula=[formula], fill=amarelo_claro)

            ws.conditional_formatting.add(range_col, rule)

    # Salva novamente
    wb.save(excel_filename)
    ws = wb.close()

    return df

def funil_1(master_transformed):
    import pandas as pd
    
    estruct_analise_v2 = master_transformed[['Username','ATO','DNC', 'WeekNumber']].copy()

    estruct_analise_v2['ATO'] = pd.to_numeric(
        estruct_analise_v2['ATO'],
        errors='coerce'
    )

    estruct_analise_v2['DNC'] = pd.to_numeric(
        estruct_analise_v2['DNC'],
        errors='coerce'
    )

    estruct_analise_v2['status_comp'] = (
        estruct_analise_v2['ATO']
        .fillna(estruct_analise_v2['DNC'])
        .fillna(0)
        .astype(int)
    )
    funil1 = (
        estruct_analise_v2
        .groupby(['Username','WeekNumber'])['status_comp']
        .value_counts()
        .unstack(fill_value=0)
        .reset_index()
        .rename(columns={
            0: 'Sem Registro',
            1: 'DNC',
            2: 'ATO'
        })
        
    )

    funil1.columns.name = None

    funil1 = funil1.loc[~(funil1.Username.isin(['brtest','brteste','brhansel','55000016']))]

    funil1['wAto'] = funil1['ATO'] > 0
    funil1['wAto>3'] = funil1['ATO'] >= 3

    # verifica se existe ATO na semana
    tem_ato_semana = funil1.groupby(['Username','WeekNumber'])['ATO'].transform(lambda x: (x > 0).any())

    # verifica se existe DNC na semana
    tem_dnc_semana = funil1.groupby(['Username','WeekNumber'])['DNC'].transform(lambda x: (x > 0).any())

    # Mutually Exclusive Event Aggregation
    funil1['wDnc'] = (funil1['DNC'] > 0) & ~(tem_ato_semana & tem_dnc_semana)

    return funil1

def funil_2(funil1):
    funil2 = (
        funil1
        .groupby(['Username'], as_index=False)
        .agg({
            'Sem Registro': 'sum',
            'DNC': 'sum',
            'ATO': 'sum',
            'wAto': 'sum',
            'wDnc': 'sum',
            'wAto>3': 'sum'
        })
    )

    import numpy as np 
    # Regra nova
    condicoes_nr = [
        (funil2['wAto'] >= 2),
        (funil2['wDnc'] >= 3),
        (funil2['wDnc'] >= 2) & (funil2['wAto'] >=1),
        (funil2['wDnc'] >= 1) & (funil2['wAto>3'] >=1) 

    ]

    valores_nr = [
        True, 
        True, 
        True,
        True
    ]

    desc_nr = [
        "ATO > 2 semanas", 
        'DNC > 3 semanas', 
        'DNC == 2 semanas & ATO == 1 semana',
        'DNC == 1 semana & ATO == 1 semana com +3 atos validos'
    ]

    # Regra anterior para comparação

    condicoes_ls = [
        (funil2['wAto'] >= 2),
        (funil2['wDnc'] >= 3),
        (funil2['wDnc'] >= 2) & (funil2['wAto'] >=1),

    ]
    
    desc_ls = [
        "ATO > 2 semanas", 
        'DNC > 3 semanas', 
        'DNC == 2 semanas & ATO == 1 semana'
    ]

    valores_ls = [
        True, 
        True, 
        True
    ]

    # Progresso indiv

    condicoes_Indiv = [
        (funil2['wAto'] == 2) | (funil2['wDnc'] >=3),
        (funil2['wAto'] == 1) & (funil2['wDnc'] == 2),
        (funil2['wAto>3'] == 1) & (funil2['wDnc'] == 1),
        (funil2['wDnc'] == 1) & (funil2['wAto'] == 1),
        (funil2['wDnc'] == 1),
        (funil2['wAto'] == 1),
        (funil2['wDnc'] == 2)


    ]
    
    desc_indiv = [
        "já É um elegível",
        "já É um elegível" ,
        'Falta 1 ATO', 
        'Falta 1 ATO',        
        '1 DNC',
        'Falta 1 ATO',
        'Falta 1 ATO',
    ]
    

    funil2['Elegivel_nr'] = np.select(condicoes_nr, valores_nr, default=False)
    funil2['Elegivel_nr_desc'] = np.select(condicoes_nr, desc_nr, default=" ")

    funil2['Elegivel_ls'] = np.select(condicoes_ls, valores_ls, default=False)
    funil2['Elegivel_ls_desc'] = np.select(condicoes_ls, desc_ls, default=False)

    funil2['Progresso_individuo'] = np.select(condicoes_Indiv, desc_indiv, default="Sem Registro")
    """funil2['Progresso_individuo'] = funil2['Progresso_individuo'].fillna('Sem_Registro')"""
    funil2.loc[funil2['Elegivel_nr'] == True, 'Progresso_individuo'] = 'já É um elegível'



    
    


    return funil2

def amostra_viva(str, estruct_analise_v2):

    individuos = carrega_individuos(str)
    bs_ind = individuos[['IndividuoOOH','Provedor',
                        'data_entrada', 'InterviewerCode', 
                        'Nome Entrev.', 'Região Kantar',
                        'Macro Região', 'sexo', 'Gacode']].copy()
    bs_ind.InterviewerCode = bs_ind.InterviewerCode.fillna(0).astype('int64')    


    amostra_viva = bs_ind.merge(
        estruct_analise_v2,
        left_on='IndividuoOOH',
        right_on='Username',
        how='left'
    )

    amostra_viva['Participacao'] = amostra_viva['Username'].notna()
    amostra_viva.drop(columns = 'Username', inplace = True)

    prefixos_validos = ('ATO_W', 'DNC_W')

    cols_semana = [c for c in amostra_viva.columns if c.startswith(prefixos_validos)]

    amostra_viva[cols_semana] = amostra_viva[cols_semana].fillna(0).astype('int64')

    return amostra_viva

# Nova Estrutura de dados por semana (Antigo Estruct Analise)
def estruct_analise_v2(funil1):
    import pandas as pd
    pv = (
        pd.pivot_table(
            funil1,
            index = ['Username'],
            columns= 'WeekNumber',
            values= ['ATO', 'DNC'],
            aggfunc= 'sum'
        )
        .reset_index()
    )
    # achata o MultiIndex
    pv.columns = [
        f"{col[0]}_W{col[1]}" if isinstance(col, tuple) else col
        for col in pv.columns
    ]

    pv.rename(columns={
        'Username_W':'Username'
                    }, inplace=True)
    
    return pv

def gerar_label_semanas_mes(df, coluna, nome_label):
    import pandas as pd
    bins = [-1, 0, 1, 2, 3, 4, 5]
    labels = [
        '0 semanas',
        '1 semana',
        '2 semanas',
        '3 semanas',
        '4 semanas',
        '5 semanas'
    ]

    df[nome_label] = pd.cut(df[coluna], bins=bins, labels=labels)

    return df


def gerar_label_faixa_atos(df, col_atos):
    import pandas as pd
    bins = [-1, 0, 1, 2, 3, 7, float('inf')]

    labels = [
        '0 ato',
        '1 ato',
        '2 atos',
        '3 atos',
        '4 - 7 atos',
        '8+ atos'
    ]
    df['faixa_atos'] = pd.cut(
        df[col_atos],
        bins=bins,
        labels=labels
    )

    return df, labels

def gerar_label_faixa_dnc(df, col_atos):
    import pandas as pd
    bins = [-1, 0, 1, 2, 3, 7, float('inf')]

    labels = [
        '0 dnc',
        '1 dnc',
        '2 dnc',
        '3 dnc',
        '4 - 7 dnc',
        '8+ dnc'
    ]

    df['faixa_dnc'] = pd.cut(
        df[col_atos],
        bins=bins,
        labels=labels
    )

    return df, labels
# Inclusão da Elegibilidade
def elegibles(funil2, amostra_viva, estruct_analise, dt_inicio, dt_fim):


    import pandas as pd
   
    bs_elg = funil2[['Username', 'DNC', 'ATO','wAto','wDnc','wAto>3','Elegivel_nr','Elegivel_nr_desc','Elegivel_ls','Progresso_individuo']].copy()
    bs_elg['total_registros'] = bs_elg['DNC'] + bs_elg['ATO']
    bs_elg = bs_elg[['Username', 'DNC', 'ATO','wAto','wDnc','wAto>3','total_registros','Elegivel_nr','Elegivel_nr_desc','Progresso_individuo']].copy()


    amostra_elegivel = amostra_viva.merge(
        bs_elg,
        left_on = 'IndividuoOOH',
        right_on = 'Username',
        how = 'left'

    )
    # trasformaçãofinal depois do ultimo merge
    amostra_elegivel.loc[amostra_elegivel['Progresso_individuo'].isna(), 'Progresso_individuo'] = 'Sem Registro'

    amostra_elegivel['dt_inicio'] = dt_inicio
    amostra_elegivel['dt_fim'] = dt_fim

    amostra_elegivel.DNC = amostra_elegivel.DNC.fillna(0).astype('int64')	
    amostra_elegivel.ATO = amostra_elegivel.ATO.fillna(0).astype('int64')
    amostra_elegivel.total_registros = amostra_elegivel.total_registros.fillna(0).astype('int64')

    
    origin_ids = pd.read_excel(f'C:/Users/{user}/Numerator International/BKO - Documents/Report/Elegibilidade OOH/projeto_ooh/datalake/egj_ids/1000_Preallocated_OOH_28112025.xlsx')

    amostra_viva['origin_egj'] = 'Amostra Anterior'
    amostra_viva.loc[
    amostra_viva['IndividuoOOH'].isin(origin_ids['ALIAS']),
    'origin_egj'
    ] = 'Ana Rissia'

    # Colunas que você quer trazer para o início
    cols_inicio = [
        'dt_inicio',
        'dt_fim',
        'IndividuoOOH', 
        'data_entrada', 
        'InterviewerCode', 
        'Nome Entrev.' 
        'Participacao', 
        'origin_egj'
    ]

    # Garante que só usa colunas que realmente existem no df
    cols_inicio = [c for c in cols_inicio if c in amostra_elegivel.columns]

    # Reordena: primeiro as escolhidas, depois o restante
    amostra_elegivel = amostra_elegivel[cols_inicio + [c for c in amostra_elegivel.columns if c not in cols_inicio]]
    amostra_elegivel.drop(columns = 'Participacao',inplace = True)

    # Adicionar chave de unicidade para garantir relacionamento 1:1 com a base de carteirização
    amostra_elegivel['index_id_gacode'] = (
        amostra_elegivel['Gacode'].fillna(0).astype(int).astype(str)
        + '-' +
        amostra_elegivel['Macro Região'].astype(str)
        + '-' +
        amostra_elegivel['Região Kantar'].astype(str)
        + '-' +
        amostra_elegivel['sexo'].astype(str)        

    )
    amostra_elegivel['wDnc'] = amostra_elegivel['wDnc'].fillna(0)
    amostra_elegivel['wAto'] = amostra_elegivel['wAto'].fillna(0)
    amostra_elegivel['ATO'] = amostra_elegivel['ATO'].fillna(0)
    amostra_elegivel['DNC'] = amostra_elegivel['DNC'].fillna(0)

    amostra_elegivel,labels = gerar_label_faixa_atos(amostra_elegivel, 'ATO')
    amostra_elegivel,labels = gerar_label_faixa_dnc(amostra_elegivel, 'DNC')

    



    amostra_elegivel = gerar_label_semanas_mes(amostra_elegivel, 'wDnc', 'faixa_partic_semanas_DNC')
    amostra_elegivel = gerar_label_semanas_mes(amostra_elegivel, 'wAto', 'faixa_partic_semanas_ATO')


    return amostra_elegivel


import os
import pandas as pd
from datetime import datetime


class Logger:

    data_hora = datetime.now()

    def __init__(self):

        os.makedirs('logs', exist_ok=True)

        self.log_file = datetime.now().strftime(
            f'C:/Users/{user}/Numerator International/BKO - Documents/Report/Elegibilidade OOH/projeto_ooh/datalake/logs/pipeline_%Y%m%d.csv'
        )


    def write(
        self,
        etapa,
        status='INFO',
        mensagem='',
        detalhes=''
    ):

        log = pd.DataFrame([{
            'datetime': datetime.now().strftime(
                '%Y-%m-%d %H:%M:%S'
            ),
            'etapa': etapa,
            'status': status,
            'mensagem': mensagem,
            'detalhes': detalhes
        }])
        # Mostra em tempo de execução
        print(
            f'[{self.data_hora}] [{status}] [{etapa}] {mensagem}'
        )

        if not os.path.exists(self.log_file):

            log.to_csv(
                self.log_file,
                index=False,
                sep=';'
            )

        else:

            log.to_csv(
                self.log_file,
                mode='a',
                header=False,
                index=False,
                sep=';'
            )


logger = Logger()

def disparar_email_vs(
    path,
    destinatarios,
    subject,
    data_ref,
):

    import win32com.client as win32

    from datetime import datetime

    data_atual = data_ref

    outlook = win32.Dispatch(
        'outlook.application'
    )

    mail = outlook.CreateItem(0)

    mail.To = destinatarios

    mail.CC = (
        'fabio.shiraishi@wp.numerator.com; '
        f'{user}@wp.numerator.com'
    )

    mail.Subject = (
        f'{subject} | {data_ref}'
    )

    mail.Body = (
        'Segue em anexo.'
    )

    mail.Attachments.Add(path)

    mail.Send()

    print(
        f'arquivo: {path}\n'
        f'disparado para: {destinatarios}'
    )


def pegar_arquivo_mais_recente(pasta, extensao=None):
    import os

    """
    Retorna o caminho do arquivo mais recente dentro da pasta.
    
    :param pasta: caminho da pasta
    :param extensao: opcional (ex: '.csv', '.xlsx')
    :return: caminho completo do arquivo mais recente
    """
    
    arquivos = [
        os.path.join(pasta, f)
        for f in os.listdir(pasta)
        if os.path.isfile(os.path.join(pasta, f))
    ]
    
    # Filtrar por extensão (se informado)
    if extensao:
        arquivos = [f for f in arquivos if f.lower().endswith(extensao.lower())]
    
    if not arquivos:
        return None

    arquivo_mais_recente = max(arquivos, key=os.path.getctime)
    
    return arquivo_mais_recente