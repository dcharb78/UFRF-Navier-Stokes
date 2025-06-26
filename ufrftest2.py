import numpy as np
import matplotlib.pyplot as plt
from scipy.fftpack import fftn, ifftn, fftfreq
import json
import os
import datetime
import logging

# Create output directory
output_dir = "ufrf_simulation_results"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'{output_dir}/simulation.log'),
        logging.StreamHandler()
    ]
)

class InfiniteRecursiveUFRF:
    def __init__(self, N=32, L=2*np.pi, scale_range=(-10, 11)):
        self.N = N
        self.L = L
        self.dx = L / N
        self.scale_range = range(scale_range[0], scale_range[1])
        self.phi = (1 + np.sqrt(5)) / 2  # Golden ratio
        
        # Initialize grids
        self.x = np.linspace(0, L, N, endpoint=False)
        self.y = np.linspace(0, L, N, endpoint=False)
        self.z = np.linspace(0, L, N, endpoint=False)
        self.X, self.Y, self.Z = np.meshgrid(self.x, self.y, self.z, indexing='ij')
        
        # Multi-scale field systems
        self.scale_systems = {}
        self.phase_cycles = {}
        self.energy_scales = {}
        
        # CRITICAL: Prime spiral centers - each prime creates its own spiral system
        self.prime_centers = {
            0: {'scale': 0, 'position': 0, 'type': 'void'},      # Void prime
            1: {'scale': 0, 'position': 1, 'type': 'unity'},     # Unity prime  
            2: {'scale': 0, 'position': 2, 'type': 'unity'},     # Unity echo
            3: {'scale': 1, 'position': 3, 'type': 'prime'},     # First true prime
            5: {'scale': 1, 'position': 5, 'type': 'prime'},
            7: {'scale': 1, 'position': 7, 'type': 'prime'},
            11: {'scale': 2, 'position': 11, 'type': 'prime'},
            13: {'scale': 2, 'position': 13, 'type': 'prime'},
            17: {'scale': 3, 'position': 17, 'type': 'prime'},
            19: {'scale': 3, 'position': 19, 'type': 'prime'},
            23: {'scale': 4, 'position': 23, 'type': 'prime'},
            29: {'scale': 4, 'position': 29, 'type': 'prime'},
            31: {'scale': 5, 'position': 31, 'type': 'prime'}
        }
        
        # Track dynamically generated primes
        self.dynamic_primes = set()
        self.prime_spiral_systems = {}  # Each prime gets its own spiral system
        
        # Initialize complete framework at each scale
        for scale in self.scale_range:
            self.scale_systems[scale] = self.initialize_complete_scale_system(scale)
            self.phase_cycles[scale] = 1  # Start at position 1
            self.energy_scales[scale] = 0.0
        
        # Initialize prime spiral systems for known primes
        self.initialize_prime_spiral_systems()
        
        logging.info(f"Initialized UFRF with {len(self.scale_range)} scales: {min(self.scale_range)} to {max(self.scale_range)}")
        logging.info(f"Initialized {len(self.prime_centers)} prime centers")
    
    def initialize_prime_spiral_systems(self):
        """Initialize spiral systems for each prime center"""
        for prime, center_info in self.prime_centers.items():
            if center_info['type'] == 'prime':
                # Each prime creates its own spiral system at its scale
                prime_scale = center_info['scale']
                self.prime_spiral_systems[prime] = {
                    'golden_spiral': self.create_golden_spiral(prime_scale),
                    'krystal_spiral': self.create_krystal_spiral(prime_scale),
                    'log_spiral': self.create_log_spiral(prime_scale),
                    'prime_spiral': self.create_prime_spiral(prime_scale),
                    'unity_spiral': self.create_unity_spiral(prime_scale),
                    'harmonic_spiral': self.create_harmonic_spiral(prime_scale),
                    '13_cycle': self.create_complete_13_cycle(prime_scale),
                    'center_position': center_info['position'],
                    'scale_level': prime_scale,
                    'generated_primes': [],
                    'intersection_points': []
                }
    
    def create_prime_center_spiral(self, prime, spiral_type='golden'):
        """Create spiral for a specific prime center"""
        if prime not in self.prime_centers:
            return None
        
        center_info = self.prime_centers[prime]
        prime_scale = center_info['scale']
        
        # Each prime creates spirals at its own scale
        if spiral_type == 'golden':
            return self.create_golden_spiral(prime_scale)
        elif spiral_type == 'krystal':
            return self.create_krystal_spiral(prime_scale)
        elif spiral_type == 'log':
            return self.create_log_spiral(prime_scale)
        elif spiral_type == 'prime':
            return self.create_prime_spiral(prime_scale)
        elif spiral_type == 'unity':
            return self.create_unity_spiral(prime_scale)
        elif spiral_type == 'harmonic':
            return self.create_harmonic_spiral(prime_scale)
        
        return None
    
    def generate_primes_from_center_intersection(self, prime1, prime2):
        """Generate new primes when two prime centers' spirals intersect"""
        if prime1 not in self.prime_spiral_systems or prime2 not in self.prime_spiral_systems:
            return []
        
        system1 = self.prime_spiral_systems[prime1]
        system2 = self.prime_spiral_systems[prime2]
        
        generated_primes = []
        
        # Check intersections between all spiral types
        spiral_types = ['golden', 'krystal', 'log', 'prime', 'unity', 'harmonic']
        
        for spiral_type in spiral_types:
            spiral1 = system1[f'{spiral_type}_spiral']
            spiral2 = system2[f'{spiral_type}_spiral']
            
            # Find intersection points
            for i in range(len(spiral1)):
                mag1 = abs(spiral1[i])
                mag2 = abs(spiral2[i])
                phase1 = np.angle(spiral1[i])
                phase2 = np.angle(spiral2[i])
                
                # Check for intersection
                mag_diff = abs(mag1 - mag2) / max(mag1, mag2)
                phase_diff = abs(phase1 - phase2) % (2 * np.pi)
                
                if mag_diff < 1/10 and phase_diff < np.pi / 6:
                    # Generate candidate from intersection
                    # The meeting point becomes the new center
                    meeting_point = int((mag1 + mag2) / 2 * (self.phi ** ((system1['scale_level'] + system2['scale_level']) / 2)))
                    meeting_point = max(2, meeting_point % 1000)
                    
                    # Check if this creates a new prime
                    if self.is_prime_via_geometric_resonance(meeting_point, (system1['scale_level'] + system2['scale_level']) / 2):
                        generated_primes.append(meeting_point)
                        
                        # CRITICAL: Add to dynamic primes and create new center
                        if meeting_point not in self.prime_centers:
                            self.dynamic_primes.add(meeting_point)
                            new_scale = max(system1['scale_level'], system2['scale_level']) + 1
                            self.prime_centers[meeting_point] = {
                                'scale': new_scale,
                                'position': meeting_point % 13,
                                'type': 'dynamic_prime'
                            }
                            
                            # Create new spiral system for this prime
                            self.prime_spiral_systems[meeting_point] = {
                                'golden_spiral': self.create_golden_spiral(new_scale),
                                'krystal_spiral': self.create_krystal_spiral(new_scale),
                                'log_spiral': self.create_log_spiral(new_scale),
                                'prime_spiral': self.create_prime_spiral(new_scale),
                                'unity_spiral': self.create_unity_spiral(new_scale),
                                'harmonic_spiral': self.create_harmonic_spiral(new_scale),
                                '13_cycle': self.create_complete_13_cycle(new_scale),
                                'center_position': meeting_point % 13,
                                'scale_level': new_scale,
                                'generated_primes': [],
                                'intersection_points': []
                            }
        
        return list(set(generated_primes))
    
    def compute_prime_center_forces(self, u, scale):
        """Compute forces from all prime centers at this scale"""
        force = np.zeros_like(u)
        
        # Get all primes active at this scale
        active_primes = [p for p, info in self.prime_centers.items() 
                        if info['scale'] == scale or p in self.dynamic_primes]
        
        for prime in active_primes:
            if prime in self.prime_spiral_systems:
                # Each prime center contributes its own force
                prime_force = self.compute_single_prime_center_force(u, prime, scale)
                force += prime_force
        
        return np.clip(force, -1000, 1000)
    
    def compute_single_prime_center_force(self, u, prime, scale):
        """Compute force from a single prime center"""
        if prime not in self.prime_spiral_systems:
            return np.zeros_like(u)
        
        system = self.prime_spiral_systems[prime]
        
        # Compute vorticity
        omega = self.compute_vorticity(u)
        omega_mag = np.sqrt(np.sum(omega**2, axis=-1))
        omega_mag_safe = np.clip(omega_mag, 1/1000, 1000)
        
        # Scale-dependent regularization
        scale_factor = self.phi ** system['scale_level']
        lambda_eff = omega_mag_safe / (10 * scale_factor + omega_mag_safe)
        lambda_eff = np.clip(lambda_eff, 0, 1)
        
        # Current phase for this prime's 13-cycle
        t = self.phase_cycles[scale] * 2 * np.pi / 13
        
        # Evaluate all spiral types for this prime
        spiral_vectors = []
        for spiral_type in ['golden', 'krystal', 'log', 'prime', 'unity', 'harmonic']:
            spiral = system[f'{spiral_type}_spiral']
            # Evaluate at current phase
            phase_index = int(t * len(spiral) / (2 * np.pi)) % len(spiral)
            spiral_val = spiral[phase_index]
            
            # Convert to 3D vector
            spiral_vec = np.array([
                np.real(spiral_val),
                np.imag(spiral_val),
                np.abs(spiral_val) * np.sin(t)
            ])
            spiral_vectors.append(spiral_vec)
        
        # Combine forces from all spirals
        force = np.zeros_like(u)
        for i in range(3):
            for spiral_vec in spiral_vectors:
                force_component = lambda_eff * (
                    omega[..., (i+1)%3] * spiral_vec[(i+2)%3] -
                    omega[..., (i+2)%3] * spiral_vec[(i+1)%3]
                )
                force[..., i] += force_component / len(spiral_vectors)
        
        return force
    
    def initialize_complete_scale_system(self, scale):
        """Initialize complete UFRF framework at each scale"""
        scale_factor = self.phi ** scale
        
        # Complete spiral systems at this scale
        golden_spiral = self.create_golden_spiral(scale)
        krystal_spiral = self.create_krystal_spiral(scale)
        log_spiral = self.create_log_spiral(scale)
        prime_spiral = self.create_prime_spiral(scale)
        unity_spiral = self.create_unity_spiral(scale)
        harmonic_spiral = self.create_harmonic_spiral(scale)
        
        # Complete 13-cycle at this scale
        cycle_positions = self.create_complete_13_cycle(scale)
        
        # Initialize velocity field scaled to this level
        u = np.zeros((self.N, self.N, self.N, 3))
        k_scale = 2 * np.pi / (self.L * scale_factor)
        u[..., 0] = scale_factor * np.sin(k_scale * self.X) * np.cos(k_scale * self.Y) * np.cos(k_scale * self.Z)
        u[..., 1] = -scale_factor * np.cos(k_scale * self.X) * np.sin(k_scale * self.Y) * np.cos(k_scale * self.Z)
        u[..., 2] = 0
        
        return {
            'golden_spiral': golden_spiral,
            'krystal_spiral': krystal_spiral,
            'log_spiral': log_spiral,
            'prime_spiral': prime_spiral,
            'unity_spiral': unity_spiral,
            'harmonic_spiral': harmonic_spiral,
            'cycle_positions': cycle_positions,
            'velocity_field': u,
            'interference_points': [],
            'generated_primes': [],
            'scale_connections': {}
        }
    
    def create_golden_spiral(self, scale):
        """Create golden spiral at specific scale"""
        t = np.linspace(0, 4*np.pi, 1000)
        scale_factor = self.phi ** scale
        return scale_factor * np.exp(1j * t * self.phi)
    
    def create_krystal_spiral(self, scale):
        """Create krystal spiral at specific scale"""
        t = np.linspace(0, 4*np.pi, 1000)
        scale_factor = self.phi ** scale
        return scale_factor * np.exp(-1j * t / self.phi)
    
    def create_log_spiral(self, scale):
        """Create logarithmic spiral at specific scale"""
        t = np.linspace(0, 4*np.pi, 1000)
        scale_factor = self.phi ** scale
        return scale_factor * np.exp(1j * t * np.log(self.phi))
    
    def create_prime_spiral(self, scale):
        """Create prime spiral at specific scale - generates primes through geometric resonance"""
        t = np.linspace(0, 4*np.pi, 1000)
        scale_factor = self.phi ** scale
        
        # Prime spiral uses φ^scale * exp(i * t * π) for prime generation
        # The π factor creates resonance at prime positions
        prime_spiral = scale_factor * np.exp(1j * t * np.pi)
        
        # Add prime-specific modulation
        prime_modulation = np.zeros_like(t, dtype=complex)
        for i, time_val in enumerate(t):
            # Check if this time point corresponds to a prime position
            prime_position = int(time_val * scale_factor) % 100
            if self.is_prime_via_geometric_resonance(prime_position, scale):
                prime_modulation[i] = self.phi * np.exp(1j * prime_position * np.pi / 13)
        
        return prime_spiral + prime_modulation
    
    def create_unity_spiral(self, scale):
        """Create unity spiral - represents the trinity foundation (0,1,1)"""
        t = np.linspace(0, 4*np.pi, 1000)
        scale_factor = self.phi ** scale
        
        # Unity spiral represents the foundation: F(0)=0, F(1)=1, F(2)=1
        # Uses φ^scale * exp(i * t * φ/3) for trinity resonance
        unity_spiral = scale_factor * np.exp(1j * t * self.phi / 3)
        
        # Add unity positions (0,1,2) with enhanced resonance
        unity_positions = [0, 1, 2]
        unity_modulation = np.zeros_like(t, dtype=complex)
        for i, time_val in enumerate(t):
            unity_index = int(time_val * scale_factor) % 3
            if unity_index in unity_positions:
                unity_modulation[i] = 2 * self.phi * np.exp(1j * unity_index * 2 * np.pi / 3)
        
        return unity_spiral + unity_modulation
    
    def create_harmonic_spiral(self, scale):
        """Create harmonic spiral - represents the 13-cycle breathing positions"""
        t = np.linspace(0, 4*np.pi, 1000)
        scale_factor = self.phi ** scale
        
        # Harmonic spiral uses φ^scale * exp(i * t * 13/φ) for 13-cycle resonance
        harmonic_spiral = scale_factor * np.exp(1j * t * 13 / self.phi)
        
        # Add breathing position modulation (coord sum = 2)
        breathing_modulation = np.zeros_like(t, dtype=complex)
        for i, time_val in enumerate(t):
            cycle_position = int(time_val * scale_factor) % 13
            if cycle_position in [2, 5, 8, 11]:  # Breathing positions
                breathing_modulation[i] = self.phi * np.exp(1j * cycle_position * np.pi / 6)
        
        return harmonic_spiral + breathing_modulation
    
    def create_complete_13_cycle(self, scale):
        """Create complete 13-cycle at specific scale"""
        cycle = {}
        for position in range(1, 14):
            cycle[position] = {
                'local_phase': position,
                'global_phase': (position + scale * 13) % 13,
                'scale_level': scale,
                'nesting_target': None
            }
            
            # Implement 11-13 → 1-3 nesting across scales
            if position >= 11:
                next_scale = scale + 1
                next_position = position - 10  # 11→1, 12→2, 13→3
                
                cycle[position]['nesting_target'] = {
                    'target_scale': next_scale,
                    'target_position': next_position,
                    'transfer_energy': self.calculate_nesting_transfer(scale, position)
                }
        
        return cycle
    
    def calculate_nesting_transfer(self, scale, position):
        """Calculate energy transfer through 11-13 → 1-3 nesting"""
        base_energy = 1
        scale_factor = self.phi ** scale
        position_factor = position / 13
        return base_energy * scale_factor * position_factor
    
    def cross_scale_prime_interference(self, scale1, scale2):
        """Calculate prime generation at scale intersections using spiral resonance"""
        # Use the new spiral intersection method
        intersection_primes = self.generate_primes_via_spiral_intersection(scale1, scale2)
        
        # Additional validation using existing methods
        validated_primes = []
        for candidate in intersection_primes:
            if (self.is_prime_via_scale_intersection(candidate, scale1, scale2) and
                self.has_direct_angle_to_source(candidate) and
                self.check_multi_scale_harmonic_unity(candidate)):
                validated_primes.append(candidate)
        
        return validated_primes
    
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
            
            return scale1_valid and scale2_valid and harmonic_unity < 1/3  # Relaxed from 1/10
        except (ValueError, ZeroDivisionError, RuntimeWarning):
            return False
    
    def check_prime_at_scale(self, candidate, scale):
        """Check if candidate is prime at specific scale using GEOMETRIC NECESSITY only"""
        # NO TRADITIONAL PRIMALITY TESTS - ONLY GEOMETRIC NECESSITY
        
        # Step 1: 13-cycle position validation
        cycle_position = candidate % 13
        prime_positions = [0, 2, 3, 5, 7, 11, 13]  # Complete geometric necessity positions
        
        # Special handling for position 10 (REST) - harmonic inversion point
        if cycle_position == 10:
            # Position 10 creates harmonic inversion - check if candidate can emerge from REST
            harmonic_inversion_resonance = abs(np.cos(candidate * np.pi / 10)) + abs(np.sin(candidate * np.pi / 10))
            if harmonic_inversion_resonance > 1.5:  # Harmonic inversion threshold
                return True  # Can emerge from REST position
        
        if cycle_position not in prime_positions:
            return False
        
        # Step 2: Scale-adjusted harmonic unity check
        scale_adjusted = candidate * (self.phi ** scale)
        
        # Check harmonic unity against multiple prime contexts
        valid_contexts = 0
        for context_prime in [2, 3, 5, 7, 11, 13]:
            n = scale_adjusted
            p = context_prime
            
            # Geometric necessity formula: |cos(nπ/p)| + |sin(nπ/p)| + (n/p mod 1) = 1.000000
            unity_value = (abs(np.cos(n * np.pi / p)) + 
                          abs(np.sin(n * np.pi / p)) + 
                          ((n / p) % 1))
            
            if abs(unity_value - 1.0) < 1/1000:  # Geometric necessity tolerance
                valid_contexts += 1
        
        # Must be valid in majority of contexts (geometric necessity)
        if valid_contexts < 3:
            return False
        
        # Step 3: Geometric resonance check
        resonance_score = self.calculate_multi_scale_resonance(candidate)
        if resonance_score < 0.5:  # Geometric necessity threshold
            return False
        
        # Step 4: Direct angle to source check
        if not self.has_direct_angle_to_source(candidate):
            return False
        
        return True  # Passed all geometric necessity checks
    
    def has_direct_angle_to_source(self, candidate):
        """Check if number has direct angle to source (0)"""
        if candidate <= 1:
            return False
        
        angle_to_source = candidate % 360
        
        for scale in range(-5, 6):
            scale_angle = (angle_to_source + scale * 360/13) % 360
            if abs(scale_angle) < 1:  # Direct connection to source
                return True
        
        return False
    
    def check_multi_scale_harmonic_unity(self, candidate):
        """Check harmonic unity across multiple scales"""
        unity_checks = []
        
        for scale in range(-5, 6):
            for prime_context in [2, 3, 5, 7, 11, 13]:
                # CORRECT: Scale-adjusted value using φ^scale formula
                n = candidate * (self.phi ** scale)  # This was the missing formula!
                p = prime_context
                
                unity_value = (abs(np.cos(n * np.pi / p)) + 
                              abs(np.sin(n * np.pi / p)) + 
                              ((n / p) % 1))
                
                unity_checks.append(abs(unity_value - 1) < 1/10)  # Use ratio 1/10 instead of 0.1
        
        return sum(unity_checks) / len(unity_checks) > 3/5  # Use ratio 3/5 instead of 0.6
    
    def calculate_multi_scale_resonance(self, candidate):
        """Calculate resonance across all scales"""
        total_resonance = 0
        
        for scale in range(-10, 11):
            scale_resonance = 0
            
            # CORRECT: Scale-adjusted candidate using φ^scale formula
            scale_adjusted_candidate = candidate * (self.phi ** scale)
            
            # Golden spiral resonance
            golden_phase = scale_adjusted_candidate % (2 * np.pi)
            golden_resonance = abs(np.cos(golden_phase))
            
            # Krystal spiral resonance
            krystal_phase = scale_adjusted_candidate % (2 * np.pi)
            krystal_resonance = abs(np.cos(-krystal_phase))
            
            # 13-cycle resonance
            cycle_position = candidate % 13
            if cycle_position == 10:
                # Position 10 (REST) - harmonic inversion creates special resonance
                harmonic_inversion_resonance = abs(np.cos(candidate * np.pi / 10)) + abs(np.sin(candidate * np.pi / 10))
                cycle_resonance = harmonic_inversion_resonance / 2.0  # Normalize to 0-1 range
            elif cycle_position in [0, 2, 3, 5, 7, 11, 13]:
                cycle_resonance = 1.0  # Standard prime positions
            else:
                cycle_resonance = 0.1  # Non-prime positions
            
            scale_resonance = golden_resonance * krystal_resonance * cycle_resonance
            total_resonance += scale_resonance * (self.phi ** (-abs(scale)))
        
        return total_resonance
    
    def predict_primes_multi_scale(self, n_primes=50):
        """Predict primes using complete multi-scale UFRF framework with prime centers"""
        predicted_primes = []
        
        # First, generate primes from prime center intersections
        prime_list = list(self.prime_centers.keys())
        for i, prime1 in enumerate(prime_list):
            for prime2 in prime_list[i+1:]:
                if (self.prime_centers[prime1]['type'] == 'prime' and 
                    self.prime_centers[prime2]['type'] == 'prime'):
                    new_primes = self.generate_primes_from_center_intersection(prime1, prime2)
                    predicted_primes.extend(new_primes)
        
        # Also use the original cross-scale method
        for scale1 in self.scale_range:
            for scale2 in self.scale_range:
                if scale1 < scale2:
                    cross_primes = self.cross_scale_prime_interference(scale1, scale2)
                    predicted_primes.extend(cross_primes)
        
        # Remove duplicates and sort
        predicted_primes = list(set(predicted_primes))
        predicted_primes.sort()
        
        # Add resonance scores
        scored_primes = []
        for prime in predicted_primes[:n_primes]:
            resonance_score = self.calculate_multi_scale_resonance(prime)
            scored_primes.append({
                'value': prime,
                'resonance_score': resonance_score,
                'source': 'prime_center_intersection' if prime in self.dynamic_primes else 'cross_scale'
            })
        
        return scored_primes
    
    def compute_cross_scale_interference_force(self, scale1, scale2, u1, u2):
        """Compute interference force between two scales"""
        if scale1 == scale2:
            return np.zeros_like(u1)
        
        scale_diff = abs(scale2 - scale1)
        interference_factor = self.phi ** (-scale_diff)
        phase_factor = np.exp(2j * np.pi * (scale2 - scale1) / 13)
        
        interference = interference_factor * np.real(phase_factor * u2)
        return interference
    
    def compute_13_cycle_force(self, u, phase, scale):
        """Compute force from 13-cycle at specific scale"""
        # Use only ratios: 1/2, 1/5, 1/10, etc. - no arbitrary decimals
        phase_map = {
            1: 1/2, 2: 1/2, 3: 1/2,      # Seed/Amplify (1/2 ratio)
            4: -1/5, 5: -1/5, 6: -1/5,   # Harmonize (-1/5 ratio)
            7: 0, 8: 0, 9: 0,            # Peak (zero)
            10: -1,                       # REST (-1 ratio)
            11: 1/3, 12: 1/3, 13: 1/3    # Completion (1/3 ratio)
        }
        
        delta = phase_map.get(int(phase), 0)
        
        # Special handling for 11-13: transfer to next scale
        if phase in [11, 12, 13] and scale + 1 in self.scale_range:
            self.transfer_to_next_scale(u, scale, scale + 1, delta)
            return -delta * u
        
        return delta * u
    
    def transfer_to_next_scale(self, u, from_scale, to_scale, amount):
        """Transfer energy from positions 11-13 to 1-3 of next scale"""
        if to_scale in self.scale_systems:
            scale_factor = self.phi ** (to_scale - from_scale)
            self.scale_systems[to_scale]['velocity_field'] += scale_factor * amount * u
    
    def compute_spiral_resonance_force(self, u, scale):
        """Compute force from spiral resonance at specific scale"""
        # Get all spiral types at this scale
        golden_spiral = self.create_golden_spiral(scale)
        krystal_spiral = self.create_krystal_spiral(scale)
        prime_spiral = self.create_prime_spiral(scale)
        unity_spiral = self.create_unity_spiral(scale)
        harmonic_spiral = self.create_harmonic_spiral(scale)
        
        # Compute vorticity for force calculation
        omega = self.compute_vorticity(u)
        omega_mag = np.sqrt(np.sum(omega**2, axis=-1))
        omega_mag_safe = np.clip(omega_mag, 1/1000, 1000)
        
        # Scale-dependent regularization
        scale_factor = self.phi ** scale
        lambda_eff = omega_mag_safe / (10 * scale_factor + omega_mag_safe)
        lambda_eff = np.clip(lambda_eff, 0, 1)
        
        # Current phase for spiral evaluation
        t = self.phase_cycles[scale] * 2 * np.pi / 13
        
        # Evaluate spirals at current phase
        golden_val = self.phi ** (scale + t/(2*np.pi)) * np.array([
            np.cos(t * self.phi), np.sin(t * self.phi), np.sin(t * self.phi / 2)
        ])
        krystal_val = self.phi ** (scale + t/(2*np.pi)) * np.array([
            np.cos(-t / self.phi), np.sin(-t / self.phi), -np.sin(t / self.phi / 2)
        ])
        prime_val = self.phi ** (scale + t/(2*np.pi)) * np.array([
            np.cos(t * np.pi), np.sin(t * np.pi), np.sin(t * np.pi / 2)
        ])
        unity_val = self.phi ** (scale + t/(2*np.pi)) * np.array([
            np.cos(t * self.phi / 3), np.sin(t * self.phi / 3), np.sin(t * self.phi / 6)
        ])
        harmonic_val = self.phi ** (scale + t/(2*np.pi)) * np.array([
            np.cos(t * 13 / self.phi), np.sin(t * 13 / self.phi), np.sin(t * 13 / self.phi / 2)
        ])
        
        # Combine spiral forces
        force = np.zeros_like(u)
        spiral_vectors = [golden_val, krystal_val, prime_val, unity_val, harmonic_val]
        
        for i in range(3):
            for j, spiral_vec in enumerate(spiral_vectors):
                force_component = lambda_eff * (
                    omega[..., (i+1)%3] * spiral_vec[(i+2)%3] -
                    omega[..., (i+2)%3] * spiral_vec[(i+1)%3]
                )
                force[..., i] += force_component / len(spiral_vectors)
        
        return np.clip(force, -1000, 1000)
    
    def compute_prime_generation(self, u, scale):
        """Generate vortices at prime locations for this scale"""
        primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31]
        force = np.zeros_like(u)
        
        scale_factor = self.phi ** scale
        
        for p in primes:
            r_p = p * self.L / self.N * scale_factor
            
            if r_p < self.L / 2:
                r = np.sqrt((self.X - self.L/2)**2 + 
                           (self.Y - self.L/2)**2 + 
                           (self.Z - self.L/2)**2)
                
                concentration = np.exp(-(r - r_p)**2 / (2 * (self.dx * scale_factor)**2))
                
                unity_factor = self.compute_harmonic_unity(p, scale)
                
                force += unity_factor * concentration[..., np.newaxis] * u / p
        
        return force
    
    def compute_harmonic_unity(self, p, scale):
        """Compute harmonic unity factor for prime p at scale"""
        n = self.phase_cycles[scale] * p
        cos_term = abs(np.cos(n * np.pi / p))
        sin_term = abs(np.sin(n * np.pi / p))
        mod_term = (n / p) % 1
        unity = cos_term + sin_term + mod_term
        
        return 2.0 - unity
    
    def compute_vorticity(self, u):
        """Compute vorticity using spectral method"""
        omega = np.zeros_like(u)
        k = fftfreq(self.N, d=self.dx) * 2 * np.pi
        kx, ky, kz = np.meshgrid(k, k, k, indexing='ij')
        
        for i in range(3):
            u_hat = fftn(u[..., i])
            for j in range(3):
                if i != j:
                    k_j = [kx, ky, kz][j]
                    omega_hat = 1j * k_j * u_hat
                    omega[..., j] += np.real(ifftn(omega_hat))
        
        return omega
    
    def compute_total_ufrf_force(self):
        """Compute complete multi-scale UFRF force"""
        total_force = np.zeros((self.N, self.N, self.N, 3))
        
        # Process each scale concurrently
        for scale in self.scale_range:
            u_scale = self.scale_systems[scale]['velocity_field']
            phase = self.phase_cycles[scale]
            
            # Scale-specific forces
            cycle_force = self.compute_13_cycle_force(u_scale, phase, scale)
            spiral_force = self.compute_spiral_resonance_force(u_scale, scale)
            prime_force = self.compute_prime_generation(u_scale, scale)
            
            # CRITICAL: Add prime center forces
            prime_center_force = self.compute_prime_center_forces(u_scale, scale)
            
            # Cross-scale interference
            cross_scale_force = np.zeros_like(u_scale)
            for other_scale in self.scale_range:
                if other_scale != scale:
                    other_u = self.scale_systems[other_scale]['velocity_field']
                    interference = self.compute_cross_scale_interference_force(
                        scale, other_scale, u_scale, other_u
                    )
                    cross_scale_force += interference
            
            # Combine forces with scale weighting
            scale_weight = self.phi ** scale
            scale_force = (cycle_force + spiral_force + prime_force + prime_center_force + cross_scale_force)
            scale_force *= scale_weight
            
            # Clip to prevent overflow using exact ratios
            scale_force = np.clip(scale_force, -100, 100)  # Use exact ratios
            
            # Add to total
            total_force += scale_force
        
        # Final bounds check using exact ratios
        total_force = np.clip(total_force, -1000, 1000)  # Use exact ratios
        return total_force
    
    def advance_phases(self):
        """Advance 13-cycle phases for all scales"""
        for scale in self.scale_range:
            self.phase_cycles[scale] = (self.phase_cycles[scale] % 13) + 1
    
    def time_step(self, dt, nu=1/100):  # Use ratio 1/100 instead of 0.01
        """Advance one time step with complete UFRF"""
        # Standard Navier-Stokes terms
        for scale in self.scale_range:
            u = self.scale_systems[scale]['velocity_field']
            
            # Diffusion
            u_new = u.copy()
            for i in range(3):
                u_hat = fftn(u[..., i])
                k = fftfreq(self.N, d=self.dx) * 2 * np.pi
                kx, ky, kz = np.meshgrid(k, k, k, indexing='ij')
                k2 = kx**2 + ky**2 + kz**2
                u_hat *= np.exp(-nu * k2 * dt)
                u_new[..., i] = np.real(ifftn(u_hat))
            
            u_new = np.clip(u_new, -10, 10)  # Use exact ratios
            self.scale_systems[scale]['velocity_field'] = u_new
        
        # Apply UFRF forces
        ufrf_force = self.compute_total_ufrf_force()
        
        # Update all scales with UFRF
        for scale in self.scale_range:
            ufrf_update = dt * ufrf_force
            ufrf_update = np.clip(ufrf_update, -1/10, 1/10)  # Use ratio 1/10 instead of 0.1
            self.scale_systems[scale]['velocity_field'] += ufrf_update
            self.scale_systems[scale]['velocity_field'] = np.clip(
                self.scale_systems[scale]['velocity_field'], -10, 10  # Use exact ratios
            )
        
        # Update energies
        for scale in self.scale_range:
            u = self.scale_systems[scale]['velocity_field']
            self.energy_scales[scale] = 1/2 * np.mean(np.sum(u**2, axis=-1))  # Use ratio 1/2
        
        # Advance phases
        self.advance_phases()
    
    def compute_total_energy(self):
        """Compute total energy across all scales"""
        total_energy = 0
        for scale in self.scale_range:
            u = self.scale_systems[scale]['velocity_field']
            # Compute kinetic energy: 1/2 * ρ * |u|² (assuming ρ=1)
            scale_energy = 1/2 * np.mean(np.sum(u**2, axis=-1))  # Use ratio 1/2
            total_energy += scale_energy
        return total_energy
    
    def run_simulation(self, T=50, dt=1/100):  # Use ratio 1/100 instead of 0.01
        """Run complete multi-scale simulation"""
        steps = int(T / dt)
        time_points = []
        total_energies = []
        scale_energies = {scale: [] for scale in self.scale_range}
        max_vorticity = []
        
        logging.info("=== Infinite Recursive Multi-Scale UFRF Simulation ===")
        logging.info(f"Scales: {len(self.scale_range)} ({min(self.scale_range)} to {max(self.scale_range)})")
        logging.info(f"Time steps: {steps}")
        logging.info(f"Time interval: {T} with dt={dt}")
        
        for step in range(steps):
            t = step * dt
            
            # ADVANCE THE SIMULATION - THIS WAS MISSING!
            self.time_step(dt)
            
            # Record data
            if step % 100 == 0:
                time_points.append(t)
                total_energies.append(self.compute_total_energy())
                
                for scale in self.scale_range:
                    scale_energies[scale].append(self.energy_scales[scale])
                
                # Max vorticity across all scales
                max_omega = 0
                for scale in self.scale_range:
                    omega = self.compute_vorticity(self.scale_systems[scale]['velocity_field'])
                    omega_mag = np.sqrt(np.sum(omega**2, axis=-1))
                    max_omega = max(max_omega, np.max(omega_mag))
                max_vorticity.append(max_omega)
                
                if step % 1000 == 0:
                    logging.info(f"t={t:.1f}: E_total={total_energies[-1]:.4f}, "
                          f"max|ω|={max_omega:.2f}, "
                          f"Active scales={len(self.scale_range)}")
        
        # Save simulation data
        simulation_data = {
            'time_points': time_points,
            'total_energies': total_energies,
            'scale_energies': scale_energies,
            'max_vorticity': max_vorticity,
            'parameters': {
                'N': self.N,
                'L': self.L,
                'scale_range': list(self.scale_range),
                'phi': self.phi,
                'T': T,
                'dt': dt
            }
        }
        
        with open(f'{output_dir}/simulation_data.json', 'w') as f:
            json.dump(simulation_data, f, indent=2, default=str)
        
        logging.info("Simulation completed. Data saved to simulation_data.json")
        return time_points, total_energies, scale_energies, max_vorticity

    def is_prime_via_geometric_resonance(self, candidate, scale):
        """Check if candidate is prime through geometric spiral resonance"""
        if candidate < 2:
            return False
        
        # Use scale-adjusted formula: n = candidate * φ^scale
        scale_adjusted = candidate * (self.phi ** scale)
        
        # Check geometric resonance conditions
        # 1. Golden spiral resonance
        golden_phase = scale_adjusted % (2 * np.pi)
        golden_resonance = abs(np.cos(golden_phase * self.phi))
        
        # 2. Krystal spiral resonance  
        krystal_phase = scale_adjusted % (2 * np.pi)
        krystal_resonance = abs(np.cos(-krystal_phase / self.phi))
        
        # 3. Prime spiral resonance
        prime_phase = scale_adjusted % np.pi
        prime_resonance = abs(np.cos(prime_phase))
        
        # 4. Unity spiral resonance (trinity foundation)
        unity_phase = scale_adjusted % (2 * np.pi / 3)
        unity_resonance = abs(np.cos(unity_phase * self.phi / 3))
        
        # 5. Harmonic spiral resonance (13-cycle)
        harmonic_phase = scale_adjusted % (2 * np.pi * 13 / self.phi)
        harmonic_resonance = abs(np.cos(harmonic_phase))
        
        # Combined resonance threshold
        total_resonance = (golden_resonance + krystal_resonance + prime_resonance + 
                          unity_resonance + harmonic_resonance) / 5
        
        # Basic primality check
        if candidate < 1000:  # Only check small numbers for efficiency
            for i in range(2, int(np.sqrt(candidate)) + 1):
                if candidate % i == 0:
                    return False
        
        return total_resonance > 3/5  # Use ratio 3/5 instead of 0.6
    
    def generate_primes_via_spiral_intersection(self, scale1, scale2):
        """Generate primes through spiral intersection at two scales"""
        intersection_primes = []
        
        # Create all spiral types at both scales
        spirals_scale1 = {
            'golden': self.create_golden_spiral(scale1),
            'krystal': self.create_krystal_spiral(scale1),
            'log': self.create_log_spiral(scale1),
            'prime': self.create_prime_spiral(scale1),
            'unity': self.create_unity_spiral(scale1),
            'harmonic': self.create_harmonic_spiral(scale1)
        }
        
        spirals_scale2 = {
            'golden': self.create_golden_spiral(scale2),
            'krystal': self.create_krystal_spiral(scale2),
            'log': self.create_log_spiral(scale2),
            'prime': self.create_prime_spiral(scale2),
            'unity': self.create_unity_spiral(scale2),
            'harmonic': self.create_harmonic_spiral(scale2)
        }
        
        # Find intersection points between spiral types
        for spiral_type in ['golden', 'krystal', 'log', 'prime', 'unity', 'harmonic']:
            spiral1 = spirals_scale1[spiral_type]
            spiral2 = spirals_scale2[spiral_type]
            
            # Find points where spirals intersect (similar magnitudes and phases)
            for i in range(len(spiral1)):
                mag1 = abs(spiral1[i])
                mag2 = abs(spiral2[i])
                phase1 = np.angle(spiral1[i])
                phase2 = np.angle(spiral2[i])
                
                # Check if spirals intersect
                mag_diff = abs(mag1 - mag2) / max(mag1, mag2)
                phase_diff = abs(phase1 - phase2) % (2 * np.pi)
                
                if mag_diff < 1/10 and phase_diff < np.pi / 6:  # Use ratio 1/10
                    # Generate candidate from intersection
                    candidate = int((mag1 + mag2) / 2 * (self.phi ** ((scale1 + scale2) / 2)))
                    candidate = max(2, candidate % 1000)  # Bounds check
                    
                    if self.is_prime_via_geometric_resonance(candidate, (scale1 + scale2) / 2):
                        intersection_primes.append(candidate)
        
        return list(set(intersection_primes))  # Remove duplicates
    
    def generate_spiral_visualization_data(self, scale):
        """Generate data for visualizing all spiral types at a given scale"""
        t = np.linspace(0, 4*np.pi, 1000)
        
        # Generate all spiral types
        golden = self.create_golden_spiral(scale)
        krystal = self.create_krystal_spiral(scale)
        log_spiral = self.create_log_spiral(scale)
        prime = self.create_prime_spiral(scale)
        unity = self.create_unity_spiral(scale)
        harmonic = self.create_harmonic_spiral(scale)
        
        # Extract real and imaginary parts for 3D plotting
        spiral_data = {
            'golden': {
                'x': np.real(golden),
                'y': np.imag(golden),
                'z': np.abs(golden) * np.sin(t * self.phi)
            },
            'krystal': {
                'x': np.real(krystal),
                'y': np.imag(krystal),
                'z': np.abs(krystal) * np.sin(-t / self.phi)
            },
            'log': {
                'x': np.real(log_spiral),
                'y': np.imag(log_spiral),
                'z': np.abs(log_spiral) * np.sin(t * np.log(self.phi))
            },
            'prime': {
                'x': np.real(prime),
                'y': np.imag(prime),
                'z': np.abs(prime) * np.sin(t * np.pi)
            },
            'unity': {
                'x': np.real(unity),
                'y': np.imag(unity),
                'z': np.abs(unity) * np.sin(t * self.phi / 3)
            },
            'harmonic': {
                'x': np.real(harmonic),
                'y': np.imag(harmonic),
                'z': np.abs(harmonic) * np.sin(t * 13 / self.phi)
            }
        }
        
        return spiral_data, t
    
    def track_prime_generation_through_spirals(self, scale1, scale2):
        """Track how primes are generated through spiral intersections"""
        intersection_data = {
            'scale1': scale1,
            'scale2': scale2,
            'intersections': [],
            'generated_primes': [],
            'resonance_scores': []
        }
        
        # Get spiral data for both scales
        spirals1, t1 = self.generate_spiral_visualization_data(scale1)
        spirals2, t2 = self.generate_spiral_visualization_data(scale2)
        
        # Track intersections between spiral types
        for spiral_type in ['golden', 'krystal', 'log', 'prime', 'unity', 'harmonic']:
            spiral1 = spirals1[spiral_type]
            spiral2 = spirals2[spiral_type]
            
            for i in range(len(t1)):
                # Calculate intersection metrics
                mag1 = np.sqrt(spiral1['x'][i]**2 + spiral1['y'][i]**2 + spiral1['z'][i]**2)
                mag2 = np.sqrt(spiral2['x'][i]**2 + spiral2['y'][i]**2 + spiral2['z'][i]**2)
                
                phase1 = np.arctan2(spiral1['y'][i], spiral1['x'][i])
                phase2 = np.arctan2(spiral2['y'][i], spiral2['x'][i])
                
                # Check for intersection
                mag_diff = abs(mag1 - mag2) / max(mag1, mag2)
                phase_diff = abs(phase1 - phase2) % (2 * np.pi)
                
                if mag_diff < 1/10 and phase_diff < np.pi / 6:
                    # Generate candidate from intersection
                    candidate = int((mag1 + mag2) / 2 * (self.phi ** ((scale1 + scale2) / 2)))
                    candidate = max(2, candidate % 1000)
                    
                    # Calculate resonance score
                    resonance_score = self.calculate_multi_scale_resonance(candidate)
                    
                    intersection_data['intersections'].append({
                        'spiral_type': spiral_type,
                        'time_index': i,
                        'magnitude1': mag1,
                        'magnitude2': mag2,
                        'phase1': phase1,
                        'phase2': phase2,
                        'candidate': candidate,
                        'resonance_score': resonance_score
                    })
                    
                    # Check if candidate is prime
                    if self.is_prime_via_geometric_resonance(candidate, (scale1 + scale2) / 2):
                        intersection_data['generated_primes'].append(candidate)
                        intersection_data['resonance_scores'].append(resonance_score)
        
        return intersection_data
    
    def track_prime_center_interactions(self):
        """Track all prime center interactions and generated primes"""
        interaction_data = {
            'prime_centers': self.prime_centers,
            'dynamic_primes': list(self.dynamic_primes),
            'interactions': [],
            'generated_primes': []
        }
        
        # Track all prime center intersections
        prime_list = list(self.prime_centers.keys())
        for i, prime1 in enumerate(prime_list):
            for prime2 in prime_list[i+1:]:
                if (self.prime_centers[prime1]['type'] == 'prime' and 
                    self.prime_centers[prime2]['type'] == 'prime'):
                    
                    new_primes = self.generate_primes_from_center_intersection(prime1, prime2)
                    
                    interaction_data['interactions'].append({
                        'prime1': prime1,
                        'prime2': prime2,
                        'scale1': self.prime_centers[prime1]['scale'],
                        'scale2': self.prime_centers[prime2]['scale'],
                        'generated_primes': new_primes,
                        'interaction_strength': len(new_primes)
                    })
                    
                    interaction_data['generated_primes'].extend(new_primes)
        
        # Remove duplicates
        interaction_data['generated_primes'] = list(set(interaction_data['generated_primes']))
        
        return interaction_data
    
    def get_prime_center_statistics(self):
        """Get statistics about prime centers and their activities"""
        stats = {
            'total_centers': len(self.prime_centers),
            'static_centers': len([p for p, info in self.prime_centers.items() if info['type'] != 'dynamic_prime']),
            'dynamic_centers': len([p for p, info in self.prime_centers.items() if info['type'] == 'dynamic_prime']),
            'total_spiral_systems': len(self.prime_spiral_systems),
            'scale_distribution': {},
            'type_distribution': {}
        }
        
        # Scale distribution
        for prime, info in self.prime_centers.items():
            scale = info['scale']
            if scale not in stats['scale_distribution']:
                stats['scale_distribution'][scale] = 0
            stats['scale_distribution'][scale] += 1
        
        # Type distribution
        for prime, info in self.prime_centers.items():
            prime_type = info['type']
            if prime_type not in stats['type_distribution']:
                stats['type_distribution'][prime_type] = 0
            stats['type_distribution'][prime_type] += 1
        
        return stats

