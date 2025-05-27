# src/services/utils.py
import logging
logger = logging.getLogger(__name__)

def print_message(sender, receiver, msg_type, content, color_tag="white"):
    # Este é um fallback para console se não houver um log_callback
    print(f"[{sender} -> {receiver}] {msg_type}: {content}")
    logger.debug(f"Utils: print_message - {sender} -> {receiver} {msg_type}")

def print_file_action(entity, action, filename, color_tag="green"):
    print(f"[{entity}] {action} Arquivo: {filename}")
    logger.debug(f"Utils: print_file_action - {entity} {action} {filename}")

def print_step(title, color_tag="magenta"):
    print(f"\n--- {title} ---")
    logger.debug(f"Utils: print_step - {title}")
