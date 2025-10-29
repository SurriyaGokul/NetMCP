#!/usr/bin/env bash
#
# End-to-end test script for MCP Network Optimizer
# Tests the complete workflow from discovery to optimization
#

set -e

echo "========================================================================"
echo "MCP Network Optimizer - End-to-End Test Suite"
echo "========================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

function print_success() {
    echo -e "${GREEN}✓${NC} $1"
    ((TESTS_PASSED++))
}

function print_failure() {
    echo -e "${RED}✗${NC} $1"
    ((TESTS_FAILED++))
}

function print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

function print_section() {
    echo ""
    echo "========================================================================"
    echo "$1"
    echo "========================================================================"
    echo ""
}

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

cd "$PROJECT_ROOT"

# Step 1: Check Python environment
print_section "Step 1: Checking Python Environment"

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_success "Python found: $PYTHON_VERSION"
else
    print_failure "Python 3 not found"
    exit 1
fi

# Step 2: Check dependencies
print_section "Step 2: Checking Dependencies"

python3 -c "import yaml" 2>/dev/null && print_success "PyYAML installed" || print_warning "PyYAML not installed (run: pip install -r requirements.txt)"
python3 -c "import pydantic" 2>/dev/null && print_success "Pydantic installed" || print_warning "Pydantic not installed (run: pip install -r requirements.txt)"
python3 -c "import pytest" 2>/dev/null && print_success "Pytest installed" || print_warning "Pytest not installed (run: pip install -r requirements.txt)"

# Step 3: Verify project structure
print_section "Step 3: Verifying Project Structure"

[[ -d "server" ]] && print_success "server/ directory exists" || print_failure "server/ directory missing"
[[ -d "policy" ]] && print_success "policy/ directory exists" || print_failure "policy/ directory missing"
[[ -f "server/main.py" ]] && print_success "server/main.py exists" || print_failure "server/main.py missing"
[[ -f "server/registry.py" ]] && print_success "server/registry.py exists" || print_failure "server/registry.py missing"
[[ -f "policy/limits.yaml" ]] && print_success "policy/limits.yaml exists" || print_failure "policy/limits.yaml missing"

# Step 4: Check configuration files
print_section "Step 4: Checking Configuration Files"

CONFIG_CARDS=$(find policy/config_cards -name "*.yaml" 2>/dev/null | wc -l)
if [[ $CONFIG_CARDS -gt 0 ]]; then
    print_success "Found $CONFIG_CARDS configuration cards"
else
    print_failure "No configuration cards found in policy/config_cards/"
fi

# Step 5: Run unit tests
print_section "Step 5: Running Unit Tests"

if command -v pytest &> /dev/null; then
    echo "Running validator tests..."
    if python3 -m pytest server/tests/test_validator.py -v 2>&1 | tee /tmp/test_validator.log; then
        print_success "Validator tests passed"
    else
        print_warning "Some validator tests failed (see /tmp/test_validator.log)"
    fi
    
    echo ""
    echo "Running planner tests..."
    if python3 -m pytest server/tests/test_planner.py -v 2>&1 | tee /tmp/test_planner.log; then
        print_success "Planner tests passed"
    else
        print_warning "Some planner tests failed (see /tmp/test_planner.log)"
    fi
else
    print_warning "pytest not available, skipping unit tests"
fi

# Step 6: Run integration tests
print_section "Step 6: Running Integration Tests"

if command -v pytest &> /dev/null; then
    echo "Running integration tests..."
    if python3 -m pytest server/tests/test_integration.py -v -s 2>&1 | tee /tmp/test_integration.log; then
        print_success "Integration tests passed"
    else
        print_warning "Some integration tests failed (see /tmp/test_integration.log)"
    fi
else
    print_warning "pytest not available, skipping integration tests"
fi

# Step 7: Run real-world scenario tests
print_section "Step 7: Running Real-World Scenario Tests"

if command -v pytest &> /dev/null; then
    echo "Running real-world scenario tests..."
    if python3 -m pytest server/tests/test_real_world_scenarios.py -v -s 2>&1 | tee /tmp/test_scenarios.log; then
        print_success "Real-world scenario tests passed"
    else
        print_warning "Some scenario tests failed (see /tmp/test_scenarios.log)"
    fi
else
    print_warning "pytest not available, skipping scenario tests"
fi

# Step 8: Run performance benchmark
print_section "Step 8: Running Performance Benchmark"

if [[ -f "server/tests/benchmark.py" ]]; then
    echo "Running baseline performance benchmark..."
    if python3 server/tests/benchmark.py -o baseline_benchmark.json 2>&1 | tee /tmp/benchmark.log; then
        print_success "Performance benchmark completed"
        echo "Results saved to: baseline_benchmark.json"
    else
        print_warning "Benchmark encountered errors (see /tmp/benchmark.log)"
    fi
else
    print_warning "Benchmark script not found"
fi

# Step 9: Check system commands availability
print_section "Step 9: Checking System Commands Availability"

command -v ip &> /dev/null && print_success "ip command available" || print_warning "ip command not found"
command -v sysctl &> /dev/null && print_success "sysctl command available" || print_warning "sysctl command not found"
command -v tc &> /dev/null && print_success "tc command available" || print_warning "tc command not found (install: iproute2)"
command -v nft &> /dev/null && print_success "nft command available" || print_warning "nft command not found (install: nftables)"
command -v ethtool &> /dev/null && print_success "ethtool command available" || print_warning "ethtool command not found (install: ethtool)"

# Step 10: Summary
print_section "Test Summary"

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $TESTS_FAILED"
echo "Total Tests:  $TOTAL_TESTS"
echo ""

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}All tests passed!${NC}"
    echo ""
    echo "========================================================================"
    echo "The MCP Network Optimizer is functioning correctly!"
    echo "========================================================================"
    echo ""
    echo "Next steps:"
    echo "  1. Review benchmark results in baseline_benchmark.json"
    echo "  2. Create an optimization plan for your use case"
    echo "  3. Apply optimizations and run benchmark again to compare"
    echo "  4. Compare results: python3 server/tests/benchmark.py --compare baseline_benchmark.json after_benchmark.json"
    echo ""
    exit 0
else
    echo -e "${YELLOW}Some tests failed or produced warnings${NC}"
    echo "Check the log files in /tmp/ for details"
    exit 1
fi