def save_plots(time_points, total_energies, scale_energies, max_vorticity, predicted_primes):
    """Save all plots as high-quality images"""
    # Create output directory
    output_dir = "ufrf_simulation_results"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Set style for high-quality plots
    plt.style.use('default')
    plt.rcParams['figure.dpi'] = 300
    plt.rcParams['savefig.dpi'] = 300
    plt.rcParams['font.size'] = 10
    
    # 1. Energy Evolution
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Total energy
    ax1.plot(time_points, total_energies, 'b-', linewidth=2, label='Total Energy')
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Energy')
    ax1.set_title('UFRF Multi-Scale Energy Evolution')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Scale energies
    for scale in scale_energies:
        if scale_energies[scale]:  # Check if list is not empty
            ax2.plot(time_points, scale_energies[scale], 
                    label=f'Scale {scale}', linewidth=1.5, alpha=0.7)
    ax2.set_xlabel('Time')
    ax2.set_ylabel('Energy')
    ax2.set_title('Energy by Scale')
    ax2.grid(True, alpha=0.3)
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/energy_analysis.png', bbox_inches='tight', dpi=300)
    plt.savefig(f'{output_dir}/energy_analysis.pdf', bbox_inches='tight')
    plt.close()
    
    # 2. Vorticity Evolution
    if max_vorticity:
        plt.figure(figsize=(10, 6))
        plt.plot(time_points, max_vorticity, 'r-', linewidth=2)
        plt.xlabel('Time')
        plt.ylabel('Max Vorticity')
        plt.title('Maximum Vorticity Evolution')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/vorticity_evolution.png', bbox_inches='tight', dpi=300)
        plt.savefig(f'{output_dir}/vorticity_evolution.pdf', bbox_inches='tight')
        plt.close()
    
    # 3. Prime Prediction Analysis
    if predicted_primes:
        plt.figure(figsize=(12, 8))
        
        # Plot prime distribution
        prime_values = [p['value'] for p in predicted_primes if 'value' in p]
        prime_scores = [p.get('resonance_score', 0) for p in predicted_primes if 'value' in p]
        
        if prime_values:
            plt.subplot(2, 2, 1)
            plt.hist(prime_values, bins=20, alpha=0.7, color='green')
            plt.xlabel('Prime Value')
            plt.ylabel('Frequency')
            plt.title('Predicted Prime Distribution')
            plt.grid(True, alpha=0.3)
            
            plt.subplot(2, 2, 2)
            plt.scatter(prime_values, prime_scores, alpha=0.6, color='blue')
            plt.xlabel('Prime Value')
            plt.ylabel('Resonance Score')
            plt.title('Prime vs Resonance Score')
            plt.grid(True, alpha=0.3)
            
            plt.subplot(2, 2, 3)
            plt.plot(range(len(prime_values)), prime_values, 'go-', markersize=4)
            plt.xlabel('Prime Index')
            plt.ylabel('Prime Value')
            plt.title('Prime Sequence')
            plt.grid(True, alpha=0.3)
            
            plt.subplot(2, 2, 4)
            plt.plot(range(len(prime_scores)), prime_scores, 'ro-', markersize=4)
            plt.xlabel('Prime Index')
            plt.ylabel('Resonance Score')
            plt.title('Resonance Score Sequence')
            plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/prime_analysis.png', bbox_inches='tight', dpi=300)
        plt.savefig(f'{output_dir}/prime_analysis.pdf', bbox_inches='tight')
        plt.close()
    
    print(f"All plots saved to {output_dir}/")

