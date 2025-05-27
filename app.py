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
if 'log_content' not in st.session_state:
    st.session_state.log_content = "Clique em 'Iniciar Simulação' para começar..."
if 'simulation_running' not in st.session_state:
    st.session_state.simulation_running = False
if 'thread_finished' not in st.session_state: # Novo estado para sinalizar o fim da thread
    st.session_state.thread_finished = False

# --- Placeholders para Atualizações Dinâmicas na UI ---
status_placeholder = st.empty()
log_placeholder = st.empty()

# --- Callback para Enviar Logs da Simulação para o Streamlit ---
def streamlit_log_callback(message, color_tag="black"):
    color_map = {
        "white": "black",
        "blue": "#1E90FF",       # DodgerBlue
        "green": "#32CD32",      # LimeGreen
        "red": "#FF4500",        # OrangeRed
        "yellow": "#FFD700",     # Gold (mais visível que yellow puro)
        "magenta": "#DA70D6",    # Orchid (um roxo suave)
        "lightblue": "#ADD8E6",  # LightBlue
        "black": "black",        # Padrão
    }
    html_color = color_map.get(color_tag, "black")
    
    st.session_state.log_content += f"<span style='color: {html_color};'>{message}</span><br>"
    
    # Atualiza o componente de log na UI do Streamlit.
    # Usar .markdown() com unsafe_allow_html=True
    log_placeholder.markdown(st.session_state.log_content, unsafe_allow_html=True)
    time.sleep(0.05) # Pequeno atraso para dar tempo de renderizar e para a visualização


# --- Função para Rodar a Simulação em uma Thread Separada ---
def run_simulation_in_thread_target(log_callback, output_dir_path):
    try:
        simulator = PaymentSimulator(output_dir=output_dir_path, log_callback=log_callback)
        simulator.run_full_simulation()
    except Exception as e:
        log_callback(f"ERRO NA SIMULAÇÃO: {e}", "red")
    finally:
        st.session_state.thread_finished = True


# --- Lógica Principal do Streamlit App ---

# Verifica se a simulação está em andamento (no estado da sessão)
if st.session_state.simulation_running:
    status_placeholder.info("Simulação em andamento...")
    # Exibe o log continuamente enquanto a simulação está rodando
    # Não precisa de uma chamada explícita para o log_placeholder aqui,
    # pois o callback já está fazendo isso.
    # O Streamlit irá re-renderizar o log_placeholder quando o session_state.log_content mudar.

    # Se a thread terminou, atualiza o status final e permite o botão novamente
    if st.session_state.thread_finished:
        status_placeholder.success("Simulação concluída! Verifique a pasta `data/output/` para os arquivos gerados.")
        st.session_state.simulation_running = False
        st.session_state.thread_finished = False # Resetar para a próxima rodada
        # Não precisa de rerun aqui. As mudanças de session_state farão o Streamlit re-renderizar.

# Botão Iniciar/Reiniciar Simulação
if st.button("Iniciar Simulação", disabled=st.session_state.simulation_running):
    st.session_state.simulation_running = True
    st.session_state.log_content = "" # Limpa o log ao iniciar
    st.session_state.thread_finished = False # Reseta o flag da thread
    
    log_placeholder.empty() # Limpa o log visível
    status_placeholder.empty() # Limpa o status visível
    
    # Inicia a função de simulação em uma nova thread.
    thread = threading.Thread(target=run_simulation_in_thread_target, args=(streamlit_log_callback, output_dir))
    thread.start()
    
    # REMOVIDA: st.experimental_rerun() AQUI.
    # A simples alteração de st.session_state.simulation_running = True
    # já é suficiente para que o Streamlit, no próximo ciclo de renderização,
    # desabilite o botão.

# Exibe o log atualizado (para quando a simulação não está rodando ativamente, mas o log precisa ser visto)
log_placeholder.markdown(st.session_state.log_content, unsafe_allow_html=True)


# --- Barra Lateral com Informações Adicionais ---
st.sidebar.header("Informações")
st.sidebar.write("Os arquivos gerados durante a simulação (captura, liquidação, CNAB, regulatórios, etc.) serão salvos na pasta **`data/output/`** do seu ambiente.")
st.sidebar.markdown("""
    ---
    Desenvolvido para fins **didáticos**.
    Simula um ecossistema de pagamentos para ilustrar a interação
    entre Estabelecimentos, Portadores, Adquirentes, Bandeiras, Emissores e o Banco Central.
    """)
