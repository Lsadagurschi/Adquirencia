import streamlit as st
import time
import threading
import os
import datetime
import queue # Importa o módulo queue

# Importa as classes e serviços de dentro do seu pacote src
from src.services.simulation import PaymentSimulator

# --- Configurações Iniciais ---
output_dir = "data/output"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Configurações de logging para o console (ainda útil para depuração interna)
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("app.py: Script iniciado.")

st.set_page_config(
    page_title="Simulador de Fluxo de Pagamentos",
    page_icon="💳",
    layout="wide"
)

# --- Título e Descrição da Aplicação ---
st.title("💳 Simulador de Fluxo de Pagamentos Detalhado")
st.write("Este aplicativo simula o complexo fluxo de transações financeiras, incluindo **autorização**, **captura**, **liquidação**, **faturamento**, **pagamento ao lojista**, **relatórios regulatórios** e, agora, o intrincado processo de **chargeback**.")

# --- Inicialização do Estado da Sessão do Streamlit ---
if 'log_messages' not in st.session_state:
    st.session_state.log_messages = ["Clique em 'Iniciar Simulação' para começar..."]
    logger.info("app.py: st.session_state.log_messages inicializado.")
if 'simulation_running' not in st.session_state:
    st.session_state.simulation_running = False
    logger.info("app.py: st.session_state.simulation_running inicializado.")
if 'thread_finished' not in st.session_state:
    st.session_state.thread_finished = False
    logger.info("app.py: st.session_state.thread_finished inicializado.")
if 'log_queue' not in st.session_state: # Novo: Fila para comunicação de logs
    st.session_state.log_queue = queue.Queue() # A fila é inicializada aqui
    logger.info("app.py: st.session_state.log_queue inicializado.")

# --- Placeholders para Atualizações Dinâmicas na UI ---
status_placeholder = st.empty()
log_placeholder = st.empty()

# --- Callback para Enviar Logs da Simulação para a FILA (na thread secundária) ---
def streamlit_log_callback(message, color_tag="black"):
    # Esta função é chamada pela thread secundária (simulação)
    # Ela NÃO toca diretamente no st.session_state.
    # Em vez disso, ela coloca a mensagem na fila.
    
    color_map = { # Mapeamento de cores
        "white": "black", "blue": "#1E90FF", "green": "#32CD32",
        "red": "#FF4500", "yellow": "#FFD700", "magenta": "#DA70D6",
        "lightblue": "#ADD8E6", "black": "black",
    }
    html_color = color_map.get(color_tag, "black")
    
    # Coloca a mensagem formatada na fila
    try:
        st.session_state.log_queue.put(f"<span style='color: {html_color};'>{message}</span>")
        logger.debug(f"app.py: Mensagem colocada na fila: {message}")
    except AttributeError:
        # Isso pode acontecer se a fila não for inicializada na primeira execução
        # Mas com a inicialização no session_state, isso deve ser raro
        logger.error("app.py: st.session_state.log_queue não acessível na callback.", exc_info=True)
    except Exception as e:
        logger.error(f"app.py: Erro ao colocar log na fila: {e}", exc_info=True)


# --- Função para Rodar a Simulação em uma Thread Separada ---
def run_simulation_in_thread_target(log_callback_func, output_dir_path):
    logger.info("app.py: Thread de simulação iniciada.")
    try:
        # Passa a função de callback para o simulador
        simulator = PaymentSimulator(output_dir=output_dir_path, log_callback=log_callback_func)
        simulator.run_full_simulation()
    except Exception as e:
        # Se ocorrer um erro crítico na simulação, registre-o na fila
        log_callback_func(f"ERRO CRÍTICO NA SIMULAÇÃO (THREAD): {e}", "red")
        logger.error(f"app.py: Erro na thread de simulação: {e}", exc_info=True)
    finally:
        # Sinaliza que a thread terminou. Esta é a única modificação direta no st.session_state
        # que a thread secundária faz, e o Streamlit lida com ela assincronamente.
        st.session_state.thread_finished = True
        logger.info("app.py: st.session_state.thread_finished definido como True.")