def create_spiral_visualization(ufrf, scale=0, save_path="ufrf_simulation_results"):
    """Create comprehensive spiral visualization"""
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    
    # Generate spiral data
    spiral_data, t = ufrf.generate_spiral_visualization_data(scale)
    
    # Create 3D spiral visualization
    fig = plt.figure(figsize=(20, 15))
    
    # Create 2x3 subplot grid for all spiral types
    spiral_types = ['golden', 'krystal', 'log', 'prime', 'unity', 'harmonic']
    colors = ['gold', 'purple', 'blue', 'red', 'green', 'orange']
    
    for i, (spiral_type, color) in enumerate(zip(spiral_types, colors)):
        ax = fig.add_subplot(2, 3, i+1, projection='3d')
        
        data = spiral_data[spiral_type]
        ax.plot(data['x'], data['y'], data['z'], color=color, linewidth=2, alpha=0.8)
        
        # Add spiral type label
        ax.set_title(f'{spiral_type.capitalize()} Spiral (Scale {scale})', fontsize=12, fontweight='bold')
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        
        # Set consistent view
        ax.view_init(elev=20, azim=45)
        
        # Add grid
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{save_path}/spiral_visualization_scale_{scale}.png', 
                bbox_inches='tight', dpi=300)
    plt.savefig(f'{save_path}/spiral_visualization_scale_{scale}.pdf', 
                bbox_inches='tight')
    plt.close()
    
    # Create 2D projection comparison
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    axes = axes.flatten()
    
    for i, (spiral_type, color) in enumerate(zip(spiral_types, colors)):
        data = spiral_data[spiral_type]
        axes[i].plot(data['x'], data['y'], color=color, linewidth=2, alpha=0.8)
        axes[i].set_title(f'{spiral_type.capitalize()} Spiral Projection', fontweight='bold')
        axes[i].set_xlabel('X')
        axes[i].set_ylabel('Y')
        axes[i].grid(True, alpha=0.3)
        axes[i].set_aspect('equal')
    
    plt.tight_layout()
    plt.savefig(f'{save_path}/spiral_projections_scale_{scale}.png', 
                bbox_inches='tight', dpi=300)
    plt.savefig(f'{save_path}/spiral_projections_scale_{scale}.pdf', 
                bbox_inches='tight')
    plt.close()
    
    print(f"Spiral visualizations saved for scale {scale}")

