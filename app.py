import streamlit as st
import time
import threading
import os
import datetime
import queue

# Importa as classes e serviços de dentro do seu pacote src
from src.services.simulation import PaymentSimulator

# --- Configurações Iniciais ---
output_dir = "data/output"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("app.py: Script iniciado.")

st.set_page_config(
    page_title="Simulador de Fluxo de Pagamentos",
    page_icon="💳",
    layout="wide"
)

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
if 'log_queue' not in st.session_state:
    st.session_state.log_queue = queue.Queue()
    logger.info("app.py: st.session_state.log_queue inicializado.")

# --- Placeholders para Atualizações Dinâmicas na UI ---
status_placeholder = st.empty()
# Novo placeholder para a animação
animation_placeholder = st.empty()
log_placeholder = st.empty()


# --- Funções Auxiliares para Animação ---
def get_image_path(entity_name):
    """Retorna o caminho da imagem para uma entidade."""
    base_path = "assets/images"
    return f"{base_path}/{entity_name}.png"


def draw_animation_step(step_data):
    """
    Desenha um passo da animação com base nos dados recebidos.
    step_data: Dicionário com 'description', 'active_entities', 'flow_path'
    """
    description = step_data.get('description', '')
    active_entities = step_data.get('active_entities', [])
    flow_path_display = step_data.get('flow_path', None)

    # Definição das entidades e seus IDs (para consistência com o CSS)
    entities = {
        "client": {"label": "Cliente"},
        "store": {"label": "Estabelecimento"},
        "acquirer": {"label": "Adquirente"},
        "flag": {"label": "Bandeira"},
        "issuer": {"label": "Emissor"},
        "bcb": {"label": "Banco Central"},
    }

    # CSS para layout e destaque
    css = """
    <style>
        .animation-container {
            display: flex;
            justify-content: space-around;
            align-items: flex-start; /* Alinha no topo para que a descrição não mova */
            padding: 10px;
            margin-bottom: 20px;
            background-color: #f0f2f6;
            border-radius: 10px;
            flex-wrap: wrap; /* Permite que os itens quebrem a linha em telas menores */
        }
        .entity-box {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            margin: 10px;
            padding: 10px;
            border: 2px solid transparent; /* Borda transparente padrão */
            border-radius: 8px;
            transition: border-color 0.3s ease-in-out, box-shadow 0.3s ease-in-out; /* Transição suave */
            min-width: 120px; /* Garante largura mínima */
        }
        .entity-box.active {
            border-color: #4CAF50; /* Borda verde para entidade ativa */
            box-shadow: 0 0 10px rgba(76, 175, 80, 0.5); /* Sombra suave */
        }
        .entity-box img {
            width: 80px;
            height: 80px;
            object-fit: contain;
            margin-bottom: 5px;
        }
        .flow-indicator {
            font-size: 1.1em;
            font-weight: bold;
            color: #555;
            margin-top: 10px;
            width: 100%; /* Ocupa a largura total para centralizar */
            text-align: center;
            min-height: 25px; /* Para evitar pular o layout */
            display: flex; /* Para alinhar o ícone do pagamento */
            justify-content: center;
            align-items: center;
        }
    </style>
    """
    
    html_content = f"{css}<div class='animation-container'>"

    # Adiciona as entidades ao container, com destaque se estiverem ativas
    for entity_id, data in entities.items():
        is_active = entity_id in active_entities
        active_class = "active" if is_active else ""
        
        img_src = get_image_path(entity_id) 
        
        html_content += f"""
        <div class="entity-box {active_class}">
            <img src="{img_src}" alt="{data['label']}">
            <strong>{data['label']}</strong>
        </div>
        """
    html_content += "</div>"

    # Adiciona a descrição da etapa e o indicador de fluxo
    html_content += f"<div class='flow-indicator'>{description}"
    if flow_path_display:
        # Substitui '_to_' e '_from_' por setas para visualização do fluxo
        # e insere o ícone de pagamento no meio do fluxo
        path_parts = flow_path_display.split('_to_')
        if len(path_parts) == 2:
            source = path_parts[0].capitalize()
            dest = path_parts[1].capitalize()
            flow_display = f"{source} &#8594; <img src='assets/images/payment_token.png' width='25px' style='vertical-align:middle; margin: 0 5px;'> &#8594; {dest}"
        else: # Handle 'from' cases or simpler flows
            path_parts = flow_path_display.split('_from_')
            if len(path_parts) == 2:
                source = path_parts[1].capitalize() # 'from' é o destino, então o segundo é a origem
                dest = path_parts[0].capitalize()
                flow_display = f"{source} &#8594; <img src='assets/images/payment_token.png' width='25px' style='vertical-align:middle; margin: 0 5px;'> &#8594; {dest}"
            else: # Fallback para casos não mapeados, ou fluxo simples
                 flow_display = flow_path_display.replace('_', ' &#8594; ')
                 # Se não tiver token, talvez seja um passo interno ou de setup
                 if 'token' not in flow_path_display:
                     flow_display = "" # Limpa para não mostrar "client -> store" sem o token
                 else:
                     flow_display = flow_path_display.replace('token', '<img src="assets/images/payment_token.png" width="25px" style="vertical-align:middle; margin: 0 5px;">')


        html_content += f"<br><small>{flow_display}</small>" # Usa small para o fluxo

    html_content += "</div>"

    animation_placeholder.markdown(html_content, unsafe_allow_html=True)


