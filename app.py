import streamlit as st
import time
import threading
import os
import datetime

# Importa as classes e serviços de dentro do seu pacote src
from src.services.simulation import PaymentSimulator

# --- Configurações Iniciais ---
output_dir = "data/output"
# Garante que a pasta de output exista ao iniciar o app
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

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
if 'simulation_running' not in st.session_state:
    st.session_state.simulation_running = False
if 'thread_finished' not in st.session_state:
    st.session_state.thread_finished = False

# --- Placeholders para Atualizações Dinâmicas na UI ---
# Estes placeholders devem ser criados no início do script Streamlit
# para que existam durante todo o ciclo de vida da aplicação.
status_placeholder = st.empty()
log_placeholder = st.empty()

# --- Callback para Enviar Logs da Simulação para o Streamlit ---
def streamlit_log_callback(message, color_tag="black"):
    color_map = {
        "white": "black",
        "blue": "#1E90FF",
        "green": "#32CD32",
        "red": "#FF4500",
        "yellow": "#FFD700",
        "magenta": "#DA70D6",
        "lightblue": "#ADD8E6",
        "black": "black",
    }
    html_color = color_map.get(color_tag, "black")
    st.session_state.log_messages.append(f"<span style='color: {html_color};'>{message}</span>")


# --- Função para Rodar a Simulação em uma Thread Separada ---
def run_simulation_in_thread_target(log_callback, output_dir_path):
    try:
        simulator = PaymentSimulator(output_dir=output_dir_path, log_callback=log_callback)
        simulator.run_full_simulation()
    except Exception as e:
        log_callback(f"ERRO NA SIMULAÇÃO: {e}", "red")
    finally:
        # Importante: A thread secundária APENAS modifica o session_state.
        # Ela NÃO deve tentar interagir diretamente com a UI ou forçar reruns.
        st.session_state.thread_finished = True


# --- Lógica Principal do Streamlit App ---

# Botão Iniciar/Reiniciar Simulação
if st.button("Iniciar Simulação", disabled=st.session_state.simulation_running):
    st.session_state.simulation_running = True
    st.session_state.log_messages = [] # Limpa o log ao iniciar
    st.session_state.thread_finished = False # Reseta o flag da thread
    
    # Limpa os placeholders visíveis para iniciar uma nova simulação
    log_placeholder.empty()
    status_placeholder.empty()
    
    # Inicia a função de simulação em uma nova thread.
    thread = threading.Thread(target=run_simulation_in_thread_target, args=(streamlit_log_callback, output_dir))
    thread.start()
    
    # --- REMOVIDA AQUI: st.experimental_rerun() ---
    # O Streamlit irá re-executar o script no próximo ciclo de renderização
    # devido à alteração de st.session_state.simulation_running.

# --- Loop de Atualização de Logs na Thread Principal ---
# Este loop só é executado se a simulação estiver rodando.
if st.session_state.simulation_running:
    # A mensagem de status deve ser exibida imediatamente
    status_placeholder.info("Simulação em andamento...")
    
    while not st.session_state.thread_finished: # Loop enquanto a thread não terminou
        # Converte a lista de mensagens em uma única string HTML para exibir.
        current_log_content = "<br>".join(st.session_state.log_messages)
        log_placeholder.markdown(current_log_content, unsafe_allow_html=True)
        
        # Pequena pausa para evitar sobrecarga de CPU e permitir que o Streamlit
        # atualize a interface. Ajuste este valor se necessário.
        time.sleep(0.1) # Pausa de 100ms

    # Quando a thread_finished for True, a simulação terminou.
    # Exibe o log final para garantir que todas as mensagens sejam mostradas.
    final_log_content = "<br>".join(st.session_state.log_messages)
    log_placeholder.markdown(final_log_content, unsafe_allow_html=True)
    
    # Atualiza o status final e permite que o botão seja clicado novamente.
    status_placeholder.success("Simulação concluída! Verifique a pasta `data/output/` para os arquivos gerados.")
    st.session_state.simulation_running = False
    st.session_state.thread_finished = False # Resetar para a próxima execução

# --- Exibir o log inicial/final quando a simulação não está rodando ---
# Garante que o log esteja visível mesmo antes ou depois da simulação
# e que a mensagem "Clique para iniciar..." apareça.
else:
    initial_log_content = "<br>".join(st.session_state.log_messages)
    log_placeholder.markdown(initial_log_content, unsafe_allow_html=True)


# --- Barra Lateral com Informações Adicionais ---
st.sidebar.header("Informações")
st.sidebar.write("Os arquivos gerados durante a simulação (captura, liquidação, CNAB, regulatórios, etc.) serão salvos na pasta **`data/output/`** do seu ambiente.")
st.sidebar.markdown("""
    ---
    Desenvolvido para fins **didáticos**.
    Simula um ecossistema de pagamentos para ilustrar a interação
    entre Estabelecimentos, Portadores, Adquirentes, Bandeiras, Emissores e o Banco Central.
    """)