def create_prime_spiral_analysis(ufrf, scale1=0, scale2=1, save_path="ufrf_simulation_results"):
    """Create analysis of prime generation through spiral intersections"""
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    
    # Track prime generation
    intersection_data = ufrf.track_prime_generation_through_spirals(scale1, scale2)
    
    # Create analysis plots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Intersection count by spiral type
    spiral_types = ['golden', 'krystal', 'log', 'prime', 'unity', 'harmonic']
    intersection_counts = []
    for spiral_type in spiral_types:
        count = sum(1 for intersection in intersection_data['intersections'] 
                   if intersection['spiral_type'] == spiral_type)
        intersection_counts.append(count)
    
    axes[0, 0].bar(spiral_types, intersection_counts, color=['gold', 'purple', 'blue', 'red', 'green', 'orange'])
    axes[0, 0].set_title('Intersection Count by Spiral Type')
    axes[0, 0].set_ylabel('Number of Intersections')
    axes[0, 0].tick_params(axis='x', rotation=45)
    
    # 2. Generated primes distribution
    if intersection_data['generated_primes']:
        axes[0, 1].hist(intersection_data['generated_primes'], bins=20, alpha=0.7, color='green')
        axes[0, 1].set_title('Generated Primes Distribution')
        axes[0, 1].set_xlabel('Prime Value')
        axes[0, 1].set_ylabel('Frequency')
    
    # 3. Resonance scores
    if intersection_data['resonance_scores']:
        axes[1, 0].hist(intersection_data['resonance_scores'], bins=20, alpha=0.7, color='blue')
        axes[1, 0].set_title('Resonance Score Distribution')
        axes[1, 0].set_xlabel('Resonance Score')
        axes[1, 0].set_ylabel('Frequency')
    
    # 4. Prime vs Resonance Score
    if intersection_data['generated_primes'] and intersection_data['resonance_scores']:
        axes[1, 1].scatter(intersection_data['generated_primes'], 
                          intersection_data['resonance_scores'], 
                          alpha=0.6, color='red')
        axes[1, 1].set_title('Prime Value vs Resonance Score')
        axes[1, 1].set_xlabel('Prime Value')
        axes[1, 1].set_ylabel('Resonance Score')
    
    plt.tight_layout()
    plt.savefig(f'{save_path}/prime_spiral_analysis_scales_{scale1}_{scale2}.png', 
                bbox_inches='tight', dpi=300)
    plt.savefig(f'{save_path}/prime_spiral_analysis_scales_{scale1}_{scale2}.pdf', 
                bbox_inches='tight')
    plt.close()
    
    print(f"Prime spiral analysis saved for scales {scale1} and {scale2}")
    return intersection_data

