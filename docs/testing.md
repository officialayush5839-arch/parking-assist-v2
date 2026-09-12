# Testing Guide

## Test Structure

```
tests/
├── unit/           # Individual module tests
├── integration/    # Pipeline integration tests
├── simulation/     # Full scenario tests
├── performance/    # Benchmarks and latency tests
└── hardware/       # Hardware-specific tests (manual)
```

## Running Tests

```bash
# All tests
python -m pytest --import-mode=importlib -q

# Unit tests only
python -m pytest tests/unit/ -v

# Integration tests
python -m pytest tests/integration/ -v

# Simulation scenario tests
python -m pytest tests/simulation/ -v

# Performance tests
python -m pytest tests/performance/ -v
```

## Safety Tests

The most critical tests verify the safety guarantee:

### Hard Safety Override
- Ultrasonic 0.30m + no vision + LOW ML → CRITICAL
- Proves AI cannot veto hard safety conditions

### Fault Handling
- Both sensors invalid → FAULT
- Camera failure → continues on ultrasonic
- Ultrasonic failure → degrades with vision

### State Transitions
- Object far → SAFE
- Object approaching → CAUTION → WARNING
- Fast approach → CRITICAL
- Both invalid → FAULT

## Self-Test

```bash
python -m app.main --mode selftest
```

Verifies:
- Configuration loads
- Zone thresholds ordered
- TTC kinematics
- Fusion weighted/ultrasonic-only
- Hard override → CRITICAL

## Performance Testing

```bash
python -m tools.benchmark
```

Measures:
- Detector FPS
- Pipeline FPS
- Per-stage latency
- Memory usage
