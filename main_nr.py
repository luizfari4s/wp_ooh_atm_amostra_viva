def main(type, inicio, fim, day_minus):
    from datetime import datetime
    import glob
    import pandas as pd
    import warnings
    import os
    from . import functions
    warnings.filterwarnings(
    "ignore",
    message="DataFrame is highly fragmented",
    category=pd.errors.PerformanceWarning
    )

    dominio_interno = os.getlogin()
    logger = functions.logger
    print(f'parametros recebidos: inicio {inicio} e  dminus {day_minus}')
    logger.write( etapa='Charge', mensagem=f'parametros recebidos: inicio {inicio} e  dminus {day_minus}') 

    logger.write( etapa='Charge', mensagem=' carregando dados QMOB') 
    # Carregamento das bases do QMOB no nivel de relatório (SURVEI & REPORT ID)
    list_df, init = functions.df_charge(type,inicio, fim)
    
    # Carregamento da base do masterfile fixa
    logger.write( etapa='Charge', mensagem='Carregando MF')
    masterfile = functions.masterfile_data(f'C:/Users/{dominio_interno}/Numerator International/BKO - Documents/Report/Elegibilidade OOH/projeto_ooh/datalake/barcodes_ooh/OOH Masterfile - Barcodes Ativos - 2025_07_15 Resumo.CSV')

    # Geração de master, o conjunto principal de onde parte as operações. (QMOB X MASTERFILE)
    master = functions.conjunto_principal(list_df,masterfile,csv_path=False,reprocessing=False) # Requisição não está respeitando o filtro de data
    logger.write( etapa='Charge', mensagem='Dados Principais carregados MF, QMOB e AMOSTRA_VIVA')

    # A API não respeita os limites de data, então preciso fazer um filtro no pós-normalização
    # Transformação, ajuste de coluna, tipagem de dados, e criação de colunas auxiliares;
    master_transformed = functions.transform_w(master)

    # Segmentação dos dados por data do mês de referência
    logger.write( etapa='Operações', mensagem='Filtragem de dados brutos')
    init = datetime.strptime(init, "%d.%m.%Y %H:%M:%S").date()

    #logger.write( etapa='info', mensagem=f'Priodo entre: {master_transformed.StartTime} e {master_transformed.StartTime.max() - pd.Timedelta(days=day_minus)}')       
    master_transformed = master_transformed.loc[(master_transformed.StartTime >= init) &                                               
    (master_transformed.StartTime <= master_transformed.StartTime.max() - pd.Timedelta(days=day_minus))]

    # Determinar Atos, o que é um ato e o que é um dnc linha a linha
    logger.write( etapa='Operações', mensagem='Determinando atos')
    master_transformed = functions.determina_ato_dnc(master_transformed) 

    # informação auxiliar de data
    dt_inicio = master_transformed.StartTime.min()
    dt_fim = master_transformed.StartTime.max()
    
    logger.write( etapa='Operações', mensagem='Atos brutos processados')

    # Atualização da base Actos QMOB
    functions.salvar_csv_sharepoint(master_transformed)
    logger.write( etapa='Operações', mensagem='Actos_Qmob atualizado')


    # Estruturação da base para identificação atos e dnc por dia, semana, mes
    logger.write( etapa='Operações', mensagem='Qualificação de registros iniciada')
    funil1 = functions.funil_1(master_transformed)
    funil2 = functions.funil_2(funil1)
    estruct_analise = functions.estruct_analise_v2(funil1)

    logger.write( etapa='Operações', mensagem='Qualificação de registros concluída')

    # Carregamento da amostra viva "condolida_ooh" tabela da esquerda à ser enriqucida
    logger.write( etapa='Charge', mensagem='Carregando Amostra Viva')

    # Caminho do arquivo depende de expressão regular. Qualquer alteração no nome ou em colunas de dentro gera erro
    caminho = f'C:/Users/{dominio_interno}/Numerator International/BKO - Documents/Report/Elegibilidade OOH/projeto_ooh/datalake/consolida ooh/Consolida de Individuos OOH_*.xlsx'
    arquivo = glob.glob(caminho)[0]  # pega o primeiro que encontrar, arquivo mais recente
    amostra_viva = functions.amostra_viva(arquivo, estruct_analise)

    # Cruzamento final, e operações internas de normalização de dados
    logger.write( etapa='Operações', mensagem='Cruzamento ELEGIVEIS vs AMOSTRA_VIVA')
    eleg = functions.elegibles(funil2, amostra_viva, estruct_analise, dt_inicio, dt_fim)

    # Amostra final, combinação de arquivos e geração de colunas de analise
    logger.write( etapa='Operações', mensagem='Ralizando Salvamento de dados finais')
    functions.final_ams(eleg, dt_inicio, dt_fim)

    # Fim do processo
    logger.write( etapa='END', mensagem='Pipeline Concluído')
    
if __name__ == '__main__':  
    main('rt', "01.08.2026", '',0) 