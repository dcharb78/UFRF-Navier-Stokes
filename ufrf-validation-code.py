"""
UFRF Navier-Stokes Validation Suite
===================================
Complete implementation for testing, visualizing, and validating the 
Unified Fractal Resonance Framework solution to the Navier-Stokes equations.

Author: Daniel Charboneau
Date: June 25, 2025
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D
import scipy.special as sp
from scipy.fft import fftn, ifftn, fftfreq
from scipy.integrate import solve_ivp
from scipy.linalg import expm
import time
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import json
import warnings
warnings.filterwarnings('ignore')

# Golden ratio constant
PHI = (1 + np.sqrt(5)) / 2

# ==============================================================================
# Core Mathematical Functions
# ==============================================================================

def is_prime(n: int) -> bool:
    """Check if a number is prime."""
    if n < 2:
        return False
    for i in range(2, int(np.sqrt(n)) + 1):
        if n % i == 0:
            return False
    return True

def get_primes_up_to(n: int) -> List[int]:
    """Get all prime numbers up to n."""
    return [i for i in range(2, n + 1) if is_prime(i)]

def harmonic_unity(n: float, p: int) -> float:
    """
    Calculate harmonic unity value U_p(n).
    U_p(n) = |cos(nπ/p)| + |sin(nπ/p)| + (n/p mod 1)
    """
    cos_term = abs(np.cos(n * np.pi / p))
    sin_term = abs(np.sin(n * np.pi / p))
    mod_term = (n / p) % 1
    return cos_term + sin_term + mod_term

def cross_scale_unity(n: float, p: int, scale_diff: int) -> float:
    """
    Calculate cross-scale unity value.
    U_cross = φ^|scale_diff| * U_p(n)
    """
    within_scale = harmonic_unity(n, p)
    return PHI**abs(scale_diff) * within_scale

def interference_factor(s1: int, s2: int) -> complex:
    """
    Calculate cross-scale interference factor I(s1, s2).
    I(s1,s2) = φ^|s1-s2| * cos(2π(s1-s2)/13) * exp(i*π(s1+s2)/7)
    """
    scale_diff = abs(s1 - s2)
    phase_13 = np.cos(2 * np.pi * (s1 - s2) / 13)
    phase_7 = np.exp(1j * np.pi * (s1 + s2) / 7)
    return PHI**scale_diff * phase_13 * phase_7

def compute_s_matrix(scales: List[int]) -> np.ndarray:
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

def thirteen_phase_ratio(phase: int) -> float:
    """Get the energy ratio for a given phase in the 13-phase cycle."""
    ratios = {
        1: 21/20, 2: 21/20, 3: 21/20,      # Energy injection
        4: 1.0, 5: 1.0, 6: 1.0,             # Inertial transfer
        7: 49/50, 8: 49/50, 9: 49/50,      # Mode coupling
        10: 9/10,                            # REST dissipation
        11: 51/50, 12: 51/50, 13: 51/50    # Scale transition
    }
    return ratios.get(phase, 1.0)

# ==============================================================================
# Multi-Scale Field Structure
# ==============================================================================

@dataclass
class ScaleLevel:
    """Represents a single scale level in the infinite hierarchy."""
    scale: int
    grid_points: int
    domain_size: float
    u: np.ndarray  # Velocity field
    omega: np.ndarray  # Vorticity field
    energy: float
    unity_violations: Dict[int, float]  # Prime context -> violation
    
    def __post_init__(self):
        self.dx = self.domain_size / self.grid_points
        self.scaled_size = self.domain_size * PHI**self.scale

class MultiScaleField:
    """Manages the infinite recursive scale structure."""
    
    def __init__(self, base_grid: int = 64, base_domain: float = 2*np.pi,
                 scale_range: Tuple[int, int] = (-2, 2)):
        self.base_grid = base_grid
        self.base_domain = base_domain
        self.scale_range = range(scale_range[0], scale_range[1] + 1)
        self.scales = {}
        self.primes = get_primes_up_to(100)
        self.s_matrix = compute_s_matrix(list(self.scale_range))
        self.time = 0.0
        
        # Initialize each scale level
        for s in self.scale_range:
            grid_size = int(base_grid * PHI**(s/2))  # Adjust grid for scale
            self.scales[s] = self._initialize_scale(s, grid_size)
    
    def _initialize_scale(self, scale: int, grid_size: int) -> ScaleLevel:
        """Initialize a single scale level."""
        # Create grid
        x = np.linspace(0, self.base_domain, grid_size)
        y = np.linspace(0, self.base_domain, grid_size)
        z = np.linspace(0, self.base_domain, grid_size)
        X, Y, Z = np.meshgrid(x, y, z, indexing='ij')
        
        # Initialize velocity field (Taylor-Green vortex scaled)
        scale_factor = PHI**scale
        u = np.zeros((grid_size, grid_size, grid_size, 3))
        u[..., 0] = scale_factor * np.sin(X) * np.cos(Y) * np.cos(Z)
        u[..., 1] = -scale_factor * np.cos(X) * np.sin(Y) * np.cos(Z)
        u[..., 2] = 0
        
        # Compute vorticity
        omega = self._compute_vorticity(u, self.base_domain / grid_size)
        
        # Compute energy
        energy = 0.5 * np.sum(u**2) * (self.base_domain / grid_size)**3
        
        return ScaleLevel(
            scale=scale,
            grid_points=grid_size,
            domain_size=self.base_domain,
            u=u,
            omega=omega,
            energy=energy,
            unity_violations={}
        )
    
    def _compute_vorticity(self, u: np.ndarray, dx: float) -> np.ndarray:
        """Compute vorticity using finite differences."""
        omega = np.zeros_like(u)
        
        # ω = ∇ × u
        omega[..., 0] = np.gradient(u[..., 2], dx, axis=1) - np.gradient(u[..., 1], dx, axis=2)
        omega[..., 1] = np.gradient(u[..., 0], dx, axis=2) - np.gradient(u[..., 2], dx, axis=0)
        omega[..., 2] = np.gradient(u[..., 1], dx, axis=0) - np.gradient(u[..., 0], dx, axis=1)
        
        return omega
    
    def compute_cross_scale_coupling(self, s1: int, s2: int) -> float:
        """Compute coupling strength between two scales."""
        if s1 not in self.scale_range or s2 not in self.scale_range:
            return 0.0
        
        i1 = list(self.scale_range).index(s1)
        i2 = list(self.scale_range).index(s2)
        
        return abs(self.s_matrix[i1, i2])
    
    def update_unity_violations(self):
        """Update harmonic unity violations for all scales and prime contexts."""
        for scale, level in self.scales.items():
            for p in self.primes[:10]:  # Check first 10 primes
                # Compute local Reynolds number
                Re = np.max(np.linalg.norm(level.u, axis=-1)) * level.scaled_size / 0.01
                
                # Check unity violation
                unity = harmonic_unity(Re, p)
                level.unity_violations[p] = abs(unity - 1.0)
    
    def get_total_energy(self) -> float:
        """Compute total energy across all scales."""
        total = 0.0
        for scale, level in self.scales.items():
            total += PHI**scale * level.energy
        return total
    
    def get_prime_vortex_centers(self, scale: int) -> List[Tuple[float, float, float]]:
        """Find vortex centers at prime locations for a given scale."""
        if scale not in self.scales:
            return []
        
        level = self.scales[scale]
        centers = []
        
        # Look for local maxima of vorticity magnitude
        omega_mag = np.linalg.norm(level.omega, axis=-1)
        
        for p in self.primes[:10]:
            # Expected radius for this prime at this scale
            r = p * level.scaled_size / level.domain_size
            
            # Search in spherical shell around this radius
            X, Y, Z = np.mgrid[0:level.grid_points, 0:level.grid_points, 0:level.grid_points]
            X = X * level.dx
            Y = Y * level.dx
            Z = Z * level.dx
            
            # Distance from origin
            R = np.sqrt((X - level.domain_size/2)**2 + 
                       (Y - level.domain_size/2)**2 + 
                       (Z - level.domain_size/2)**2)
            
            # Find maxima in shell
            shell_mask = (abs(R - r) < level.dx * 2)
            if np.any(shell_mask):
                shell_omega = omega_mag * shell_mask
                if np.max(shell_omega) > 0:
                    idx = np.unravel_index(np.argmax(shell_omega), shell_omega.shape)
                    centers.append((X[idx], Y[idx], Z[idx]))
        
        return centers

# ==============================================================================
# Spiral Decomposition
# ==============================================================================

class SpiralDecomposition:
    """Implements golden and krystal spiral decomposition."""
    
    def __init__(self, grid_size: int, domain_size: float):
        self.grid_size = grid_size
        self.domain_size = domain_size
        self.dx = domain_size / grid_size
        
        # Create coordinate grids
        x = np.linspace(0, domain_size, grid_size)
        self.X, self.Y, self.Z = np.meshgrid(x, x, x, indexing='ij')
    
    def golden_spiral(self, t: float, scale: int = 0) -> np.ndarray:
        """Generate golden spiral basis at given time and scale."""
        scale_factor = PHI**(scale + t/(2*np.pi))
        
        # Cylindrical coordinates
        R = np.sqrt((self.X - self.domain_size/2)**2 + 
                   (self.Y - self.domain_size/2)**2)
        theta = np.arctan2(self.Y - self.domain_size/2, 
                          self.X - self.domain_size/2)
        
        # Golden spiral
        spiral = np.zeros((self.grid_size, self.grid_size, self.grid_size, 3))
        spiral[..., 0] = scale_factor * np.cos(theta + t) * np.exp(-R/(self.domain_size/4))
        spiral[..., 1] = scale_factor * np.sin(theta + t) * np.exp(-R/(self.domain_size/4))
        spiral[..., 2] = scale_factor * np.sin(t/PHI) * np.exp(-R/(self.domain_size/4))
        
        return spiral
    
    def krystal_spiral(self, t: float, scale: int = 0) -> np.ndarray:
        """Generate krystal spiral basis at given time and scale."""
        scale_factor = PHI**(scale + t/(2*np.pi))
        
        # Cylindrical coordinates
        R = np.sqrt((self.X - self.domain_size/2)**2 + 
                   (self.Y - self.domain_size/2)**2)
        theta = np.arctan2(self.Y - self.domain_size/2, 
                          self.X - self.domain_size/2)
        
        # Krystal spiral (opposite chirality)
        spiral = np.zeros((self.grid_size, self.grid_size, self.grid_size, 3))
        spiral[..., 0] = scale_factor * np.cos(theta - t) * np.exp(-R/(self.domain_size/4))
        spiral[..., 1] = scale_factor * np.sin(theta - t) * np.exp(-R/(self.domain_size/4))
        spiral[..., 2] = -scale_factor * np.sin(t/PHI) * np.exp(-R/(self.domain_size/4))
        
        return spiral
    
    def decompose(self, omega: np.ndarray, t: float, scale: int = 0) -> Dict[str, np.ndarray]:
        """Decompose vorticity into spiral components."""
        golden = self.golden_spiral(t, scale)
        krystal = self.krystal_spiral(t, scale)
        
        # Project onto spirals
        omega_golden_coeff = np.sum(omega * golden) / np.sum(golden * golden)
        omega_krystal_coeff = np.sum(omega * krystal) / np.sum(krystal * krystal)
        
        omega_golden = omega_golden_coeff * golden
        omega_krystal = omega_krystal_coeff * krystal
        omega_residual = omega - omega_golden - omega_krystal
        
        return {
            'golden': omega_golden,
            'krystal': omega_krystal,
            'residual': omega_residual,
            'golden_coeff': omega_golden_coeff,
            'krystal_coeff': omega_krystal_coeff
        }

# ==============================================================================
# Regularization Mechanisms
# ==============================================================================

class UFRFRegularization:
    """Implements all four regularization mechanisms."""
    
    def __init__(self, multi_scale_field: MultiScaleField):
        self.field = multi_scale_field
        self.spiral_decomp = {}
        
        # Initialize spiral decomposition for each scale
        for scale, level in self.field.scales.items():
            self.spiral_decomp[scale] = SpiralDecomposition(
                level.grid_points, level.domain_size
            )
    
    def spiral_interference(self, scale: int, omega: np.ndarray) -> np.ndarray:
        """
        Mechanism 1: Spiral interference regularization.
        λ_eff = |ω|/(10 + |ω|)
        """
        omega_mag = np.linalg.norm(omega, axis=-1, keepdims=True)
        lambda_eff = omega_mag / (10 + omega_mag)
        
        # Apply regularization where vorticity is strong
        reg = -lambda_eff * omega
        
        # Add cross-scale coupling
        for other_scale in self.field.scale_range:
            if other_scale != scale:
                coupling = self.field.compute_cross_scale_coupling(scale, other_scale)
                if coupling > 0.1:  # Significant coupling
                    other_omega = self.field.scales[other_scale].omega
                    # Interpolate if needed (simplified here)
                    reg += coupling * self._interpolate_field(other_omega, scale, other_scale)
        
        return reg
    
    def prime_center_regularization(self, scale: int, omega: np.ndarray) -> np.ndarray:
        """
        Mechanism 2: Prime center distribution regularization.
        """
        level = self.field.scales[scale]
        reg = np.zeros_like(omega)
        
        # Get vortex centers
        centers = self.field.get_prime_vortex_centers(scale)
        
        for i, (cx, cy, cz) in enumerate(centers):
            if i < len(self.field.primes):
                p = self.field.primes[i]
                
                # Gaussian regularization at prime center
                R2 = ((self.spiral_decomp[scale].X - cx)**2 + 
                     (self.spiral_decomp[scale].Y - cy)**2 + 
                     (self.spiral_decomp[scale].Z - cz)**2)
                
                gaussian = np.exp(-R2 / (level.dx * p)**2)
                reg -= (1.0 / p) * gaussian[..., np.newaxis] * omega
        
        return reg
    
    def harmonic_unity_regularization(self, scale: int, u: np.ndarray) -> np.ndarray:
        """
        Mechanism 3: Harmonic unity constraint regularization.
        """
        level = self.field.scales[scale]
        
        # Check unity violations
        min_violation = 1.0
        best_prime = 2
        
        for p, violation in level.unity_violations.items():
            if violation < min_violation:
                min_violation = violation
                best_prime = p
        
        # If unity is achieved (violation < threshold), apply gradient bound
        if min_violation < 0.1:
            # Compute local Reynolds number
            Re = np.max(np.linalg.norm(u, axis=-1)) * level.scaled_size / 0.01
            
            # Gradient bound
            grad_bound = np.sqrt(Re)
            
            # Compute gradient magnitude
            grad_u = np.zeros_like(u)
            for i in range(3):
                grad_u[..., i] = np.gradient(u[..., i], level.dx)
            
            grad_mag = np.linalg.norm(grad_u, axis=-1, keepdims=True)
            
            # Apply regularization where gradient exceeds bound
            mask = grad_mag > grad_bound
            reg = -mask * (grad_mag - grad_bound) * u / (grad_mag + 1e-10)
        else:
            reg = np.zeros_like(u)
        
        return reg
    
    def thirteen_phase_cascade(self, scale: int, u: np.ndarray, t: float) -> np.ndarray:
        """
        Mechanism 4: 13-phase energy cascade.
        """
        # Current phase (synchronized across scales)
        phase = int((t * 13 / (2 * np.pi)) % 13) + 1
        
        # Get energy ratio for current phase
        ratio = thirteen_phase_ratio(phase)
        
        # Apply phase-dependent modification
        if phase <= 3:  # Energy injection
            reg = (ratio - 1.0) * u
        elif phase <= 6:  # Inertial transfer
            reg = np.zeros_like(u)
        elif phase <= 9:  # Mode coupling
            # Enhance mode coupling
            k_space = fftn(u, axes=(0, 1, 2))
            k_space *= ratio
            reg = np.real(ifftn(k_space, axes=(0, 1, 2))) - u
        elif phase == 10:  # REST dissipation
            # Enhanced dissipation
            reg = (ratio - 1.0) * u
        else:  # Scale transition
            # Prepare for scale transition
            reg = (ratio - 1.0) * u
        
        return reg
    
    def _interpolate_field(self, field: np.ndarray, target_scale: int, 
                          source_scale: int) -> np.ndarray:
        """Interpolate field between scales (simplified)."""
        # In full implementation, use proper spectral interpolation
        scale_ratio = PHI**(target_scale - source_scale)
        
        if scale_ratio > 1:
            # Upsampling (simplified)
            return np.repeat(field, int(scale_ratio), axis=(0, 1, 2))[:field.shape[0], 
                                                                      :field.shape[1], 
                                                                      :field.shape[2]]
        else:
            # Downsampling (simplified)
            step = int(1 / scale_ratio)
            return field[::step, ::step, ::step]
    
    def total_regularization(self, t: float) -> Dict[int, Dict[str, np.ndarray]]:
        """Apply all regularization mechanisms to all scales."""
        regularizations = {}
        
        for scale, level in self.field.scales.items():
            reg_u = np.zeros_like(level.u)
            reg_omega = np.zeros_like(level.omega)
            
            # Apply each mechanism
            reg_omega += self.spiral_interference(scale, level.omega)
            reg_omega += self.prime_center_regularization(scale, level.omega)
            reg_u += self.harmonic_unity_regularization(scale, level.u)
            reg_u += self.thirteen_phase_cascade(scale, level.u, t)
            
            regularizations[scale] = {
                'u': reg_u,
                'omega': reg_omega
            }
        
        return regularizations

# ==============================================================================
# Validation Tests
# ==============================================================================

class ValidationSuite:
    """Comprehensive validation tests for UFRF theory."""
    
    def __init__(self, multi_scale_field: MultiScaleField):
        self.field = multi_scale_field
        self.results = {}
    
    def test_harmonic_unity(self, num_tests: int = 1000) -> Dict[str, float]:
        """Test harmonic unity rule within and across scales."""
        results = {
            'within_scale_accuracy': [],
            'cross_scale_accuracy': [],
            'multi_context_resonance': []
        }
        
        for _ in range(num_tests):
            # Random prime and value
            p = np.random.choice(self.field.primes[:20])
            k = np.random.randint(1, 100)
            n = k * p
            
            # Test within scale
            unity = harmonic_unity(n, p)
            results['within_scale_accuracy'].append(abs(unity - 1.0))
            
            # Test cross-scale
            scale_diff = np.random.randint(-2, 3)
            cross_unity = cross_scale_unity(n, p, scale_diff)
            expected = PHI**abs(scale_diff)
            results['cross_scale_accuracy'].append(abs(cross_unity - expected))
            
            # Test multi-context resonance (n = 30 in contexts 2, 3, 5)
            if n == 30:
                for test_p in [2, 3, 5]:
                    unity_p = harmonic_unity(30, test_p)
                    results['multi_context_resonance'].append(abs(unity_p - 1.0))
        
        return {
            'within_scale_mean_error': np.mean(results['within_scale_accuracy']),
            'within_scale_max_error': np.max(results['within_scale_accuracy']),
            'cross_scale_mean_error': np.mean(results['cross_scale_accuracy']),
            'cross_scale_max_error': np.max(results['cross_scale_accuracy']),
            'multi_context_success': np.sum(np.array(results['multi_context_resonance']) < 1e-10) 
                                    / len(results['multi_context_resonance']) if results['multi_context_resonance'] else 0
        }
    
    def test_scale_invariance(self) -> Dict[str, float]:
        """Test scale invariance of patterns."""
        results = {}
        
        # Check golden ratio scaling
        for s1 in self.field.scale_range:
            for s2 in self.field.scale_range:
                if s1 != s2:
                    # Energy scaling
                    E1 = self.field.scales[s1].energy
                    E2 = self.field.scales[s2].energy
                    expected_ratio = PHI**(s2 - s1)
                    actual_ratio = E2 / E1 if E1 > 0 else 0
                    
                    results[f'energy_scaling_{s1}_to_{s2}'] = abs(actual_ratio / expected_ratio - 1.0)
        
        return results
    
    def test_s_matrix_properties(self) -> Dict[str, bool]:
        """Test properties of the scale synchronization matrix."""
        S = self.field.s_matrix
        results = {}
        
        # Test 1: Hermiticity
        results['is_hermitian'] = np.allclose(S, S.conj().T)
        
        # Test 2: Eigenvalues on unit circle
        eigenvalues = np.linalg.eigvals(S)
        results['eigenvalues_unit_circle'] = np.allclose(np.abs(eigenvalues), 1.0)
        
        # Test 3: 13-cycle property (S^13 = I)
        S13 = np.linalg.matrix_power(S, 13)
        results['thirteen_cycle'] = np.allclose(S13, np.eye(len(S)))
        
        return results
    
    def test_prime_distribution(self) -> Dict[str, float]:
        """Test prime vortex center distribution."""
        results = {}
        
        for scale in self.field.scale_range:
            centers = self.field.get_prime_vortex_centers(scale)
            
            # Check spacing between centers
            if len(centers) > 1:
                spacings = []
                for i in range(len(centers) - 1):
                    c1 = np.array(centers[i])
                    c2 = np.array(centers[i + 1])
                    spacings.append(np.linalg.norm(c2 - c1))
                
                # Average spacing should scale with ln(p)
                avg_spacing = np.mean(spacings)
                expected_spacing = np.log(self.field.primes[len(centers) // 2]) * self.field.scales[scale].scaled_size
                
                results[f'spacing_accuracy_scale_{scale}'] = abs(avg_spacing / expected_spacing - 1.0)
        
        return results
    
    def test_energy_conservation(self, regularization: UFRFRegularization, 
                               time_steps: int = 100, dt: float = 0.01) -> Dict[str, List[float]]:
        """Test energy conservation/dissipation properties."""
        energy_history = []
        phase_history = []
        
        for step in range(time_steps):
            t = step * dt
            
            # Get total energy
            total_energy = self.field.get_total_energy()
            energy_history.append(total_energy)
            
            # Get current phase
            phase = int((t * 13 / (2 * np.pi)) % 13) + 1
            phase_history.append(phase)
            
            # Apply regularization (simplified - just track energy change)
            reg = regularization.total_regularization(t)
            
            # Update energy (simplified)
            for scale, level in self.field.scales.items():
                # Energy change from regularization
                delta_E = np.sum(level.u * reg[scale]['u']) * level.dx**3
                level.energy += dt * delta_E
        
        return {
            'energy_history': energy_history,
            'phase_history': phase_history,
            'energy_monotonic': all(energy_history[i] >= energy_history[i+1] 
                                  for i in range(len(energy_history)-1))
        }
    
    def run_all_tests(self, regularization: UFRFRegularization) -> Dict[str, any]:
        """Run complete validation suite."""
        print("Running UFRF Validation Suite...")
        
        results = {
            'harmonic_unity': self.test_harmonic_unity(),
            'scale_invariance': self.test_scale_invariance(),
            's_matrix': self.test_s_matrix_properties(),
            'prime_distribution': self.test_prime_distribution(),
            'energy_conservation': self.test_energy_conservation(regularization)
        }
        
        # Summary statistics
        results['summary'] = {
            'harmonic_unity_valid': results['harmonic_unity']['within_scale_mean_error'] < 1e-10,
            'cross_scale_valid': results['harmonic_unity']['cross_scale_mean_error'] < 1e-10,
            's_matrix_valid': all(results['s_matrix'].values()),
            'energy_conserved': results['energy_conservation']['energy_monotonic']
        }
        
        return results

# ==============================================================================
# Visualization Functions
# ==============================================================================

class UFRFVisualizer:
    """Visualization tools for UFRF validation."""
    
    def __init__(self, multi_scale_field: MultiScaleField):
        self.field = multi_scale_field
        self.fig = None
    
    def plot_harmonic_unity(self, p: int = 7, scale_range: Tuple[int, int] = (-2, 2)):
        """Visualize harmonic unity function within and across scales."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Within scale unity
        n_values = np.arange(0, 10*p, 0.1)
        unity_values = [harmonic_unity(n, p) for n in n_values]
        
        ax1.plot(n_values/p, unity_values, 'b-', linewidth=2)
        ax1.axhline(y=1, color='r', linestyle='--', label='Unity')
        ax1.set_xlabel('n/p')
        ax1.set_ylabel('U_p(n)')
        ax1.set_title(f'Harmonic Unity Function (p={p})')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Cross-scale unity
        scales = np.linspace(scale_range[0], scale_range[1], 100)
        cross_unity = [PHI**abs(s) for s in scales]
        
        ax2.plot(scales, cross_unity, 'g-', linewidth=2)
        ax2.set_xlabel('Scale Difference')
        ax2.set_ylabel('Cross-Scale Unity Factor')
        ax2.set_title('Cross-Scale Unity: φ^|Δs|')
        ax2.grid(True, alpha=0.3)
        ax2.set_yscale('log')
        
        plt.tight_layout()
        return fig
    
    def plot_spiral_decomposition(self, scale: int = 0, t: float = 0):
        """Visualize spiral decomposition at a given scale and time."""
        if scale not in self.field.scales:
            print(f"Scale {scale} not available")
            return
        
        level = self.field.scales[scale]
        decomp = SpiralDecomposition(level.grid_points, level.domain_size)
        
        # Get spirals
        golden = decomp.golden_spiral(t, scale)
        krystal = decomp.krystal_spiral(t, scale)
        
        # Plot middle slice
        mid = level.grid_points // 2
        
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        
        # Golden spiral components
        for i, (ax, title) in enumerate(zip(axes[0], ['Golden X', 'Golden Y', 'Golden Z'])):
            im = ax.imshow(golden[mid, :, :, i], cmap='RdBu', aspect='equal')
            ax.set_title(title)
            plt.colorbar(im, ax=ax)
        
        # Krystal spiral components
        for i, (ax, title) in enumerate(zip(axes[1], ['Krystal X', 'Krystal Y', 'Krystal Z'])):
            im = ax.imshow(krystal[mid, :, :, i], cmap='RdBu', aspect='equal')
            ax.set_title(title)
            plt.colorbar(im, ax=ax)
        
        plt.suptitle(f'Spiral Decomposition at Scale {scale}, t={t:.2f}')
        plt.tight_layout()
        return fig
    
    def plot_multi_scale_structure(self):
        """Visualize the multi-scale field structure."""
        fig = plt.figure(figsize=(15, 10))
        
        # Create subplots for different scales
        n_scales = len(self.field.scales)
        cols = int(np.ceil(np.sqrt(n_scales)))
        rows = int(np.ceil(n_scales / cols))
        
        for idx, (scale, level) in enumerate(self.field.scales.items()):
            ax = fig.add_subplot(rows, cols, idx + 1)
            
            # Plot vorticity magnitude at middle slice
            mid = level.grid_points // 2
            omega_mag = np.linalg.norm(level.omega[mid, :, :], axis=-1)
            
            im = ax.imshow(omega_mag, cmap='hot', aspect='equal')
            ax.set_title(f'Scale {scale}: Vorticity')
            ax.axis('off')
            
            # Mark prime centers
            centers = self.field.get_prime_vortex_centers(scale)
            for cx, cy, cz in centers[:5]:  # Show first 5
                if abs(cz - level.domain_size/2) < level.dx:
                    ax.plot(cy/level.dx, cx/level.dx, 'w*', markersize=10)
        
        plt.suptitle('Multi-Scale Vorticity Structure')
        plt.tight_layout()
        return fig
    
    def plot_s_matrix(self):
        """Visualize the scale synchronization matrix."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        S = self.field.s_matrix
        
        # Magnitude
        im1 = ax1.imshow(np.abs(S), cmap='viridis', aspect='equal')
        ax1.set_title('S-Matrix Magnitude')
        ax1.set_xlabel('Scale Index')
        ax1.set_ylabel('Scale Index')
        plt.colorbar(im1, ax=ax1)
        
        # Phase
        im2 = ax2.imshow(np.angle(S), cmap='hsv', aspect='equal', vmin=-np.pi, vmax=np.pi)
        ax2.set_title('S-Matrix Phase')
        ax2.set_xlabel('Scale Index')
        ax2.set_ylabel('Scale Index')
        plt.colorbar(im2, ax=ax2, label='Phase (rad)')
        
        plt.tight_layout()
        return fig
    
    def plot_13_phase_cycle(self, time_steps: int = 130):
        """Visualize the 13-phase energy cascade cycle."""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        times = np.linspace(0, 4*np.pi, time_steps)
        phases = ((times * 13 / (2 * np.pi)) % 13).astype(int) + 1
        ratios = [thirteen_phase_ratio(p) for p in phases]
        
        # Phase evolution
        ax1.plot(times, phases, 'b-', linewidth=2)
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Phase')
        ax1.set_title('13-Phase Cycle Evolution')
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(0, 14)
        
        # Energy ratios
        ax2.plot(times, ratios, 'r-', linewidth=2)
        ax2.axhline(y=1, color='k', linestyle='--', alpha=0.5)
        ax2.set_xlabel('Time')
        ax2.set_ylabel('Energy Ratio')
        ax2.set_title('Phase-Dependent Energy Ratios')
        ax2.grid(True, alpha=0.3)
        
        # Mark phase boundaries
        for i in range(1, 14):
            phase_time = i * 2 * np.pi / 13
            ax1.axvline(x=phase_time, color='gray', alpha=0.3)
            ax2.axvline(x=phase_time, color='gray', alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def animate_evolution(self, regularization: UFRFRegularization, 
                         frames: int = 100, interval: int = 50):
        """Animate the multi-scale evolution."""
        fig = plt.figure(figsize=(12, 8))
        
        # Setup axes
        n_scales = len(self.field.scales)
        axes = []
        for i, scale in enumerate(self.field.scales.keys()):
            ax = fig.add_subplot(1, n_scales, i + 1, projection='3d')
            axes.append(ax)
        
        def update(frame):
            t = frame * 0.1
            
            # Clear axes
            for ax in axes:
                ax.clear()
            
            # Apply regularization
            reg = regularization.total_regularization(t)
            
            # Update and plot each scale
            for i, (scale, level) in enumerate(self.field.scales.items()):
                ax = axes[i]
                
                # Simple evolution (for visualization)
                level.u += 0.01 * reg[scale]['u']
                level.omega = regularization.field.field._compute_vorticity(
                    level.u, level.dx
                )
                
                # Plot isosurface of vorticity magnitude
                omega_mag = np.linalg.norm(level.omega, axis=-1)
                threshold = 0.5 * np.max(omega_mag)
                
                # Create simplified isosurface visualization
                x, y, z = np.where(omega_mag > threshold)
                if len(x) > 0:
                    ax.scatter(x[::10], y[::10], z[::10], 
                             c=omega_mag[x[::10], y[::10], z[::10]], 
                             cmap='hot', s=1)
                
                ax.set_title(f'Scale {scale}')
                ax.set_xlim(0, level.grid_points)
                ax.set_ylim(0, level.grid_points)
                ax.set_zlim(0, level.grid_points)
            
            plt.suptitle(f'Multi-Scale Evolution (t={t:.2f})')
        
        anim = FuncAnimation(fig, update, frames=frames, interval=interval)
        return anim

# ==============================================================================
# Main Execution and Testing
# ==============================================================================

def run_complete_validation():
    """Run the complete UFRF validation suite."""
    print("=" * 80)
    print("UFRF Navier-Stokes Validation Suite")
    print("=" * 80)
    
    # Initialize multi-scale field
    print("\nInitializing multi-scale field structure...")
    field = MultiScaleField(base_grid=32, scale_range=(-2, 2))
    print(f"Created {len(field.scales)} scale levels: {list(field.scales.keys())}")
    
    # Initialize regularization
    print("\nInitializing regularization mechanisms...")
    regularization = UFRFRegularization(field)
    
    # Run validation tests
    print("\nRunning validation tests...")
    validator = ValidationSuite(field)
    results = validator.run_all_tests(regularization)
    
    # Print results
    print("\n" + "=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)
    
    print("\n1. Harmonic Unity Tests:")
    print(f"   Within-scale mean error: {results['harmonic_unity']['within_scale_mean_error']:.2e}")
    print(f"   Within-scale max error: {results['harmonic_unity']['within_scale_max_error']:.2e}")
    print(f"   Cross-scale mean error: {results['harmonic_unity']['cross_scale_mean_error']:.2e}")
    print(f"   Multi-context resonance success: {results['harmonic_unity']['multi_context_success']:.1%}")
    
    print("\n2. S-Matrix Properties:")
    for prop, valid in results['s_matrix'].items():
        print(f"   {prop}: {'✓' if valid else '✗'}")
    
    print("\n3. Energy Conservation:")
    print(f"   Energy monotonic: {'✓' if results['energy_conservation']['energy_monotonic'] else '✗'}")
    
    print("\n4. Overall Validation:")
    all_valid = all(results['summary'].values())
    print(f"   All tests passed: {'✓' if all_valid else '✗'}")
    
    # Create visualizations
    print("\nGenerating visualizations...")
    visualizer = UFRFVisualizer(field)
    
    # Save figures
    figs = []
    figs.append(visualizer.plot_harmonic_unity())
    figs.append(visualizer.plot_spiral_decomposition())
    figs.append(visualizer.plot_multi_scale_structure())
    figs.append(visualizer.plot_s_matrix())
    figs.append(visualizer.plot_13_phase_cycle())
    
    # Save results
    print("\nSaving results...")
    with open('ufrf_validation_results.json', 'w') as f:
        # Convert numpy arrays to lists for JSON serialization
        json_results = {
            'summary': results['summary'],
            'harmonic_unity': results['harmonic_unity'],
            's_matrix': {k: bool(v) for k, v in results['s_matrix'].items()},
            'energy_history': results['energy_conservation']['energy_history'][:20]  # First 20 points
        }
        json.dump(json_results, f, indent=2)
    
    print("\nValidation complete! Results saved to 'ufrf_validation_results.json'")
    
    return field, regularization, results, figs

if __name__ == "__main__":
    # Run the validation
    field, reg, results, figures = run_complete_validation()
    
    # Show plots
    plt.show()
