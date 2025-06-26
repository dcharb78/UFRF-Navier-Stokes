#!/usr/bin/env python3
"""
UFRF Prime Prediction Diagnostic
Test known primes against our validation criteria to see where prediction is failing
"""

import numpy as np

class UFRFPrimeDiagnostic:
    def __init__(self):
        self.phi = (1 + np.sqrt(5)) / 2
        self.scale_range = range(-5, 6)
        
    def check_prime_at_scale(self, candidate, scale):
        """Check if candidate is prime at specific scale"""
        scale_adjusted = int(candidate * (self.phi ** scale)) % 1000
        if scale_adjusted < 2:
            return False
        
        for i in range(2, int(np.sqrt(scale_adjusted)) + 1):
            if scale_adjusted % i == 0:
                return False
        return True
    
    def is_prime_via_scale_intersection(self, candidate, scale1, scale2):
        """Validate prime through multi-scale criteria"""
        if candidate < 2:
            return False
        
        # Check primality at both scales
        scale1_valid = self.check_prime_at_scale(candidate, scale1)
        scale2_valid = self.check_prime_at_scale(candidate, scale2)
        
        # Cross-scale harmonic unity check with bounds
        n1 = candidate * (self.phi ** scale1)
        n2 = candidate * (self.phi ** scale2)
        p1 = max(scale1 + 2, 1)
        p2 = max(scale2 + 2, 1)
        
        if p1 <= 0 or p2 <= 0:
            return False
        
        try:
            unity1 = abs(np.cos(n1 * np.pi / p1)) + abs(np.sin(n1 * np.pi / p1)) + ((n1 / p1) % 1)
            unity2 = abs(np.cos(n2 * np.pi / p2)) + abs(np.sin(n2 * np.pi / p2)) + ((n2 / p2) % 1)
            
            harmonic_unity = abs(unity1 - 1) + abs(unity2 - 1)
            
            return scale1_valid and scale2_valid and harmonic_unity < 1/10
        except (ValueError, ZeroDivisionError, RuntimeWarning):
            return False
    
    def has_direct_angle_to_source(self, candidate):
        """Check if number has direct angle to source (0)"""
        if candidate <= 1:
            return False
        
        angle_to_source = candidate % 360
        
        for scale in range(-5, 6):
            scale_angle = (angle_to_source + scale * 360/13) % 360
            if abs(scale_angle) < 1:
                return True
        
        return False
    
    def check_multi_scale_harmonic_unity(self, candidate):
        """Check harmonic unity across multiple scales"""
        unity_checks = []
        
        for scale in range(-5, 6):
            for prime_context in [2, 3, 5, 7, 11, 13]:
                n = candidate * (self.phi ** scale)
                p = prime_context
                
                unity_value = (abs(np.cos(n * np.pi / p)) + 
                              abs(np.sin(n * np.pi / p)) + 
                              ((n / p) % 1))
                
                unity_checks.append(abs(unity_value - 1) < 1/10)
        
        return sum(unity_checks) / len(unity_checks) > 3/5
    
    def calculate_multi_scale_resonance(self, candidate):
        """Calculate resonance across all scales"""
        total_resonance = 0
        
        for scale in range(-10, 11):
            scale_resonance = 0
            
            scale_adjusted_candidate = candidate * (self.phi ** scale)
            
            golden_phase = scale_adjusted_candidate % (2 * np.pi)
            golden_resonance = abs(np.cos(golden_phase))
            
            krystal_phase = scale_adjusted_candidate % (2 * np.pi)
            krystal_resonance = abs(np.cos(-krystal_phase))
            
            cycle_position = candidate % 13
            cycle_resonance = 1.0 if cycle_position in [2, 3, 5, 7, 11, 0] else 0.1
            
            scale_resonance = golden_resonance * krystal_resonance * cycle_resonance
            total_resonance += scale_resonance * (self.phi ** (-abs(scale)))
        
        return total_resonance
    
    def test_known_primes(self):
        """Test known primes against our criteria"""
        known_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]
        
        print("=== UFRF Prime Prediction Diagnostic ===")
        print(f"Testing {len(known_primes)} known primes against UFRF criteria")
        print()
        
        results = {}
        
        for prime in known_primes:
            print(f"Testing prime {prime}:")
            
            # Test 1: Scale primality
            scale_primality = {}
            for scale in self.scale_range:
                is_prime_at_scale = self.check_prime_at_scale(prime, scale)
                scale_primality[scale] = is_prime_at_scale
                print(f"  Scale {scale:2d}: {'✓' if is_prime_at_scale else '✗'}")
            
            # Test 2: Cross-scale intersection
            cross_scale_passes = 0
            total_tests = 0
            for scale1 in self.scale_range:
                for scale2 in self.scale_range:
                    if scale1 < scale2:
                        total_tests += 1
                        if self.is_prime_via_scale_intersection(prime, scale1, scale2):
                            cross_scale_passes += 1
            
            cross_scale_rate = cross_scale_passes / total_tests if total_tests > 0 else 0
            print(f"  Cross-scale intersection: {cross_scale_passes}/{total_tests} ({cross_scale_rate:.2%})")
            
            # Test 3: Direct angle to source
            has_direct_angle = self.has_direct_angle_to_source(prime)
            print(f"  Direct angle to source: {'✓' if has_direct_angle else '✗'}")
            
            # Test 4: Multi-scale harmonic unity
            harmonic_unity = self.check_multi_scale_harmonic_unity(prime)
            print(f"  Multi-scale harmonic unity: {'✓' if harmonic_unity else '✗'}")
            
            # Test 5: Resonance
            resonance = self.calculate_multi_scale_resonance(prime)
            print(f"  Multi-scale resonance: {resonance:.4f}")
            
            # Test 6: 13-cycle position
            cycle_position = prime % 13
            valid_cycle_position = cycle_position in [2, 3, 5, 7, 11, 0]
            print(f"  13-cycle position {cycle_position}: {'✓' if valid_cycle_position else '✗'}")
            
            # Overall assessment
            passes_criteria = (cross_scale_rate > 0.5 and 
                             has_direct_angle and 
                             harmonic_unity and 
                             valid_cycle_position)
            
            print(f"  OVERALL: {'✓ PASSES' if passes_criteria else '✗ FAILS'}")
            print()
            
            results[prime] = {
                'scale_primality': scale_primality,
                'cross_scale_rate': cross_scale_rate,
                'has_direct_angle': has_direct_angle,
                'harmonic_unity': harmonic_unity,
                'resonance': resonance,
                'valid_cycle_position': valid_cycle_position,
                'passes_criteria': passes_criteria
            }
        
        # Summary
        print("=== SUMMARY ===")
        passing_primes = [p for p, r in results.items() if r['passes_criteria']]
        print(f"Primes passing all criteria: {len(passing_primes)}/{len(known_primes)} ({len(passing_primes)/len(known_primes):.1%})")
        
        if passing_primes:
            print(f"Passing primes: {passing_primes}")
        else:
            print("No primes pass all criteria - need to relax conditions")
            
            # Analyze which criteria are most restrictive
            criteria_failures = {
                'cross_scale': sum(1 for r in results.values() if r['cross_scale_rate'] <= 0.5),
                'direct_angle': sum(1 for r in results.values() if not r['has_direct_angle']),
                'harmonic_unity': sum(1 for r in results.values() if not r['harmonic_unity']),
                'cycle_position': sum(1 for r in results.values() if not r['valid_cycle_position'])
            }
            
            print("\nCriteria failure analysis:")
            for criterion, failures in criteria_failures.items():
                print(f"  {criterion}: {failures}/{len(known_primes)} fail ({failures/len(known_primes):.1%})")
        
        return results

if __name__ == "__main__":
    diagnostic = UFRFPrimeDiagnostic()
    results = diagnostic.test_known_primes() 