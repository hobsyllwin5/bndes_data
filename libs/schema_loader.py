"""
Helper para carregar schema.yml de forma compatível com Docker e local
"""

import yaml
import os


def load_schema_config():
    """Carrega configurações do schema.yml"""
    # Tenta diferentes caminhos (Docker e local)
    possible_paths = [
        '/opt/airflow/config/schema.yml',  # Docker
        'config/schema.yml',  # Local (raiz do projeto)
        os.path.join(os.path.dirname(__file__), '..', 'config', 'schema.yml')  # Relativo
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
    
    raise FileNotFoundError(f"schema.yml não encontrado em nenhum dos caminhos: {possible_paths}")

