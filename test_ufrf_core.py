#!/usr/bin/env python3
"""
Core UFRF Mathematical Validation
================================
Focused testing of the fundamental mathematical principles
of the Unified Fractal Resonance Framework.
"""

import numpy as np
import matplotlib.pyplot as plt

# Golden ratio constant
PHI = (1 + np.sqrt(5)) / 2

def is_prime(n):
    """Check if a number is prime."""
    if n < 2:
        return False
    for i in range(2, int(np.sqrt(n)) + 1):
        if n % i == 0:
            return False
    return True

def get_primes_up_to(n):
    """Get all prime numbers up to n."""
    return [i for i in range(2, n + 1) if is_prime(i)]

def harmonic_unity(n, p):
    """
    Calculate harmonic unity value U_p(n).
    U_p(n) = |cos(nπ/p)| + |sin(nπ/p)| + (n/p mod 1)
    """
    cos_term = abs(np.cos(n * np.pi / p))
    sin_term = abs(np.sin(n * np.pi / p))
    mod_term = (n / p) % 1
    return cos_term + sin_term + mod_term

def cross_scale_unity(k, p, s1, s2):
    """
    Calculate cross-scale unity value using only ratios of φ (never arbitrary decimals).
    For n = k * p * φ^s1 at scale s1, p = p * φ^s2 at scale s2:
    U_cross = φ^|s1-s2| * (|cos(ratio * π)| + |sin(ratio * π)| + (ratio % 1))
    where ratio = k * φ^{s1-s2}
    """
    ratio = k * PHI**(s1 - s2)
    cos_term = abs(np.cos(ratio * np.pi))
    sin_term = abs(np.sin(ratio * np.pi))
    mod_term = ratio % 1
    return PHI**abs(s1 - s2) * (cos_term + sin_term + mod_term)

def interference_factor(s1, s2):
    """
    Calculate cross-scale interference factor I(s1, s2).
    I(s1,s2) = φ^|s1-s2| * cos(2π(s1-s2)/13) * exp(i*π(s1+s2)/7)
    """
    scale_diff = abs(s1 - s2)
    phase_13 = np.cos(2 * np.pi * (s1 - s2) / 13)
    phase_7 = np.exp(1j * np.pi * (s1 + s2) / 7)
    return PHI**(-scale_diff) * phase_13 * phase_7  # Note: negative exponent for decay

def compute_s_matrix(scales):
    """
    Compute the Scale Synchronization Matrix.
    S[i,j] = φ^|i-j| * exp(2πi(i-j)/13) * δ(phase_alignment)
    """
    n = len(scales)
    S = np.zeros((n, n), dtype=complex)
    
    for i, s1 in enumerate(scales):
        for j, s2 in enumerate(scales):
            if abs(s1 - s2) % 13 == 0:  # Phase alignment condition
                S[i, j] = PHI**abs(s1 - s2) * np.exp(2j * np.pi * (s1 - s2) / 13)
    
    return S

def test_harmonic_unity():
    """Test the harmonic unity principle."""
    print("Testing Harmonic Unity Principle...")
    
    primes = get_primes_up_to(20)
    errors = []
    
    for p in primes:
        # Test harmonic series H_p = {kp : k ∈ ℕ}
        for k in range(1, 21):
            n = k * p
            unity = harmonic_unity(n, p)
            error = abs(unity - 1.0)
            errors.append(error)
            
            if error > 1e-10:
                print(f"  Warning: Large error for n={n}, p={p}: {error:.2e}")
    
    mean_error = np.mean(errors)
    max_error = np.max(errors)
    
    print(f"  Mean error: {mean_error:.2e}")
    print(f"  Max error: {max_error:.2e}")
    print(f"  Success rate: {100 * (np.array(errors) < 1e-10).mean():.1f}%")
    
    return mean_error < 1e-10

def test_cross_scale_unity():
    """Test cross-scale unity relationships at harmonic nodes using only ratios of φ."""
    print("\nTesting Cross-Scale Unity at harmonic nodes (ratios only)...")
    
    p = 7  # Test prime
    scale_range = range(-3, 4)
    ks = [1, 2, 3, 5, 8, 13]  # Fibonacci numbers as example k values
    errors = []
    
    for s1 in scale_range:
        for s2 in scale_range:
            if s1 != s2:
                for k in ks:
                    # n = k * p * φ^s1 at scale s1, p * φ^s2 at scale s2
                    expected = PHI**abs(s2 - s1)
                    actual = cross_scale_unity(k, p, s1, s2)
                    error = abs(actual - expected)
                    errors.append(error)
                    if error > 1e-10:
                        print(f"  Warning: Large error for s1={s1}, s2={s2}, k={k}: {error:.2e}")
    
    mean_error = np.mean(errors)
    max_error = np.max(errors)
    
    print(f"  Mean error (harmonic nodes): {mean_error:.2e}")
    print(f"  Max error (harmonic nodes): {max_error:.2e}")
    
    return mean_error < 1e-10