# --- Lógica Principal do Streamlit App ---
logger.info(f"app.py: Início da lógica principal. simulation_running: {st.session_state.simulation_running}")

# Botão Iniciar/Reiniciar Simulação
if st.button("Iniciar Simulação", disabled=st.session_state.simulation_running):
    logger.info("app.py: Botão 'Iniciar Simulação' clicado.")
    st.session_state.simulation_running = True
    st.session_state.log_messages = [] # Limpa o log ao iniciar
    st.session_state.thread_finished = False # Reseta o flag da thread
    
    # Limpa a fila ao iniciar uma nova simulação
    with st.session_state.log_queue.mutex: # Garante que a fila seja limpa de forma thread-safe
        st.session_state.log_queue.queue.clear() 
    
    log_placeholder.empty()
    status_placeholder.empty()
    
    thread = threading.Thread(target=run_simulation_in_thread_target, args=(streamlit_log_callback, output_dir))
    thread.start()
    logger.info("app.py: Thread de simulação disparada.")

# --- Loop de Atualização de Logs na Thread Principal ---
if st.session_state.simulation_running:
    logger.info("app.py: Entrando no loop de atualização de logs.")
    status_placeholder.info("Simulação em andamento...")
    
    while not st.session_state.thread_finished or not st.session_state.log_queue.empty():
        # Enquanto a thread não terminou OU ainda há mensagens na fila
        while not st.session_state.log_queue.empty():
            try:
                # Pega a mensagem da fila (non-blocking)
                message = st.session_state.log_queue.get_nowait()
                st.session_state.log_messages.append(message)
                logger.debug(f"app.py: Mensagem pega da fila: {message[:50]}...")
            except queue.Empty:
                break # Fila vazia, sai do loop interno
            except Exception as e:
                logger.error(f"app.py: Erro ao pegar log da fila: {e}", exc_info=True)
                break

        # Renderiza todo o conteúdo do log acumulado no st.session_state
        current_log_content = "<br>".join(st.session_state.log_messages)
        log_placeholder.markdown(current_log_content, unsafe_allow_html=True)
        
        time.sleep(0.1) # Pequena pausa para evitar sobrecarga de CPU e permitir que o Streamlit atualize.

    logger.info("app.py: Saindo do loop de atualização de logs.")
    # Quando a thread_finished for True E a fila estiver vazia, a simulação terminou.
    final_log_content = "<br>".join(st.session_state.log_messages)
    log_placeholder.markdown(final_log_content, unsafe_allow_html=True)
    
    status_placeholder.success("Simulação concluída! Verifique a pasta `data/output/` para os arquivos gerados.")
    st.session_state.simulation_running = False
    st.session_state.thread_finished = False # Resetar para a próxima execução
    logger.info("app.py: Simulação concluída e estado resetado.")

# --- Exibir o log inicial/final quando a simulação não está rodando ---
else:
    initial_log_content = "<br>".join(st.session_state.log_messages)
    log_placeholder.markdown(initial_log_content, unsafe_allow_html=True)
    logger.info("app.py: Exibindo log inicial/final.")


# --- Barra Lateral com Informações Adicionais ---
st.sidebar.header("Informações")
st.sidebar.write("Os arquivos gerados durante a simulação (captura, liquidação, CNAB, regulatórios, etc.) serão salvos na pasta **`data/output/`** do seu ambiente.")
st.sidebar.markdown("""
    ---
    Desenvolvido para fins **didáticos**.
    Simula um ecossistema de pagamentos para ilustrar a interação
    entre Estabelecimentos, Portadores, Adquirentes, Bandeiras, Emissores e o Banco Central.
    """)
logger.info("app.py: Script finalizado (renderização do Streamlit).")
