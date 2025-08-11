import yaml
import os
from pathlib import Path

class ConfigYml:
    _config = None
    
    @staticmethod
    def load_config():
        """Carrega configurações do arquivo YAML"""
        if ConfigYml._config is None:
            # Buscar o arquivo config.yml na pasta config/
            config_path = Path(__file__).parent.parent / "config" / "config.yml"
            
            if not config_path.exists():
                raise FileNotFoundError(f"Arquivo de configuração não encontrado: {config_path}")
            
            with open(config_path, 'r', encoding='utf-8') as file:
                ConfigYml._config = yaml.safe_load(file)
        
        return ConfigYml._config
    
    @staticmethod
    def get_api_config():
        """Retorna configurações da API"""
        config = ConfigYml.load_config()
        return config.get('api', {})
    
    @staticmethod
    def get_database_config():
        """Retorna configurações do banco de dados"""
        config = ConfigYml.load_config()
        return config.get('database', {})
    
    @staticmethod
    def get_minio_config():
        """Retorna configurações do MinIO"""
        config = ConfigYml.load_config()
        return config.get('minio', {})
    
    @staticmethod
    def get_storage_config():
        """Retorna configurações de armazenamento"""
        config = ConfigYml.load_config()
        return config.get('storage', {})
    
    @staticmethod
    def get_processing_config():
        """Retorna configurações de processamento"""
        config = ConfigYml.load_config()
        return config.get('processing', {})
    
    @staticmethod
    def get_resources():
        """Retorna lista de recursos da API"""
        config = ConfigYml.load_config()
        api_config = config.get('api', {})
        return api_config.get('resources', []) 