def test_s_matrix_properties():
    """Test S-matrix mathematical properties."""
    print("\nTesting S-Matrix Properties...")
    
    scales = list(range(-2, 3))
    S = compute_s_matrix(scales)
    
    # Test Hermiticity
    is_hermitian = np.allclose(S, S.conj().T)
    print(f"  Hermitian: {is_hermitian}")
    
    # Test eigenvalues on unit circle
    eigenvals = np.linalg.eigvals(S)
    eigenvals_magnitude = np.abs(eigenvals)
    on_unit_circle = np.allclose(eigenvals_magnitude, 1.0, atol=1e-10)
    print(f"  Eigenvalues on unit circle: {on_unit_circle}")
    
    # Test 13-cycle property
    S_13 = np.linalg.matrix_power(S, 13)
    thirteen_cycle = np.allclose(S_13, np.eye(len(scales)), atol=1e-10)
    print(f"  13-cycle property: {thirteen_cycle}")
    
    return is_hermitian and on_unit_circle and thirteen_cycle

def test_interference_factor():
    """Test cross-scale interference factor properties."""
    print("\nTesting Interference Factor...")
    
    scale_range = range(-3, 4)
    properties_ok = True
    
    for s1 in scale_range:
        for s2 in scale_range:
            I = interference_factor(s1, s2)
            
            # Test symmetry: I(s1,s2) = I(s2,s1)*
            I_conj = interference_factor(s2, s1)
            if not np.allclose(I, I_conj.conj(), atol=1e-10):
                print(f"  Symmetry violation: I({s1},{s2}) != I({s2},{s1})*")
                print(f"    I({s1},{s2}) = {I}")
                print(f"    I({s2},{s1})* = {I_conj.conj()}")
                properties_ok = False
            
            # Test decay property: |I(s1,s2)| ≤ φ^(-|s1-s2|)
            expected_decay = PHI**(-abs(s1 - s2))
            if abs(I) > expected_decay + 1e-10:
                print(f"  Decay violation: |I({s1},{s2})| = {abs(I):.6f} > φ^(-|{s1}-{s2}|) = {expected_decay:.6f}")
                properties_ok = False
    
    print(f"  All properties satisfied: {properties_ok}")
    return properties_ok

def test_golden_ratio_properties():
    """Test fundamental golden ratio properties."""
    print("\nTesting Golden Ratio Properties...")
    
    # Test φ² = φ + 1
    phi_squared = PHI**2
    phi_plus_one = PHI + 1
    golden_identity = abs(phi_squared - phi_plus_one) < 1e-15
    print(f"  φ² = φ + 1: {golden_identity}")
    
    # Test scale relationships
    scale_relationships_ok = True
    for s in range(-3, 4):
        phi_s = PHI**s
        phi_neg_s = PHI**(-s)
        if abs(phi_s * phi_neg_s - 1.0) > 1e-15:
            print(f"  Scale relationship violation at s={s}")
            scale_relationships_ok = False
    
    print(f"  Scale relationships: {scale_relationships_ok}")
    
    return golden_identity and scale_relationships_ok

def test_prime_distribution():
    """Test prime number distribution properties."""
    print("\nTesting Prime Distribution...")
    
    primes = get_primes_up_to(100)
    
    # Test prime gaps
    gaps = [primes[i+1] - primes[i] for i in range(len(primes)-1)]
    avg_gap = np.mean(gaps)
    expected_gap = np.log(50)  # Approximate average gap around 50
    
    gap_ratio = avg_gap / expected_gap
    gap_ok = 0.5 < gap_ratio < 2.0  # Reasonable range
    
    print(f"  Average prime gap: {avg_gap:.3f}")
    print(f"  Expected gap (ln(50)): {expected_gap:.3f}")
    print(f"  Gap ratio: {gap_ratio:.3f}")
    print(f"  Gap distribution reasonable: {gap_ok}")
    
    return gap_ok

def main():
    """Run all core UFRF tests."""
    print("=" * 60)
    print("UFRF Core Mathematical Validation")
    print("=" * 60)
    
    tests = [
        ("Golden Ratio Properties", test_golden_ratio_properties),
        ("Harmonic Unity", test_harmonic_unity),
        ("Cross-Scale Unity", test_cross_scale_unity),
        ("S-Matrix Properties", test_s_matrix_properties),
        ("Interference Factor", test_interference_factor),
        ("Prime Distribution", test_prime_distribution),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"  Error in {test_name}: {e}")
            results[test_name] = False
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed ({100*passed/total:.1f}%)")
    
    if passed == total:
        print("\n🎉 All core UFRF mathematical principles validated!")
    else:
        print(f"\n⚠️  {total-passed} test(s) failed - review required")
    
    return results

if __name__ == "__main__":
    results = main() 