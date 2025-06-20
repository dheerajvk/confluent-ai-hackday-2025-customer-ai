#!/usr/bin/env python3
"""
Python launcher for the Confluent AI Support Optimizer
Uses venv for dependency isolation and includes comprehensive cleanup
"""
import os
import sys
import subprocess
import shutil
import signal
import atexit
import time
from pathlib import Path

class SentimentOptimizerLauncher:
    def __init__(self):
        self.script_dir = Path(__file__).parent.absolute()
        self.venv_dir = self.script_dir / "venv"
        self.pid_file = self.script_dir / ".app.pid"
        self.cleanup_done = False
        self.app_process = None
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.handle_sigint)
        signal.signal(signal.SIGTERM, self.handle_sigterm)
        atexit.register(self.cleanup)
    
    def print_banner(self):
        """Print application banner"""
        print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║  🚀 CONFLUENT AI SUPPORT OPTIMIZER - PYTHON LAUNCHER                        ║
║                                                                               ║
║  Real-Time Customer Sentiment & Support Optimizer                            ║
║  Built with: Python venv + Confluent + Claude AI + Gradio                   ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
""")
    
    def handle_sigint(self, signum, frame):
        """Handle SIGINT (Ctrl+C)"""
        print("\n⚠️  Received SIGINT (Ctrl+C). Cleaning up...")
        self.cleanup()
        sys.exit(130)
    
    def handle_sigterm(self, signum, frame):
        """Handle SIGTERM"""
        print("\n⚠️  Received SIGTERM. Cleaning up...")
        self.cleanup()
        sys.exit(143)
    
    def cleanup(self):
        """Comprehensive cleanup function"""
        if self.cleanup_done:
            return
        
        print("🧹 Starting cleanup process...")
        
        # Kill the application if it's running
        if self.app_process and self.app_process.poll() is None:
            print(f"🛑 Stopping application (PID: {self.app_process.pid})...")
            try:
                self.app_process.terminate()
                self.app_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("⚠️  Force killing application...")
                self.app_process.kill()
                self.app_process.wait()
        
        # Clean up PID file
        if self.pid_file.exists():
            try:
                pid = int(self.pid_file.read_text().strip())
                try:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(2)
                    os.kill(pid, 0)  # Check if still alive
                    os.kill(pid, signal.SIGKILL)  # Force kill
                except (OSError, ProcessLookupError):
                    pass  # Process already dead
            except (ValueError, FileNotFoundError):
                pass
            
            self.pid_file.unlink(missing_ok=True)
        
        # Clean up Python cache files recursively (enhanced)
        print("🗑️  Cleaning up Python cache files recursively...")
        
        # Remove __pycache__ directories and Python bytecode files
        patterns_to_remove = [
            "**/__pycache__",
            "**/*.pyc", 
            "**/*.pyo",
            "**/*.pyd",
            "**/*.egg-info",
            "**/build",
            "**/dist",
            "**/.coverage",
            "**/.mypy_cache",
            "**/.tox"
        ]
        
        for pattern in patterns_to_remove:
            for path in self.script_dir.glob(pattern):
                try:
                    if path.is_dir():
                        shutil.rmtree(path, ignore_errors=True)
                        print(f"   🗂️  Removed directory: {path.relative_to(self.script_dir)}")
                    else:
                        path.unlink(missing_ok=True)
                        print(f"   📄 Removed file: {path.relative_to(self.script_dir)}")
                except Exception as e:
                    print(f"   ⚠️  Could not remove {path}: {e}")
                    pass
        
        # Clean up log files
        log_file = self.script_dir / "app.log"
        if log_file.exists():
            print("📝 Cleaning up log files...")
            log_file.unlink(missing_ok=True)
        
        # Clean up temporary files
        print("🧽 Cleaning up temporary files...")
        temp_files = [".coverage", "htmlcov", ".pytest_cache"]
        for temp_file in temp_files:
            temp_path = self.script_dir / temp_file
            if temp_path.exists():
                if temp_path.is_dir():
                    shutil.rmtree(temp_path, ignore_errors=True)
                else:
                    temp_path.unlink(missing_ok=True)
        
        self.cleanup_done = True
        print("✅ Cleanup completed")
    
    def cleanup_venv(self):
        """Clean up virtual environment"""
        if self.venv_dir.exists():
            print("🗂️  Removing existing virtual environment...")
            shutil.rmtree(self.venv_dir, ignore_errors=True)
            print("✅ Virtual environment removed")
    
    def check_python(self):
        """Check if Python is available and version is sufficient"""
        python_cmd = None
        
        for cmd in ["python3", "python"]:
            if shutil.which(cmd):
                python_cmd = cmd
                break
        
        if not python_cmd:
            print("❌ Python is not installed or not in PATH")
            return None
        
        # Check Python version
        try:
            result = subprocess.run([python_cmd, "--version"], capture_output=True, text=True)
            version_str = result.stdout.strip().split()[1]
            major, minor = map(int, version_str.split('.')[:2])
            
            if major < 3 or (major == 3 and minor < 9):
                print(f"❌ Python 3.9 or higher is required. Found: {version_str}")
                return None
            
            print(f"✅ Python {version_str} found")
            return python_cmd
            
        except Exception as e:
            print(f"❌ Error checking Python version: {e}")
            return None
    
    def check_env_file(self):
        """Check if .env file exists and create template if not"""
        env_file = self.script_dir / ".env"
        if not env_file.exists():
            print("⚠️  .env file not found. Creating template...")
            env_content = """# Confluent Cloud Config (Optional - for production)
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
"""
            env_file.write_text(env_content)
            print("✅ Created .env template file")
            print("⚠️  Please edit .env file with your actual API keys if needed")
        else:
            print("✅ .env file exists")
        return True
    
    def create_venv(self, python_cmd):
        """Create virtual environment"""
        print("📦 Creating virtual environment...")
        try:
            subprocess.run([python_cmd, "-m", "venv", str(self.venv_dir)], check=True)
            print("✅ Virtual environment created successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create virtual environment: {e}")
            return False
    
    def get_venv_python(self):
        """Get path to Python executable in venv"""
        if os.name == 'nt':  # Windows
            return self.venv_dir / "Scripts" / "python.exe"
        else:  # Unix-like
            return self.venv_dir / "bin" / "python"
    
    def install_dependencies(self):
        """Install dependencies in virtual environment"""
        print("📥 Installing dependencies...")
        
        venv_python = self.get_venv_python()
        
        try:
            # Upgrade pip first
            subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], 
                         check=True, capture_output=True)
            
            # Install from requirements.txt
            requirements_file = self.script_dir / "requirements.txt"
            if requirements_file.exists():
                subprocess.run([str(venv_python), "-m", "pip", "install", "-r", str(requirements_file)], 
                             check=True, capture_output=True)
                print("✅ Dependencies installed successfully")
                return True
            else:
                print("❌ requirements.txt not found")
                return False
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            if e.stderr:
                print(f"Error output: {e.stderr.decode()}")
            return False
    
    def validate_imports(self):
        """Validate Python imports"""
        print("🔍 Validating Python imports...")
        
        venv_python = self.get_venv_python()
        
        test_script = '''
import sys
sys.path.insert(0, "src")

try:
    from core.sentiment import SentimentAnalyzer, TicketProcessor
    from streaming.kafka_client import KafkaClient, DemoMessageGenerator  
    from ai.response_generator import AIResponseGenerator
    from ui.dashboard import SentimentDashboard
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Validation error: {e}")
    sys.exit(1)
'''
        
        try:
            result = subprocess.run([str(venv_python), "-c", test_script], 
                                  check=True, capture_output=True, text=True, 
                                  cwd=str(self.script_dir))
            print("✅ All imports validated successfully")
            return True
        except subprocess.CalledProcessError as e:
            print("❌ Import validation failed")
            if e.stdout:
                print(f"Output: {e.stdout}")
            if e.stderr:
                print(f"Error: {e.stderr}")
            return False
    
    def run_application(self):
        """Run the main application"""
        print("🚀 Starting the Real-Time Customer Sentiment Dashboard...")
        print("📊 Dashboard will be available at: http://localhost:7860")
        print("⚠️  Press Ctrl+C to stop the application")
        
        # Check if we're in demo mode
        env_file = self.script_dir / ".env"
        if env_file.exists():
            content = env_file.read_text()
            if "DEMO_MODE=true" in content:
                print("🎯 Running in DEMO MODE (no external APIs required)")
                print("🎪 The dashboard will simulate customer messages and responses")
            else:
                print("🏭 Running in PRODUCTION MODE")
                print("⚠️  Make sure your .env file has valid API keys")
        
        print()
        print("🎯 READY TO LAUNCH!")
        print()
        
        venv_python = self.get_venv_python()
        main_script = self.script_dir / "src" / "main.py"
        
        try:
            # Start the application
            self.app_process = subprocess.Popen(
                [str(venv_python), str(main_script)],
                cwd=str(self.script_dir)
            )
            
            # Write PID file
            self.pid_file.write_text(str(self.app_process.pid))
            
            # Wait for the application
            exit_code = self.app_process.wait()
            
            # Clean up PID file
            self.pid_file.unlink(missing_ok=True)
            
            if exit_code == 0:
                print("✅ Application completed successfully")
            else:
                print(f"⚠️  Application exited with code: {exit_code}")
            
            return exit_code == 0
            
        except KeyboardInterrupt:
            print("\n🛑 Application stopped by user")
            return True
        except Exception as e:
            print(f"❌ Application failed to start: {e}")
            return False
    
    def main(self):
        """Main launcher function"""
        self.print_banner()
        
        # Clean up any previous runs
        self.cleanup()
        
        # Check prerequisites
        print("🔍 Checking prerequisites...")
        python_cmd = self.check_python()
        if not python_cmd:
            return False
        
        if not self.check_env_file():
            return False
        
        # Set up virtual environment
        self.cleanup_venv()
        if not self.create_venv(python_cmd):
            return False
        
        # Install dependencies
        if not self.install_dependencies():
            return False
        
        # Validate the code
        if not self.validate_imports():
            return False
        
        # Run the application
        return self.run_application()
    
    def check_only(self):
        """Check system requirements only"""
        print("🔍 Checking system requirements...")
        python_cmd = self.check_python()
        if not python_cmd:
            return False
        
        if not self.check_env_file():
            return False
        
        print("✅ System check complete")
        return True
    
    def validate_only(self):
        """Validate code structure only"""
        print("🔍 Validating code structure...")
        python_cmd = self.check_python()
        if not python_cmd:
            return False
        
        if not self.create_venv(python_cmd):
            return False
        
        if not self.install_dependencies():
            return False
        
        if not self.validate_imports():
            return False
        
        self.cleanup_venv()
        print("✅ Code validation complete")
        return True
    
    def clean_only(self):
        """Perform deep cleanup only"""
        print("🧹 Performing deep cleanup...")
        self.cleanup()
        self.cleanup_venv()
        print("✅ Deep cleanup completed")
        return True

def main():
    """Main entry point"""
    launcher = SentimentOptimizerLauncher()
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        if arg in ["--help", "-h"]:
            print("""
Usage: python run.py [options]

Options:
  --help, -h       Show this help message
  --clean          Clean up and exit (removes venv, cache, logs)
  --check          Check system requirements only
  --validate       Validate code imports only

Environment Variables (set in .env):
  DEMO_MODE=true/false       Run in demo mode (default: true)
  GRADIO_PORT=7860           Port for Gradio dashboard  
  ANTHROPIC_API_KEY=xxx      Claude AI API key (optional)
  CONFLUENT_*                Confluent Cloud settings (optional)

Demo Features:
  • Simulated customer messages
  • Real-time sentiment analysis
  • AI response generation
  • Live dashboard with charts
  • Manual message testing

Cleanup:
  • Removes virtual environment on each run
  • Cleans Python cache files (__pycache__, *.pyc)
  • Removes log files and temporary files
  • Handles Ctrl+C interrupts gracefully
""")
            return True
        
        elif arg == "--clean":
            return launcher.clean_only()
        
        elif arg == "--check":
            return launcher.check_only()
        
        elif arg == "--validate":
            return launcher.validate_only()
        
        else:
            print(f"❌ Unknown option: {arg}")
            print("Use --help for usage information")
            return False
    
    # Run the main application
    success = launcher.main()
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)