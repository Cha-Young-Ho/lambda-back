#!/bin/bash

# Blog System Test Runner
# 전체 테스트 스위트를 실행하는 스크립트

set -e

echo "🧪 Blog System Test Runner"
echo "=========================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running in CI environment
if [ "$CI" = "true" ]; then
    echo "🤖 Running in CI environment"
    PYTEST_ARGS="--tb=short --no-header -q"
else
    echo "🖥️  Running in local environment"
    PYTEST_ARGS="--tb=short -v"
fi

# Function to print status
print_status() {
    echo -e "${BLUE}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check dependencies
print_status "Checking dependencies..."

if ! command -v python3 &> /dev/null; then
    print_error "Python3 is required but not installed"
    exit 1
fi

if ! python3 -c "import pytest" &> /dev/null; then
    print_warning "pytest not found, installing test dependencies..."
    pip3 install -r requirements-test.txt
fi

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)/layers/common-layer/python"
export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test

# Parse command line arguments
TEST_TYPE="all"
COVERAGE="false"
PARALLEL="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            TEST_TYPE="unit"
            shift
            ;;
        --integration)
            TEST_TYPE="integration"
            shift
            ;;
        --coverage)
            COVERAGE="true"
            shift
            ;;
        --parallel)
            PARALLEL="true"
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --unit         Run only unit tests"
            echo "  --integration  Run only integration tests"
            echo "  --coverage     Generate coverage report"
            echo "  --parallel     Run tests in parallel"
            echo "  --help         Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Start test services for integration tests
start_test_services() {
    print_status "Starting test services..."
    
    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        print_warning "Docker not found, skipping service startup"
        return 1
    fi
    
    # Start test services
    cd tests
    # Try docker-compose first, fallback to docker compose
    if command -v docker-compose >/dev/null 2>&1; then
        echo "Using docker-compose"
        docker-compose -f docker-compose.test.yml up -d
    else
        echo "Using docker compose"
        docker compose -f docker-compose.test.yml up -d
    fi
    cd ..
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 10
    
    # Check DynamoDB Local
    if curl -s http://localhost:8001 > /dev/null; then
        print_success "DynamoDB Local is ready"
    else
        print_warning "DynamoDB Local may not be ready"
    fi
    
    # Check LocalStack
    if curl -s http://localhost:4566 > /dev/null; then
        print_success "LocalStack is ready"
    else
        print_warning "LocalStack may not be ready"
    fi
    
    return 0
}

# Stop test services
stop_test_services() {
    print_status "Stopping test services..."
    if [ -f tests/docker-compose.test.yml ]; then
        cd tests
        if command -v docker-compose >/dev/null 2>&1; then
            docker-compose -f docker-compose.test.yml down
        else
            docker compose -f docker-compose.test.yml down
        fi
        cd ..
    fi
}

# Build pytest command
build_pytest_cmd() {
    local cmd="python3 -m pytest"
    
    # Add coverage if requested
    if [ "$COVERAGE" = "true" ]; then
        cmd="$cmd --cov=layers/common-layer/python/common --cov=auth --cov=news --cov=gallery --cov-report=html --cov-report=term-missing"
    fi
    
    # Add parallel execution if requested
    if [ "$PARALLEL" = "true" ]; then
        if python3 -c "import pytest_xdist" &> /dev/null; then
            cmd="$cmd -n auto"
        else
            print_warning "pytest-xdist not installed, running tests sequentially"
        fi
    fi
    
    # Add test markers based on type
    case $TEST_TYPE in
        "unit")
            cmd="$cmd tests/unit/ -m unit"
            ;;
        "integration")
            cmd="$cmd tests/integration/ -m integration"
            ;;
        "all")
            cmd="$cmd tests/"
            ;;
    esac
    
    cmd="$cmd $PYTEST_ARGS"
    echo "$cmd"
}

# Cleanup function
cleanup() {
    print_status "Cleaning up..."
    stop_test_services
}

# Set up cleanup trap
trap cleanup EXIT

# Main execution
main() {
    print_status "Running $TEST_TYPE tests..."
    
    # Start services if running integration tests
    if [ "$TEST_TYPE" = "integration" ] || [ "$TEST_TYPE" = "all" ]; then
        if ! start_test_services; then
            print_warning "Could not start test services, integration tests may fail"
        fi
    fi
    
    # Build and run pytest command
    PYTEST_CMD=$(build_pytest_cmd)
    print_status "Running: $PYTEST_CMD"
    
    if eval "$PYTEST_CMD"; then
        print_success "All tests passed!"
        
        if [ "$COVERAGE" = "true" ]; then
            print_status "Coverage report generated in htmlcov/"
        fi
    else
        print_error "Some tests failed!"
        exit 1
    fi
}

# Run main function
main "$@"
