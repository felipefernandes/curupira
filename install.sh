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
    __  __ __  ____  __ __  ____ ____  ____    ____ 
   /  ]|  |  ||    \|  |  ||    \    ||    \  /    |
  /  / |  |  ||  D  )  |  ||  o  )  | |  D  )|  o  |
 /  /  |  |  ||    /|  |  ||   _/|  | |    / |     |
/   \_ |  :  ||    \|  :  ||  |  |  | |    \ |  _  |
\     ||     ||  .  \     ||  |  |  | |  .  \|  |  |
 \____| \__,_||__|\_|\__,_||__| |____||__|\_||__|__|
                                                                                              
EOF
echo -e "${NC}"
echo -e "${CYAN}:: O AI Bot leve para Raspberry Pi ::${NC}"
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

# Instalar CLI Global (Curupira Wrapper)
echo -e "${YELLOW}[*] Instalando comando global 'curupira'...${NC}"
WRAPPER_SRC="curupira_wrapper.sh"
WRAPPER_DEST="/usr/local/bin/curupira"

# Preparar o wrapper com os caminhos corretos
CURRENT_DIR=$(pwd)
CURRENT_USER=$(whoami)

# Substituir placeholders em um arquivo temporário
cp $WRAPPER_SRC curupira_tmp.sh
sed -i "s|__PROJECT_DIR__|$CURRENT_DIR|g" curupira_tmp.sh
sed -i "s|__USER_NAME__|$CURRENT_USER|g" curupira_tmp.sh

# Mover para bin (precisa de sudo)
echo -e "${BLUE}[i] Precisamos de permissão sudo para criar o comando global.${NC}"
sudo mv curupira_tmp.sh $WRAPPER_DEST
sudo chmod +x $WRAPPER_DEST

if [ -f "$WRAPPER_DEST" ]; then
    echo -e "${GREEN}[OK] Comando 'curupira' instalado!${NC}"
else
    echo -e "${RED}[!] Falha ao instalar comando global.${NC}"
fi

# Finalização
echo ""
echo -e "${GREEN}==============================================${NC}"
echo -e "${GREEN}   INSTALAÇÃO CONCLUÍDA COM SUCESSO! 🍃      ${NC}"
echo -e "${GREEN}==============================================${NC}"
echo ""
echo -e "Agora você pode usar o comando global:"
echo -e "${CYAN}curupira acorda${NC}   -> Para rodar agora"
echo -e "${CYAN}sudo curupira daemon${NC} -> Para instalar e rodar em background (boot)"
echo ""

