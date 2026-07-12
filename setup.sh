set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}"
echo "╔════════════════════════════════════════════════════╗"
echo "║  Squire Production Backend - Setup                 ║"
echo "╚════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check Python 3.10 explicitly
echo -e "\n${YELLOW}[1/5] Checking Python 3.10...${NC}"

if ! command -v py &> /dev/null; then
    echo -e "${RED}❌ Python launcher (py) not found! Install Python 3.10${NC}"
    exit 1
fi

PY_VERSION=$(py -3.10 --version 2>&1 || true)

if [[ ! $PY_VERSION == *"Python 3.10"* ]]; then
    echo -e "${RED}❌ Python 3.10 not found! Please install Python 3.10${NC}"
    exit 1
fi

echo -e "${GREEN}✓ $PY_VERSION found${NC}"

# Create venv using Python 3.10
echo -e "\n${YELLOW}[2/5] Creating virtual environment (Python 3.10)...${NC}"

if [ ! -d "venv" ]; then
    py -3.10 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

source venv/Scripts/activate 2>/dev/null || source venv/bin/activate

echo -e "${GREEN}✓ Virtual environment activated${NC}"

echo -e "\n${YELLOW}[3/5] Upgrading pip...${NC}"
python -m pip install --upgrade pip setuptools wheel -q
echo -e "${GREEN}✓ pip upgraded${NC}"

echo -e "\n${YELLOW}[4/5] Installing dependencies...${NC}"
pip install -q -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

echo -e "\n${YELLOW}[5/5] Setting up environment...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env from template${NC}"
    echo -e "${YELLOW}   Please edit .env with your configuration!${NC}"
else
    echo -e "${GREEN}✓ .env already exists${NC}"
fi