#!/bin/bash
# ZMK Environment Setup Script with Python Virtual Environment
set -e

echo "Starting ZMK Environment Setup..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# 1. System Dependencies (Arch Linux)
echo "Installing system dependencies (requires sudo)..."
if ! command -v cmake &> /dev/null || ! command -v python3 &> /dev/null; then
    sudo pacman -S --needed --noconfirm \
        git cmake ninja gperf \
        ccache dfu-util dtc wget \
        python python-pip python-virtualenv python-wheel xz file \
        make gcc gcc-libs sdl2 libmagic
else
    echo "Dependencies seemingly installed. Skipping pacman."
fi

# 2. Create and activate Python virtual environment
echo "Setting up Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "Virtual environment created at $VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# 3. Install Python Dependencies
echo "Installing west and zephyr dependencies..."
pip install west pyelftools

# 4. Initialize West Workspace (if not already done)
if [ ! -d "$SCRIPT_DIR/.west" ]; then
    echo "Initializing west workspace..."
    cd "$SCRIPT_DIR"
    west init -l config
    west update
    west zephyr-export
fi

# 5. Install Zephyr SDK
SDK_VERSION="0.16.9"
SDK_DIR="$HOME/zephyr-sdk-${SDK_VERSION}"
SDK_URL="https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v${SDK_VERSION}/zephyr-sdk-${SDK_VERSION}_linux-x86_64_minimal.tar.xz"

if [ ! -d "$SDK_DIR" ]; then
    echo "Installing Zephyr SDK ${SDK_VERSION}..."
    wget -c -O "$SCRIPT_DIR/zephyr-sdk.tar.xz" "$SDK_URL"
    tar -xf "$SCRIPT_DIR/zephyr-sdk.tar.xz" -C "$HOME"
    rm "$SCRIPT_DIR/zephyr-sdk.tar.xz"
else
    echo "Zephyr SDK found at $SDK_DIR"
fi

# 6. Register SDK and Install Toolchain
echo "Registering SDK and installing ARM toolchain..."
cd "$SDK_DIR"
./setup.sh -t arm-zephyr-eabi -h -c

# 7. Create activation script
cat > "$SCRIPT_DIR/activate_zmk.sh" << 'EOF'
#!/bin/bash
# Source this script to activate ZMK build environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export VIRTUAL_ENV_DISABLE_PROMPT=1
source "$SCRIPT_DIR/.venv/bin/activate"
export ZEPHYR_SDK_INSTALL_DIR="$HOME/zephyr-sdk-0.16.9"
export PATH="$ZEPHYR_SDK_INSTALL_DIR/arm-zephyr-eabi/bin:$PATH"
echo "ZMK environment activated!"
echo "Virtual environment: $SCRIPT_DIR/.venv"
echo "Zephyr SDK: $ZEPHYR_SDK_INSTALL_DIR"
EOF
chmod +x "$SCRIPT_DIR/activate_zmk.sh"

echo ""
echo "============================================"
echo "Setup Complete!"
echo "============================================"
echo ""
echo "To activate the environment, run:"
echo "  source ./activate_zmk.sh"
echo ""
echo "To build firmware, run:"
echo "  west build -d build/left -b nice_nano_v2 -- -DSHIELD='sofle_left nice_oled'"
echo "  west build -d build/right -b nice_nano_v2 -- -DSHIELD='sofle_right nice_oled'"
echo ""
echo "Or use the GitHub Actions build."
