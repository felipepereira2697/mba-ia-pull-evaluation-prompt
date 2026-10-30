"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull do prompt semente do desafio
3. Salva localmente em prompts/bug_to_user_story_v1.yml

DICAS DE IMPLEMENTAÇÃO:

- O pull é feito pelo cliente do LangSmith:

      from langsmith import Client
      client = Client()
      prompt = client.pull_prompt(
          "leonanluppi/bug_to_user_story_v1",
          dangerously_pull_public_prompt=True,
      )

- O parâmetro `dangerously_pull_public_prompt=True` é obrigatório sempre que o
  identificador tem dono explícito ("owner/nome"). O LangSmith bloqueia esse pull
  por padrão porque um prompt do Hub é um objeto LangChain serializado, que pode
  vir de terceiros. Aqui o prompt é o do desafio, então o risco é conhecido.

- O retorno é um ChatPromptTemplate. Para extrair o conteúdo das mensagens,
  use a serialização nativa do LangChain (`prompt.messages`, e o atributo
  `.prompt.template` de cada mensagem).

- Use `save_yaml` de utils.py para gravar o resultado no arquivo .yml.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import HumanMessagePromptTemplate, SystemMessagePromptTemplate
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()

SEED_PROMPT = "leonanluppi/bug_to_user_story_v1"
OUTPUT_PATH = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v1.yml"


def pull_prompts_from_langsmith():
    """
    Faz pull do prompt semente e o converte para o formato do arquivo YAML.

    Returns:
        Dicionário pronto para ser salvo em YAML
    """
    client = Client()
    prompt = client.pull_prompt(SEED_PROMPT, dangerously_pull_public_prompt=True)

    templates = {}
    for message in prompt.messages:
        if isinstance(message, SystemMessagePromptTemplate):
            templates["system_prompt"] = message.prompt.template
        elif isinstance(message, HumanMessagePromptTemplate):
            templates["user_prompt"] = message.prompt.template

    return {
        "bug_to_user_story_v1": {
            "description": "Prompt para converter relatos de bugs em User Stories",
            **templates,
            "version": "v1",
            "source": SEED_PROMPT,
        }
    }


def main():
    """Função principal"""
    print_section_header("PULL DO PROMPT INICIAL")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    try:
        print(f"Puxando prompt do LangSmith Hub: {SEED_PROMPT}")
        prompt_data = pull_prompts_from_langsmith()
    except Exception as e:
        print(f"❌ Erro ao puxar o prompt: {e}")
        return 1

    if not save_yaml(prompt_data, str(OUTPUT_PATH)):
        return 1

    print(f"✓ Prompt salvo em {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
