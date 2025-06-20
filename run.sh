#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
PID_FILE="$SCRIPT_DIR/.app.pid"
CLEANUP_DONE=false

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_banner() {
    echo -e "${BLUE}"
    cat << 'EOF'
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║  🚀 CONFLUENT AI SUPPORT OPTIMIZER - VENV LAUNCHER                          ║
║                                                                               ║
║  Real-Time Customer Sentiment & Support Optimizer                            ║
║  Built with: Python venv + Confluent + Claude AI + Gradio                   ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# Comprehensive cleanup function
cleanup() {
    if [ "$CLEANUP_DONE" = true ]; then
        return 0
    fi
    
    print_status "Starting cleanup process..."
    
    # Kill the application if it's running
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE" 2>/dev/null)
        if [ ! -z "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            print_status "Stopping application (PID: $pid)..."
            kill -TERM "$pid" 2>/dev/null || true
            sleep 2
            if kill -0 "$pid" 2>/dev/null; then
                print_warning "Force killing application..."
                kill -KILL "$pid" 2>/dev/null || true
            fi
        fi
        rm -f "$PID_FILE"
    fi
    
    # Clean up Python cache files recursively (enhanced)
    print_status "Cleaning up Python cache files recursively..."
    
    # Remove __pycache__ directories recursively (more thorough approach)
    find "$SCRIPT_DIR" -type d -name "__pycache__" -print0 | xargs -0 rm -rf 2>/dev/null || true
    
    # Remove Python bytecode files
    find "$SCRIPT_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
    find "$SCRIPT_DIR" -type f -name "*.pyo" -delete 2>/dev/null || true
    find "$SCRIPT_DIR" -type f -name "*.pyd" -delete 2>/dev/null || true
    
    # Remove Python build artifacts
    find "$SCRIPT_DIR" -type d -name "*.egg-info" -print0 | xargs -0 rm -rf 2>/dev/null || true
    find "$SCRIPT_DIR" -type d -name "build" -print0 | xargs -0 rm -rf 2>/dev/null || true
    find "$SCRIPT_DIR" -type d -name "dist" -print0 | xargs -0 rm -rf 2>/dev/null || true
    
    # Remove additional Python cache and temp files
    find "$SCRIPT_DIR" -type f -name ".coverage" -delete 2>/dev/null || true
    find "$SCRIPT_DIR" -type d -name ".coverage" -print0 | xargs -0 rm -rf 2>/dev/null || true
    find "$SCRIPT_DIR" -type d -name ".mypy_cache" -print0 | xargs -0 rm -rf 2>/dev/null || true
    find "$SCRIPT_DIR" -type d -name ".tox" -print0 | xargs -0 rm -rf 2>/dev/null || true
    
    # Clean up log files
    if [ -f "$SCRIPT_DIR/app.log" ]; then
        print_status "Cleaning up log files..."
        rm -f "$SCRIPT_DIR/app.log"
    fi
    
    # Clean up temporary files
    print_status "Cleaning up temporary files..."
    rm -f "$SCRIPT_DIR"/.coverage 2>/dev/null || true
    rm -rf "$SCRIPT_DIR"/htmlcov 2>/dev/null || true
    rm -rf "$SCRIPT_DIR"/.pytest_cache 2>/dev/null || true
    
    CLEANUP_DONE=true
    print_success "Cleanup completed"
}

# Clean up virtual environment
cleanup_venv() {
    if [ -d "$VENV_DIR" ]; then
        print_status "Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
        print_success "Virtual environment removed"
    fi
}

# Signal handlers
handle_sigint() {
    print_warning "Received SIGINT (Ctrl+C). Cleaning up..."
    cleanup
    exit 130
}

handle_sigterm() {
    print_warning "Received SIGTERM. Cleaning up..."
    cleanup
    exit 143
}

handle_exit() {
    cleanup
}

# Set up signal handlers
trap handle_sigint SIGINT
trap handle_sigterm SIGTERM  
trap handle_exit EXIT

# Check if Python is available
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        print_error "Python is not installed or not in PATH"
        exit 1
    fi
    
    # Check Python version
    local python_version=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
    local major_version=$(echo $python_version | cut -d'.' -f1)
    local minor_version=$(echo $python_version | cut -d'.' -f2)
    
    if [ "$major_version" -lt 3 ] || ([ "$major_version" -eq 3 ] && [ "$minor_version" -lt 9 ]); then
        print_error "Python 3.9 or higher is required. Found: $python_version"
        exit 1
    fi
    
    print_success "Python $python_version found"
}

# Check if .env file exists
check_env_file() {
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        print_warning ".env file not found. Creating template..."
        cat > "$SCRIPT_DIR/.env" << 'EOF'
# Confluent Cloud Config (Optional - for production)
CONFLUENT_BOOTSTRAP_SERVERS=your-bootstrap-server
CONFLUENT_API_KEY=your-api-key
CONFLUENT_API_SECRET=your-api-secret

# Claude AI Config (Optional - for AI responses)
ANTHROPIC_API_KEY=your-claude-api-key

# App Config
KAFKA_TOPIC_TICKETS=support-tickets
KAFKA_TOPIC_PROCESSED=processed-tickets
KAFKA_TOPIC_RESPONSES=ai-responses

# Demo Config
DEMO_MODE=true
GRADIO_PORT=7860
LOG_LEVEL=INFO
EOF
        print_success "Created .env template file"
        print_warning "Please edit .env file with your actual API keys if needed"
    else
        print_success ".env file exists"
    fi
}

# Create virtual environment
create_venv() {
    print_status "Creating virtual environment..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    if [ $? -eq 0 ]; then
        print_success "Virtual environment created successfully"
    else
        print_error "Failed to create virtual environment"
        exit 1
    fi
}

# Activate virtual environment
activate_venv() {
    print_status "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
    if [ $? -eq 0 ]; then
        print_success "Virtual environment activated"
        # Upgrade pip
        pip install --upgrade pip --quiet
    else
        print_error "Failed to activate virtual environment"
        exit 1
    fi
}

# Install dependencies
install_dependencies() {
    print_status "Installing dependencies..."
    
    # Install from requirements.txt 
    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
        if [ $? -eq 0 ]; then
            print_success "Dependencies installed successfully"
        else
            print_error "Failed to install dependencies"
            exit 1
        fi
    else
        print_error "requirements.txt not found"
        exit 1
    fi
}

# Validate Python imports
validate_imports() {
    print_status "Validating Python imports..."
    
    cd "$SCRIPT_DIR"
    
    # Test critical imports
    $PYTHON_CMD -c "
import sys
sys.path.insert(0, 'src')

try:
    from core.sentiment import SentimentAnalyzer, TicketProcessor
    from streaming.kafka_client import KafkaClient, DemoMessageGenerator  
    from ai.response_generator import AIResponseGenerator
    from ui.dashboard import SentimentDashboard
    print('✅ All imports successful')
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ Validation error: {e}')
    sys.exit(1)
" 2>/dev/null

    if [ $? -eq 0 ]; then
        print_success "All imports validated successfully"
    else
        print_error "Import validation failed"
        exit 1
    fi
}

# Main execution
main() {
    print_banner
    
    # Clean up any previous runs
    cleanup
    
    # Check prerequisites
    print_status "Checking prerequisites..."
    check_python
    check_env_file
    
    # Set up virtual environment
    cleanup_venv
    create_venv
    activate_venv
    
    # Install dependencies
    install_dependencies
    
    # Validate the code
    validate_imports
    
    # Check if we're in demo mode
    if grep -q "DEMO_MODE=true" "$SCRIPT_DIR/.env"; then
        print_status "Running in DEMO MODE (no external APIs required)"
        print_status "The dashboard will simulate customer messages and responses"
    else
        print_status "Running in PRODUCTION MODE"
        print_warning "Make sure your .env file has valid API keys"
    fi
    
    # Launch the application
    print_status "Starting the Real-Time Customer Sentiment Dashboard..."
    print_status "Dashboard will be available at: http://localhost:7860"
    print_status "Press Ctrl+C to stop the application"
    
    echo ""
    echo -e "${GREEN}🎯 READY TO LAUNCH!${NC}"
    echo ""
    
    # Change to script directory
    cd "$SCRIPT_DIR"
    
    # Run the application and capture PID
    $PYTHON_CMD src/main.py &
    local app_pid=$!
    echo $app_pid > "$PID_FILE"
    
    # Wait for the application
    wait $app_pid
    local exit_code=$?
    
    # Clean up PID file
    rm -f "$PID_FILE"
    
    if [ $exit_code -eq 0 ]; then
        print_success "Application completed successfully"
    else
        print_warning "Application exited with code: $exit_code"
    fi
    
    return $exit_code
}

# Parse command line arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h       Show this help message"
        echo "  --clean          Clean up and exit (removes venv, cache, logs)"
        echo "  --check          Check system requirements only"
        echo "  --validate       Validate code imports only"
        echo ""
        echo "Environment Variables (set in .env):"
        echo "  DEMO_MODE=true/false       Run in demo mode (default: true)"
        echo "  GRADIO_PORT=7860           Port for Gradio dashboard"
        echo "  ANTHROPIC_API_KEY=xxx      Claude AI API key (optional)"
        echo "  CONFLUENT_*                Confluent Cloud settings (optional)"
        echo ""
        echo "Demo Features:"
        echo "  • Simulated customer messages"
        echo "  • Real-time sentiment analysis"
        echo "  • AI response generation"
        echo "  • Live dashboard with charts"
        echo "  • Manual message testing"
        echo ""
        echo "Cleanup:"
        echo "  • Removes virtual environment on each run (fresh install)"
        echo "  • Recursively cleans Python cache files (__pycache__, *.pyc, *.pyo)"
        echo "  • Removes build artifacts (build/, dist/, *.egg-info/)"
        echo "  • Cleans testing files (.coverage, .pytest_cache, .mypy_cache)"
        echo "  • Removes log files and temporary files"
        echo "  • Handles Ctrl+C interrupts gracefully"
        exit 0
        ;;
    --clean)
        print_status "Performing deep cleanup..."
        cleanup
        cleanup_venv
        print_success "Deep cleanup completed"
        exit 0
        ;;
    --check)
        print_status "Checking system requirements..."
        check_python
        check_env_file
        print_success "System check complete"
        exit 0
        ;;
    --validate)
        print_status "Validating code structure..."
        check_python
        create_venv
        activate_venv
        install_dependencies
        validate_imports
        cleanup_venv
        print_success "Code validation complete"
        exit 0
        ;;
    "")
        main
        ;;
    *)
        print_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac