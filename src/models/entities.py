import streamlit as st
import time
import threading
import os
import datetime # Para formatar datas no log

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
# O Streamlit re-executa o script a cada interação, então st.session_state é crucial
# para manter o estado entre as execuções.
if 'log_content' not in st.session_state:
    st.session_state.log_content = "Clique em 'Iniciar Simulação' para começar..."
if 'simulation_running' not in st.session_state:
    st.session_state.simulation_running = False

# --- Placeholders para Atualizações Dinâmicas na UI ---
# Usamos st.empty() para criar "slots" onde podemos atualizar o conteúdo
# sem re-renderizar todo o aplicativo, o que é útil para logs em tempo real.
status_placeholder = st.empty()
log_placeholder = st.empty()

# --- Callback para Enviar Logs da Simulação para o Streamlit ---
def streamlit_log_callback(message, color_tag="black"):
    # Mapeia tags de cor internas para cores HTML/CSS para exibição no Streamlit.
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
    html_color = color_map.get(color_tag, "black") # Pega a cor mapeada, ou preto como fallback

    # Adiciona a nova mensagem formatada ao conteúdo acumulado do log.
    # Usamos <br> para quebra de linha em HTML.
    st.session_state.log_content += f"<span style='color: {html_color};'>{message}</span><br>"
    
    # Atualiza o componente de log na UI do Streamlit.
    # unsafe_allow_html=True é necessário para renderizar tags HTML.
    log_placeholder.markdown(st.session_state.log_content, unsafe_allow_html=True)
    time.sleep(0.05) # Pequeno atraso para dar tempo de renderizar e para a visualização


# --- Função para Rodar a Simulação em uma Thread Separada ---
def run_simulation_in_thread():
    # Instancia o simulador, passando o diretório de saída e a função de callback para logs.
    simulator = PaymentSimulator(output_dir=output_dir, log_callback=streamlit_log_callback)
    simulator.run_full_simulation() # Inicia o fluxo completo da simulação.
    
    # Após a simulação, atualiza o status final e permite que o botão seja clicado novamente.
    status_placeholder.success("Simulação concluída! Verifique a pasta `data/output/` para os arquivos gerados.")
    st.session_state.simulation_running = False
    st.experimental_rerun() # Força o Streamlit a re-renderizar para atualizar o estado do botão.

# --- Botão Iniciar/Reiniciar Simulação ---
if st.button("Iniciar Simulação", disabled=st.session_state.simulation_running):
    st.session_state.simulation_running = True
    st.session_state.log_content = "" # Limpa o log ao iniciar uma nova simulação.
    
    # Limpa os placeholders antes de iniciar a simulação para uma nova corrida.
    log_placeholder.empty()
    status_placeholder.empty()
    
    # Inicia a função de simulação em uma nova thread.
    # Isso é crucial para que a interface do Streamlit não "congele" durante a simulação.
    thread = threading.Thread(target=run_simulation_in_thread)
    thread.start()
    
    # Exibe um status inicial enquanto a simulação está em andamento.
    status_placeholder.info("Simulação em andamento...")
    st.experimental_rerun() # Re-renderiza para desabilitar o botão imediatamente.

# --- Exibe o Log de Eventos (Atualizado pelo callback) ---
# Este `markdown` estará sempre "ouvindo" as atualizações do `log_placeholder`.
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
