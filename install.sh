#!/bin/bash

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Limpar tela
clear

# ASCII Art
echo -e "${GREEN}"
cat << "EOF"
   ______                               _           
  / ____/   __  _____  __  __  ____    (_)   _____  ____ _
 / /       / / / /   \/ / / / / __ \  / /   / ___/ / __ `/
/ /___    / /_/ /     / /_/ / / /_/ / / /   / /    / /_/ / 
\____/    \__,_/     / _,_/ / .___/ /_/   /_/     \__,_/  
                    /_/    /_/                            
EOF
echo -e "${NC}"
echo -e "${CYAN}:: O Protetor do Sistema (DietOpenclaw) para Raspberry Pi ::${NC}"
echo -e "--------------------------------------------------------"
echo ""

# Check Python 3
echo -e "${YELLOW}[*] Verificando Python 3...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[!] Python 3 não encontrado! Por favor instale (sudo apt install python3).${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] Python 3 detectado.${NC}"
echo ""

# Criar venv
echo -e "${YELLOW}[*] Criando ambiente virtual (venv)...${NC}"
if [ -d "venv" ]; then
    echo -e "${BLUE}[i] Ambiente virtual já existe. Pulando criação.${NC}"
else
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[OK] Ambiente virtual criado.${NC}"
    else
        echo -e "${RED}[!] Falha ao criar venv. Verifique se o venv está instalado (sudo apt install python3-venv).${NC}"
        exit 1
    fi
fi
echo ""

# Instalar dependências
echo -e "${YELLOW}[*] Instalando dependências...${NC}"
source venv/bin/activate
pip install --upgrade pip &> /dev/null
pip install -r requirements.txt
if [ $? -eq 0 ]; then
    echo -e "${GREEN}[OK] Dependências instaladas.${NC}"
else
    echo -e "${RED}[!] Erro ao instalar dependências.${NC}"
    exit 1
fi
echo ""

# Configurar .env
echo -e "${YELLOW}[*] Configuração de Ambiente (.env)${NC}"
if [ -f ".env" ]; then
    echo -e "${BLUE}[i] Arquivo .env já existe.${NC}"
    read -p "Deseja reconfigurar? (y/N): " reconf
    if [[ $reconf =~ ^[Yy]$ ]]; then
        SETUP_ENV=true
    else
        SETUP_ENV=false
    fi
else
    SETUP_ENV=true
fi

if [ "$SETUP_ENV" = true ]; then
    echo -e "Por favor, insira suas chaves:"
    
    read -p "TELEGRAM_TOKEN: " tk_token
    read -p "GEMINI_API_KEY: " gm_key
    read -p "AUTHORIZED_USER_ID (Seu ID Telegram): " user_id

    echo "TELEGRAM_TOKEN=$tk_token" > .env
    echo "GEMINI_API_KEY=$gm_key" >> .env
    echo "AUTHORIZED_USER_ID=$user_id" >> .env
    
    echo -e "${GREEN}[OK] Arquivo .env criado/atualizado.${NC}"
fi

# Finalização
echo ""
echo -e "${GREEN}==============================================${NC}"
echo -e "${GREEN}   INSTALAÇÃO CONCLUÍDA COM SUCESSO! 🍃      ${NC}"
echo -e "${GREEN}==============================================${NC}"
echo ""
echo -e "Para iniciar o Curupira, execute:"
echo -e "${CYAN}source venv/bin/activate${NC}"
echo -e "${CYAN}python bot.py${NC}"
echo ""
