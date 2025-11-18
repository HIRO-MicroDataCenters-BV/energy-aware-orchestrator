#!/bin/bash

# Token test script to verify K8s proxy functionality
# This script tests the token retrieval and proxy health endpoints

set -e

PROXY_URL="http://localhost:3000"
COLORED_OUTPUT=true

# Colors for output
if [ "$COLORED_OUTPUT" = true ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_header() {
    echo ""
    echo "=============================================="
    print_status "$BLUE" "$1"
    echo "=============================================="
}

print_success() {
    print_status "$GREEN" "✅ $1"
}

print_error() {
    print_status "$RED" "❌ $1"
}

print_warning() {
    print_status "$YELLOW" "⚠️  $1"
}

print_info() {
    print_status "$BLUE" "ℹ️  $1"
}

# Function to check if jq is available
check_jq() {
    if ! command -v jq &> /dev/null; then
        print_warning "jq is not installed. JSON responses will be shown raw."
        return 1
    fi
    return 0
}

# Function to make HTTP request and handle response
make_request() {
    local url=$1
    local description=$2
    local expected_status=${3:-200}

    print_info "Testing: $description"
    print_info "URL: $url"

    # Make the request and capture response
    local response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null || echo -e "\nERROR")
    local body=$(echo "$response" | head -n -1)
    local status=$(echo "$response" | tail -n 1)

    if [ "$status" = "ERROR" ]; then
        print_error "Connection failed - is the proxy running?"
        return 1
    fi

    echo "Status Code: $status"

    if [ "$status" -eq "$expected_status" ]; then
        print_success "HTTP Status: $status (Expected: $expected_status)"
    else
        print_error "HTTP Status: $status (Expected: $expected_status)"
    fi

    # Pretty print JSON if jq is available, otherwise show raw
    if check_jq && echo "$body" | jq . >/dev/null 2>&1; then
        echo "Response:"
        echo "$body" | jq .
    else
        echo "Response:"
        echo "$body"
    fi

    echo ""
    return 0
}

# Function to test proxy health
test_health() {
    print_header "Testing Proxy Health Endpoint"
    make_request "$PROXY_URL/health" "Proxy health check"
}

# Function to test token retrieval
test_token() {
    print_header "Testing Token Retrieval"
    make_request "$PROXY_URL/get-token" "K8s token retrieval"
}

# Function to check if proxy is running
check_proxy_running() {
    print_header "Checking if K8s Proxy is Running"

    if curl -s "$PROXY_URL/health" >/dev/null 2>&1; then
        print_success "Proxy is running at $PROXY_URL"
        return 0
    else
        print_error "Proxy is not responding at $PROXY_URL"
        print_info "Make sure to start the proxy with: docker-compose up k8s-proxy"
        return 1
    fi
}

# Function to show environment info
show_environment() {
    print_header "Environment Information"

    if [ -f ".env" ]; then
        print_success ".env file found"
        print_info "Configuration:"
        while IFS= read -r line; do
            # Skip empty lines and comments
            if [[ ! -z "$line" && ! "$line" =~ ^[[:space:]]*# ]]; then
                echo "  $line"
            fi
        done < .env
    else
        print_warning ".env file not found"
        print_info "Create it with: ./scripts/setup-env.sh"
    fi
    echo ""
}

# Function to run all tests
run_all_tests() {
    print_header "K8s Proxy Token Test Suite"

    show_environment

    if check_proxy_running; then
        test_health
        test_token

        print_header "Test Summary"
        print_success "All tests completed"
        print_info "If token retrieval failed, check your .env configuration"
    else
        print_header "Test Summary"
        print_error "Cannot run tests - proxy is not running"
        print_info "Start with: docker-compose up -d k8s-proxy"
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  --health    Test only the health endpoint"
    echo "  --token     Test only the token endpoint"
    echo "  --env       Show environment configuration"
    echo "  --help      Show this help message"
    echo ""
    echo "Without options, runs all tests."
}

# Main script logic
case "${1:-}" in
    --health)
        check_proxy_running && test_health
        ;;
    --token)
        check_proxy_running && test_token
        ;;
    --env)
        show_environment
        ;;
    --help)
        show_usage
        ;;
    "")
        run_all_tests
        ;;
    *)
        print_error "Unknown option: $1"
        show_usage
        exit 1
        ;;
esac