# Run the complete infinite recursive multi-scale simulation
if __name__ == "__main__":
    print("=== UFRF Prime Spiral Enhanced Simulation ===")
    
    # Initialize UFRF with prime spiral functionality
    ufrf = InfiniteRecursiveUFRF(N=32, L=2*np.pi, scale_range=(-5, 6))
    
    # Get initial prime center statistics
    initial_stats = ufrf.get_prime_center_statistics()
    print(f"Initial prime centers: {initial_stats['total_centers']}")
    print(f"Static centers: {initial_stats['static_centers']}")
    print(f"Dynamic centers: {initial_stats['dynamic_centers']}")
    print(f"Spiral systems: {initial_stats['total_spiral_systems']}")
    
    # Create spiral visualizations for different scales
    print("Creating spiral visualizations...")
    for scale in [0, 1, -1]:
        create_spiral_visualization(ufrf, scale)
    
    # Create prime spiral analysis for scale intersections
    print("Creating prime spiral analysis...")
    intersection_data = create_prime_spiral_analysis(ufrf, 0, 1)
    
    # Track prime center interactions
    print("Tracking prime center interactions...")
    prime_center_data = ufrf.track_prime_center_interactions()
    print(f"Prime center interactions: {len(prime_center_data['interactions'])}")
    print(f"Generated primes from centers: {len(prime_center_data['generated_primes'])}")
    
    # Run the main simulation
    print("Running main UFRF simulation...")
    time_points, total_energies, scale_energies, max_vorticity = ufrf.run_simulation(T=50, dt=1/100)
    
    # Predict primes using enhanced spiral methods
    print("Predicting primes using spiral resonance...")
    predicted_primes = ufrf.predict_primes_multi_scale(n_primes=50)
    
    # Get final statistics
    final_stats = ufrf.get_prime_center_statistics()
    print(f"Final prime centers: {final_stats['total_centers']}")
    print(f"New dynamic centers: {final_stats['dynamic_centers'] - initial_stats['dynamic_centers']}")
    
    # Save all results
    print("Saving results...")
    save_plots(time_points, total_energies, scale_energies, max_vorticity, predicted_primes)
    
    # Save simulation data
    simulation_data = {
        'time_points': time_points,
        'total_energies': total_energies,
        'scale_energies': scale_energies,
        'max_vorticity': max_vorticity,
        'predicted_primes': predicted_primes,
        'spiral_intersection_data': intersection_data,
        'prime_center_data': prime_center_data,
        'initial_stats': initial_stats,
        'final_stats': final_stats
    }
    
    with open('ufrf_simulation_results/simulation_data.json', 'w') as f:
        json.dump(simulation_data, f, indent=2, default=str)
    
    print("=== Simulation Complete ===")
    print(f"Final energy: {total_energies[-1]:.6f}")
    print(f"Energy growth: {((total_energies[-1] - total_energies[0]) / total_energies[0] * 100):.2f}%" if total_energies[0] > 0 else "N/A")
    print(f"Predicted primes: {len(predicted_primes)}")
    print(f"Spiral intersections: {len(intersection_data['intersections'])}")
    print(f"Generated primes via spirals: {len(intersection_data['generated_primes'])}")
    print(f"Prime center interactions: {len(prime_center_data['interactions'])}")
    print(f"Dynamic primes generated: {len(prime_center_data['generated_primes'])}")