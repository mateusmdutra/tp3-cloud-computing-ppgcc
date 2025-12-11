import datetime
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional
import importlib.util

import redis

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Exceção para erros de configuração"""
    pass


class Context:
    
    def __init__(self, host: str, port: int, input_key: str, output_key: str):
        self.host = host
        self.port = port
        self.input_key = input_key
        self.output_key = output_key
        self.last_execution: Optional[datetime.datetime] = None
        self.env: Dict[str, Any] = {}
        self.function_getmtime = self._get_module_mtime()
        
    def _get_module_mtime(self) -> str:
        try:
            module_path = Path(f"/app/function/{os.getenv('ROOT_FUNCTION_MODULE')}.py")
            if module_path.exists():
                timestamp = module_path.stat().st_mtime
                return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            return "Unknown"
        except Exception as e:
            logger.warning(f"Não foi possível obter mtime do módulo: {e}")
            return "Unknown"
        
    def set_env(self, env: Dict[str, Any]) -> None:
        self.env = env

    def set_last_execution(self) -> None:
        self.last_execution = datetime.datetime.now()


class RedisHandler:
    """Handler para processamento de mensagens via Redis"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis_client = self._create_redis_client()
        self.function = self._import_function(f"/app/function/{os.getenv('ROOT_FUNCTION_MODULE')}.py")
        self.context = self._create_context()
        
    def _create_redis_client(self) -> redis.Redis:
        client = redis.Redis(
            host=self.config['redis_host'],
            port=self.config['redis_port'],
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        # Testa a conexão
        client.ping()
        logger.info(f"Conectado ao Redis em {self.config['redis_host']}:{self.config['redis_port']}")
        return client
    
    def _create_context(self) -> Context:
        return Context(
            host=self.config['redis_host'],
            port=self.config['redis_port'],
            input_key=self.config['redis_input_key'],
            output_key=self.config['redis_output_key']
        )
    
    def _import_function(self, root_function_module):
        spec = importlib.util.spec_from_file_location("user_module", root_function_module)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, "handler")
    
    def _get_input(self) -> Optional[Dict[str, Any]]:
        raw_input = self.redis_client.get(self.config['redis_input_key'])
        if raw_input:
            return json.loads(raw_input)
        return None
    
    def _send_output(self, output: Any) -> None:
        if not output:
            return
            
        serialized = json.dumps(output)
        self.redis_client.set(self.config['redis_output_key'], serialized)
        logger.debug("Output enviado com sucesso")
    
    def _process_message(self, input_data: Dict[str, Any]) -> Optional[Any]:
        output = self.function.handler(input_data, self.context)
        self.context.set_last_execution()
        return output
    
    def run(self) -> None:
        logger.info("Iniciando loop de processamento")
        
        while True:
            input_data = self._get_input()
            
            if input_data:
                logger.info("Mensagem recebida, processando...")
                output = self._process_message(input_data)
                
                if output:
                    self._send_output(output)
            
            time.sleep(self.config['sleep_time'])


def load_config() -> Dict[str, Any]:
    redis_output_key = os.getenv('REDIS_OUTPUT_KEY')
    
    if not redis_output_key:
        raise ConfigurationError("REDIS_OUTPUT_KEY não configurado")
    
    return {
        'redis_host': os.getenv('REDIS_HOST', 'localhost'),
        'redis_port': int(os.getenv('REDIS_PORT', '6379')),
        'redis_input_key': os.getenv('REDIS_INPUT_KEY'),
        'redis_output_key': redis_output_key,
        'sleep_time': int(os.getenv('SLEEP_TIME', '5'))
    }


def main() -> None:
    config = load_config()
    handler = RedisHandler(config)
    handler.run()


if __name__ == '__main__':
    main()