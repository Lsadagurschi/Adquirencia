# app.py
import streamlit as st
import time
import threading
import os

# Importa a classe do simulador de dentro do seu pacote src
from src.services.simulation import PaymentSimulator

# Garante que a pasta de output exista
output_dir = "data/output"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

st.set_page_config(
    page_title="Simulador de Fluxo de Pagamentos",
    page_icon="💳",
    layout="wide"
)

st.title("💳 Simulador de Fluxo de Pagamentos Detalhado")
st.write("Este aplicativo simula o complexo fluxo de transações financeiras entre Adquirentes, Bandeiras e Emissores, incluindo a troca de mensagens em tempo real (ISO 8583) e arquivos em lote (Captura, Liquidação, CNAB, 3040, Regulatórios).")

# Inicializa o estado da sessão do Streamlit
if 'log_content' not in st.session_state:
    st.session_state.log_content = "Clique em 'Iniciar Simulação' para começar..."
if 'simulation_running' not in st.session_state:
    st.session_state.simulation_running = False

# Placeholder para o log e status
log_placeholder = st.empty()
status_placeholder = st.empty()

# Callback para o simulador enviar logs para o Streamlit
def streamlit_log_callback(message, color_tag="black"):
    # Adiciona a mensagem ao log e atualiza o componente QTextEdit do Streamlit
    # usando HTML para cores.
    color_map = {
        "white": "black", "blue": "blue", "green": "green", "red": "red",
        "yellow": "orange", "magenta": "purple", "lightblue": "lightblue",
        "black": "black", # Default
    }
    html_color = color_map.get(color_tag, "black")

    # O Streamlit não tem um QLineEdit "append". Precisa atualizar o Text Area inteiro.
    # Por isso, acumulamos no st.session_state.log_content
    st.session_state.log_content += f"<font color='{html_color}'>{message}</font><br>"
    log_placeholder.markdown(st.session_state.log_content, unsafe_allow_html=True)
    time.sleep(0.1) # Pequeno atraso para visualização

def run_simulation_in_thread():
    # A lógica principal da simulação
    simulator = PaymentSimulator(output_dir=output_dir, log_callback=streamlit_log_callback)
    simulator.run_full_simulation()

    # Finaliza a simulação e atualiza o status final
    status_placeholder.info("Simulação concluída!")
    st.session_state.simulation_running = False
    st.experimental_rerun() # Força o Streamlit a re-renderizar e habilitar o botão

# Botão Iniciar/Reiniciar Simulação
if st.button("Iniciar Simulação", disabled=st.session_state.simulation_running):
    st.session_state.simulation_running = True
    st.session_state.log_content = "" # Limpa o log ao iniciar
    log_placeholder.empty()
    status_placeholder.empty()

    # Inicia a simulação em uma thread separada para não travar a UI do Streamlit
    thread = threading.Thread(target=run_simulation_in_thread)
    thread.start()
    status_placeholder.info("Simulação em andamento...")
    st.experimental_rerun() # Re-renderiza para desabilitar o botão

# Exibe o log atualizado constantemente
log_placeholder.markdown(st.session_state.log_content, unsafe_allow_html=True)

st.sidebar.header("Informações")
st.sidebar.write("Os arquivos gerados serão salvos na pasta `data/output/` do repositório.")
st.sidebar.write("Desenvolvido para fins didáticos.")
