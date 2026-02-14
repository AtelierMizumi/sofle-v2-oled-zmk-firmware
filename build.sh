#!/bin/bash
# ZMK Build Script for Sofle v2 with nice! OLED
# Usage: ./build.sh [left|right|all|clean]
# Default: build both sides

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
ZEPHYR_SDK="$HOME/zephyr-sdk-0.16.9"
OUTPUT_DIR="$SCRIPT_DIR/firmware"

# Board and shields
BOARD="nice_nano_v2"
SHIELD_LEFT="sofle_left nice_oled"
SHIELD_RIGHT="sofle_right nice_oled"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check dependencies
check_dependencies() {
    log_info "Checking dependencies..."
    
    # Check Python venv
    if [ ! -d "$VENV_DIR" ]; then
        log_error "Python virtual environment not found at $VENV_DIR"
        log_info "Please run: python3 -m venv .venv"
        log_info "Then: source .venv/bin/activate && pip install west pyelftools"
        exit 1
    fi
    
    # Check Zephyr SDK
    if [ ! -d "$ZEPHYR_SDK" ]; then
        log_error "Zephyr SDK not found at $ZEPHYR_SDK"
        log_info "Please download and install Zephyr SDK 0.16.9"
        exit 1
    fi
    
    # Check west workspace
    if [ ! -d "$SCRIPT_DIR/.west" ]; then
        log_warn "West workspace not initialized"
        log_info "Initializing west workspace..."
        source "$VENV_DIR/bin/activate"
        cd "$SCRIPT_DIR"
        west init -l config
        west update
        west zephyr-export
    fi
    
    log_success "All dependencies OK"
}

# Activate environment
activate_env() {
    source "$VENV_DIR/bin/activate"
    export ZEPHYR_SDK_INSTALL_DIR="$ZEPHYR_SDK"
    export PATH="$ZEPHYR_SDK/arm-zephyr-eabi/bin:$PATH"
}

# Create output directory
setup_output() {
    mkdir -p "$OUTPUT_DIR"
    log_info "Output directory: $OUTPUT_DIR"
}

# Build function
build_side() {
    local side=$1
    local shield=$2
    local build_dir="$SCRIPT_DIR/build/$side"
    local uf2_source="$build_dir/zephyr/zmk.uf2"
    local uf2_dest="$OUTPUT_DIR/sofle_${side}_nice_oled.uf2"
    
    log_info "Building $side side..."
    log_info "Shield: $shield"
    log_info "Build directory: $build_dir"
    
    cd "$SCRIPT_DIR"
    
    # Clean build if requested
    if [ "$CLEAN_BUILD" = "true" ]; then
        log_warn "Cleaning build directory: $build_dir"
        rm -rf "$build_dir"
    fi
    
    # Build
    if west build -d "$build_dir" -b "$BOARD" zmk/app -- -DSHIELD="$shield" 2>&1; then
        log_success "Build completed for $side side"
        
        # Copy firmware to output directory
        if [ -f "$uf2_source" ]; then
            cp "$uf2_source" "$uf2_dest"
            log_success "Firmware copied to: $uf2_dest"
            
            # Show file size
            local size=$(ls -lh "$uf2_dest" | awk '{print $5}')
            log_info "Firmware size: $size"
        else
            log_error "UF2 file not found: $uf2_source"
            return 1
        fi
    else
        log_error "Build failed for $side side"
        return 1
    fi
}

# Build left side
build_left() {
    build_side "left" "$SHIELD_LEFT"
}

# Build right side
build_right() {
    build_side "right" "$SHIELD_RIGHT"
}

# Build both sides
build_all() {
    log_info "Building both sides..."
    build_left
    build_right
    log_success "All builds completed!"
}

# Clean build directories
clean_builds() {
    log_warn "Cleaning all build directories..."
    rm -rf "$SCRIPT_DIR/build"
    rm -rf "$OUTPUT_DIR"
    log_success "Clean completed"
}

# Show help
show_help() {
    echo "ZMK Build Script for Sofle v2 with nice! OLED"
    echo ""
    echo "Usage: ./build.sh [OPTION]"
    echo ""
    echo "Options:"
    echo "  left      Build left side firmware only"
    echo "  right     Build right side firmware only"
    echo "  all       Build both sides (default)"
    echo "  clean     Clean all build directories"
    echo "  --clean   Force clean build before compiling"
    echo "  -h, help  Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./build.sh              # Build both sides"
    echo "  ./build.sh left         # Build left side only"
    echo "  ./build.sh right        # Build right side only"
    echo "  ./build.sh --clean      # Clean build both sides"
    echo "  ./build.sh left --clean # Clean build left side"
    echo ""
    echo "Output: firmware/"
    echo "  - sofle_left_nice_oled.uf2"
    echo "  - sofle_right_nice_oled.uf2"
}

# Main
main() {
    echo "============================================"
    echo "  ZMK Build Script - Sofle v2 OLED"
    echo "============================================"
    echo ""
    
    local command="all"
    
    # Parse arguments
    for arg in "$@"; do
        case $arg in
            left|right|all|clean)
                command="$arg"
                ;;
            --clean)
                CLEAN_BUILD="true"
                ;;
            -h|--help|help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $arg"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Execute command
    case $command in
        clean)
            clean_builds
            ;;
        left|right|all)
            check_dependencies
            activate_env
            setup_output
            
            if [ "$command" = "all" ]; then
                build_all
            else
                build_$command
            fi
            
            echo ""
            echo "============================================"
            log_success "Build process completed!"
            echo "============================================"
            echo ""
            echo "Firmware files:"
            ls -lh "$OUTPUT_DIR"/*.uf2 2>/dev/null || echo "No firmware files found"
            echo ""
            echo "To flash:"
            echo "  1. Put nice!nano in bootloader mode (double-tap reset)"
            echo "  2. Copy .uf2 file to the USB drive"
            echo ""
            ;;
    esac
}

# Run main
main "$@"
