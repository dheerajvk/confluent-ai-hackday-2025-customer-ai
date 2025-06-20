#!/bin/bash
# Basic Dependencies Installer
# Installs minimal dependencies needed for Stream Lineage monitoring

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}📦 Basic Dependencies Installer${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
}

main() {
    print_header
    
    print_status "Installing basic dependencies for Stream Lineage monitoring..."
    
    # Install python-dotenv
    print_status "Installing python-dotenv..."
    if pip3 install python-dotenv; then
        print_success "python-dotenv installed successfully"
    else
        print_error "Failed to install python-dotenv"
        exit 1
    fi
    
    # Test if we can now import the monitor
    print_status "Testing Stream Lineage monitor import..."
    if python3 -c "import sys; sys.path.insert(0, 'src'); from streaming.stream_lineage_monitor import lineage_monitor" &> /dev/null; then
        print_success "Stream Lineage monitor can be imported successfully"
        echo ""
        print_success "✅ Basic dependencies installed! You can now run:"
        echo "   ./check_stream_lineage.sh"
        echo "   python3 stream_lineage_status.py"
    else
        print_error "Stream Lineage monitor still cannot be imported"
        print_status "You may need to install all dependencies:"
        echo "   pip3 install -r requirements.txt"
        exit 1
    fi
}

main "$@"