# --- Callback para Enviar Logs da Simulação para a FILA (na thread secundária) ---
def streamlit_log_callback(q: queue.Queue, message: str, color_tag: str = "black", animation_data=None):
    """
    Formata a mensagem com cores HTML e a coloca na fila,
    junto com dados para a animação.
    """
    color_map = {
        "white": "black", "blue": "#1E90FF", "green": "#32CD32",
        "red": "#FF4500", "yellow": "#FFD700", "magenta": "#DA70D6",
        "lightblue": "#ADD8E6", "black": "black",
    }
    html_color = color_map.get(color_tag, "black")
    
    formatted_message = f"<span style='color: {html_color};'>{message}</span>"
    
    try:
        # Coloca um dicionário na fila com a mensagem formatada e os dados da animação
        q.put({"log_message": formatted_message, "animation_data": animation_data}) 
        logger.debug(f"app.py: Mensagem colocada na fila: {message}")
    except Exception as e:
        logger.error(f"app.py: Erro ao colocar log na fila: {e}", exc_info=True)


# --- Função para Rodar a Simulação em uma Thread Separada ---
def run_simulation_in_thread_target(log_queue_ref: queue.Queue, log_callback_func, output_dir_path):
    """
    Função alvo para a thread de simulação.
    """
    logger.info("app.py: Thread de simulação iniciada.")
    try:
        # A PaymentSimulator agora espera um log_callback que pode receber 3 argumentos
        simulator = PaymentSimulator(
            output_dir=output_dir_path, 
            log_callback=lambda msg, color, anim_data=None: log_callback_func(log_queue_ref, msg, color, anim_data)
        )
        simulator.run_full_simulation()
    except Exception as e:
        # Em caso de erro crítico, ainda podemos logar e passar dados de animação
        log_callback_func(log_queue_ref, f"ERRO CRÍTICO NA SIMULAÇÃO (THREAD): {e}", "red", {"description": "ERRO NA SIMULAÇÃO", "active_entities": [], "flow_path": None})
        logger.error(f"app.py: Erro na thread de simulação: {e}", exc_info=True)
    finally:
        st.session_state.thread_finished = True
        logger.info("app.py: st.session_state.thread_finished definido como True.")


# --- Lógica Principal do Streamlit App ---
logger.info(f"app.py: Início da lógica principal. simulation_running: {st.session_state.simulation_running}")

if st.button("Iniciar Simulação", disabled=st.session_state.simulation_running):
    logger.info("app.py: Botão 'Iniciar Simulação' clicado.")
    st.session_state.simulation_running = True
    st.session_state.log_messages = [] # Limpa o log ao iniciar
    st.session_state.thread_finished = False # Reseta o flag da thread
    
    with st.session_state.log_queue.mutex:
        st.session_state.log_queue.queue.clear() # Limpa a fila ao iniciar
    
    log_placeholder.empty() # Limpa o placeholder do log na UI
    status_placeholder.empty() # Limpa o placeholder de status na UI
    animation_placeholder.empty() # Limpa o placeholder da animação

    # Renderiza o estado inicial da animação
    draw_animation_step({
        "description": "Simulação Pronta para Iniciar",
        "active_entities": [],
        "flow_path": None
    })
    
    # Inicia a thread de simulação, passando a fila de logs e a função de callback
    thread = threading.Thread(target=run_simulation_in_thread_target, 
                              args=(st.session_state.log_queue, streamlit_log_callback, output_dir))
    thread.start()
    logger.info("app.py: Thread de simulação disparada.")

# --- Loop de Atualização de Logs e Animação na Thread Principal ---
if st.session_state.simulation_running:
    logger.info("app.py: Entrando no loop de atualização de logs e animação.")
    status_placeholder.info("Simulação em andamento...")
    
    while not st.session_state.thread_finished or not st.session_state.log_queue.empty():
        # Processa todas as mensagens na fila para manter a UI atualizada
        while not st.session_state.log_queue.empty():
            try:
                item = st.session_state.log_queue.get_nowait()
                
                # Adiciona a mensagem ao log textual
                st.session_state.log_messages.append(item["log_message"])
                
                # ATUALIZA A ANIMAÇÃO
                if item["animation_data"]:
                    draw_animation_step(item["animation_data"])
                    time.sleep(0.05) # Pequena pausa para a animação ser visível (ajuste conforme necessário)
                
                logger.debug(f"app.py: Item processado da fila: {item['log_message'][:50]}...")
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"app.py: Erro ao processar item da fila: {e}", exc_info=True)
                break

        # Renderiza o log textual acumulado
        current_log_content = "<br>".join(st.session_state.log_messages)
        log_placeholder.markdown(current_log_content, unsafe_allow_html=True)
        
        time.sleep(0.1) # Pequena pausa geral para evitar sobrecarga de CPU

    logger.info("app.py: Saindo do loop de atualização de logs e animação.")
    final_log_content = "<br>".join(st.session_state.log_messages)
    log_placeholder.markdown(final_log_content, unsafe_allow_html=True)
    
    status_placeholder.success("Simulação concluída! Verifique a pasta `data/output/` para os arquivos gerados.")
    st.session_state.simulation_running = False
    st.session_state.thread_finished = False # Resetar para a próxima execução
    logger.info("app.py: Simulação concluída e estado resetado.")

# --- Exibir o log inicial/final e a animação inicial quando a simulação não está rodando ---
else:
    initial_log_content = "<br>".join(st.session_state.log_messages)
    log_placeholder.markdown(initial_log_content, unsafe_allow_html=True)
    
    # Desenha o estado inicial da animação ao carregar o app ou após a simulação
    draw_animation_step({
        "description": "Simulação Pronta para Iniciar",
        "active_entities": [],
        "flow_path": None
    })
    logger.info("app.py: Exibindo log inicial/final e animação inicial.")


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
