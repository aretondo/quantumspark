import math
import random
import statistics
import pygame
import time
import os
from dotenv import load_dotenv
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# -----------------------
# VARIÁVEIS GLOBAIS
# -----------------------
# A largura e a altura da janela do jogo.
WIDTH = int(os.getenv("WIDTH", 1920))
HEIGHT = int(os.getenv("HEIGHT", 1080))

# A taxa de criação de novas flutuações, em milissegundos.
SPAWN_MULTIPLIER = float(os.getenv("SPAWN_MULTIPLIER", 0.5))

# O nível de caos (r) decai a cada N flutuações criadas.
R_DECAY_INTERVAL = int(os.getenv("R_DECAY_INTERVAL", 50))
# A taxa com que o nível de caos (r) decai.
R_DECAY_RATE = float(os.getenv("R_DECAY_RATE", 0.005))

# Constantes de Física
EM_CONSTANT = float(os.getenv("EM_CONSTANT", 50.0))
GRAVITY_CONSTANT = float(os.getenv("GRAVITY_CONSTANT", 1.0))
NUCLEAR_THRESHOLD = int(os.getenv("NUCLEAR_THRESHOLD", 20))

# Tempos de vida de partículas e efeitos visuais
QUARK_DECAY_MAX_LIFETIME = int(os.getenv("QUARK_DECAY_MAX_LIFETIME", 300))
SPARK_LIFETIME = int(os.getenv("SPARK_LIFETIME", 60))
PHOTON_LIFETIME = int(os.getenv("PHOTON_LIFETIME", 60))

# Cor de fundo
BG_COLOR = (0, 0, 0)

# -----------------------
# Logística
# -----------------------

def logistic_iter(r, x0, n_iters=200, discard=100):
    x = x0
    seq = []
    for _ in range(n_iters):
        x = r * x * (1 - x)
        seq.append(x)
    return seq[discard:]

def cluster_attractors(values, eps=1e-3):
    clusters = []
    for v in values:
        placed = False
        for c in clusters:
            if abs(c[0] - v) < eps:
                c.append(v)
                placed = True
                break
        if not placed:
            clusters.append([v])
    results = [(statistics.mean(c), len(c)) for c in clusters]
    results.sort(key=lambda t: t[0])
    return results

def sample_branches_for_r(r, n_inits=60):
    all_end_values = []
    for _ in range(n_inits):
        x0 = random.random()
        tail = logistic_iter(r, x0)
        sampled = tail[-20:]
        all_end_values.extend(sampled)
    return cluster_attractors(all_end_values, eps=1e-3)

# -----------------------
# Classes de Objetos
# -----------------------

class QuantumSpark:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.vx = random.uniform(-1, 1)
        self.vy = random.uniform(-2, -0.5)
        self.size = random.randint(1, 3)
        self.color = color
        self.lifetime = SPARK_LIFETIME

    def update(self):
        self.x += self.vx * 0.5
        self.y += self.vy * 0.5
        self.vy += 0.1
        self.lifetime -= 1
        self.size *= 0.98
        self.color = (max(0, self.color[0]-5), max(0, self.color[1]-5), max(0, self.color[2]-5))

    def draw(self, screen):
        if self.lifetime > 0:
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), int(self.size))

class Photon:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-5, 5)
        self.vy = random.uniform(-5, 5)
        self.size = 3
        self.color = (255, 255, 0) # Amarelo, representando a luz
        self.lifetime = PHOTON_LIFETIME

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= 1
        self.size = max(0, self.size - 0.1)

    def draw(self, screen):
        if self.lifetime > 0:
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), int(self.size))

def generate_wave_shape(x, y, base_size, num_points, distortion, angle_offset=0):
    points = []
    for i in range(num_points):
        angle = math.radians(i * (360 / num_points) + angle_offset)
        current_radius = base_size + math.sin(angle * 5 + pygame.time.get_ticks() * 0.01) * distortion
        px = x + current_radius * math.cos(angle)
        py = y + current_radius * math.sin(angle)
        points.append((px, py))
    return points

class Fluctuation:
    def __init__(self, x, y, center_value, color, game_instance, chaos_level=0.0, vx=None, vy=None):
        self.x = x
        self.y = y
        self.center_value = center_value
        self.color = color
        self.size = 10
        self.vx = vx if vx is not None else random.uniform(-1.5, 1.5)
        self.vy = vy if vy is not None else random.uniform(-1.5, 1.5)
        self.state = game_instance.interpret_branch(center_value)
        self.animation_timer = 0
        self.pulse_offset = 0
        self.angle = 0
        self.spin_speed = random.uniform(-5, 5)

        self.chaos_level = chaos_level 
        self.num_points = 12
        self.distortion_factor = 5

        self.quantum_circuit = self.create_quantum_circuit(self.state)

    def create_quantum_circuit(self, state):
        qc = QuantumCircuit(1, 1)
        if "Anti" in state:
            qc.x(0)
        qc.h(0)
        qc.measure(0, 0)
        return qc

    def update_visuals_from_chaos(self):
        self.num_points = 8 + int((1.0 - self.chaos_level) * 4)
        self.distortion_factor = 5 + (self.chaos_level * 15)

    def update(self):
        self.update_visuals_from_chaos()

        self.x += self.vx
        self.y += self.vy
        self.animate()
        self.angle += self.spin_speed
        
        if self.x < 0:
            self.x = WIDTH
        elif self.x > WIDTH:
            self.x = 0
        if self.y < 0:
            self.y = HEIGHT
        elif self.y > HEIGHT:
            self.y = 0
        
    def animate(self):
        self.animation_timer += 1
        self.pulse_offset = math.sin(self.animation_timer * 0.1) * 3
        
    def draw(self, screen):
        current_size = self.size + self.pulse_offset
        if current_size > 0:
            points = generate_wave_shape(self.x, self.y, current_size, self.num_points, self.distortion_factor, self.angle)
            pygame.draw.polygon(screen, self.color, points)

class StableParticle:
    def __init__(self, x, y, color, particle_type, magnetic_field_strength=0.1, vx=0, vy=0):
        self.x = x
        self.y = y
        self.color = color
        self.particle_type = particle_type
        self.size = 5
        self.magnetic_field_strength = magnetic_field_strength
        self.angle = random.uniform(0, 360)
        self.spin_speed = random.uniform(-3, 3)
        self.vx = vx
        self.vy = vy
        self.is_captured = False

        self.lifetime = 1000
        self.is_long_lived = True
        self.charge = 0

        # Define as propriedades de cada tipo de partícula
        if self.particle_type == "Proton":
            self.charge = 1
        elif self.particle_type == "Electron":
            self.charge = -1
        elif self.particle_type == "Positron":
            self.charge = 1
        elif self.particle_type == "Deuterium": # Núcleo de Deutério
            self.charge = 1
            self.size = 15
        elif self.particle_type == "Deuterium Atom": # Átomo de Deutério
            self.charge = 0
            self.size = 20
        elif self.particle_type == "Hydrogen":
            self.charge = 0
            self.size = 12

        if self.particle_type.startswith("Quark_"):
            self.is_long_lived = False
            self.decay_countdown = random.randint(QUARK_DECAY_MAX_LIFETIME // 3, QUARK_DECAY_MAX_LIFETIME)
            self.decay_chance = 0.5 
            self.quantum_circuit = self.create_decay_circuit()
        
        # Efeito de piscar para novas partículas
        self.is_new = True
        self.new_timer = 60
        self.blink_state = True

    def create_decay_circuit(self):
        qc = QuantumCircuit(1, 1)
        qc.h(0) 
        qc.measure(0, 0)
        return qc

    def update(self):
        self.angle += self.spin_speed
        self.x += self.vx
        self.y += self.vy

        if self.x < 0:
            self.x = WIDTH
        elif self.x > WIDTH:
            self.x = 0
        if self.y < 0:
            self.y = HEIGHT
        elif self.y > HEIGHT:
            self.y = 0
        
        if not self.is_long_lived:
            self.decay_countdown -= 1
        
        # Lógica de piscar
        if self.is_new:
            self.new_timer -= 1
            if self.new_timer % 10 == 0:
                self.blink_state = not self.blink_state
            if self.new_timer <= 0:
                self.is_new = False
                self.blink_state = True

    def draw(self, screen):
        # Nao desenha se estiver piscando
        if self.is_new and not self.blink_state:
            return

        if self.particle_type == "Hydrogen":
            pygame.draw.circle(screen, (100, 100, 100), (int(self.x), int(self.y)), 12)
            pygame.draw.circle(screen, (50, 50, 50), (int(self.x), int(self.y)), 25, 1)
            orbit_angle = pygame.time.get_ticks() * 0.1
            electron_x = self.x + 25 * math.cos(math.radians(orbit_angle))
            electron_y = self.y + 25 * math.sin(math.radians(orbit_angle))
            pygame.draw.circle(screen, (0, 255, 0), (int(electron_x), int(electron_y)), 5)
            return

        # Desenho para Deuterio Atom
        if self.particle_type == "Deuterium Atom":
            pygame.draw.circle(screen, (150, 150, 255), (int(self.x), int(self.y)), 15)
            pygame.draw.circle(screen, (50, 50, 50), (int(self.x), int(self.y)), 30, 1)
            orbit_angle = pygame.time.get_ticks() * 0.1
            electron_x = self.x + 30 * math.cos(math.radians(orbit_angle))
            electron_y = self.y + 30 * math.sin(math.radians(orbit_angle))
            pygame.draw.circle(screen, (0, 255, 0), (int(electron_x), int(electron_y)), 5)
            return
        
        if self.particle_type == "Proton":
            pygame.draw.circle(screen, (255, 255, 0), (int(self.x), int(self.y)), 12)
            points = []
            size = 15
            for i in range(3):
                angle = math.radians(i * 120 + self.angle)
                px = self.x + size * math.cos(angle)
                py = self.y + size * math.sin(angle)
                points.append((px, py))
            pygame.draw.polygon(screen, self.color, points, 2)
            return
        
        if self.particle_type == "Deuterium":
            pygame.draw.circle(screen, (100, 100, 255), (int(self.x), int(self.y)), 15)
            points = []
            size = 20
            for i in range(4):
                angle = math.radians(i * 90 + self.angle)
                px = self.x + size * math.cos(angle)
                py = self.y + size * math.sin(angle)
                points.append((px, py))
            pygame.draw.polygon(screen, self.color, points, 2)
            return

        num_points = 6
        distortion = 1 
        points = generate_wave_shape(self.x, self.y, self.size, num_points, distortion, self.angle)
        
        if self.particle_type == "Neutron" and self.is_captured:
            final_color = (self.color[0] + 50, self.color[1] + 50, self.color[2] + 50)
            pygame.draw.polygon(screen, final_color, points)
        else:
            pygame.draw.polygon(screen, self.color, points)
        
        if self.particle_type != "Neutron" and self.particle_type != "Proton":
            field_radius = 50 + self.magnetic_field_strength * 100
            field_surface = pygame.Surface((field_radius * 2, field_radius * 2), pygame.SRCALPHA)
            alpha = 50 
            
            if "Anti" in self.particle_type: 
                field_color = (255, 0, 0, alpha) 
            elif self.particle_type == "Positron":
                field_color = (255, 165, 0, alpha)
            else: 
                field_color = (0, 0, 255, alpha) 

            pygame.draw.circle(field_surface, field_color, (field_radius, field_radius), field_radius)
            screen.blit(field_surface, (self.x - field_radius, self.y - field_radius))

# -----------------------
# Game logic
# -----------------------

class QuantumCollectorGame:
    def __init__(self):
        self.r = 4.0
        self.quantum_bias = 0.0
        self.fluctuations = []
        self.sparks = []
        self.stable_particles = []
        self.photons = []
        self.last_spawn_time = pygame.time.get_ticks()
        self.game_over = False
        self.mouse_pos = None
        self.particle_counts = {}
        self.spawn_counter = 0 
        self.sim = AerSimulator()
        self.matter_created = 0
        self.matter_stabilized = 0
        
    def get_color_for_state(self, state):
        if state == "Red": return (255, 0, 0)
        if state == "Green": return (0, 255, 0)
        if state == "Blue": return (0, 0, 255)
        if state == "Antired": return (0, 255, 255) 
        if state == "Antigreen": return (255, 0, 255) 
        if state == "Antiblue": return (255, 255, 0) 
        return (150, 150, 150)

    def get_anti_state_and_color(self, state):
        if state == "Red": return "Antired", (0, 255, 255)
        if state == "Antired": return "Red", (255, 0, 0)
        if state == "Green": return "Antigreen", (255, 0, 255)
        if state == "Antigreen": return "Green", (0, 255, 0)
        if state == "Blue": return "Antiblue", (255, 255, 0)
        if state == "Antiblue": return "Blue", (0, 0, 255)
        return "Neutral", (150, 150, 150)

    def interpret_branch(self, center_value):
        if center_value < 0.15: return "Antired"
        elif center_value < 0.30: return "Antigreen"
        elif center_value < 0.45: return "Antiblue" 
        elif center_value < 0.60: return "Blue"
        elif center_value < 0.75: return "Green"
        else: return "Red"

    def spawn_fluctuation(self):
        self.spawn_counter += 1
        if self.spawn_counter >= R_DECAY_INTERVAL:
            self.r = max(3.0, self.r - R_DECAY_RATE) 
            self.spawn_counter = 0
        
        branches = sample_branches_for_r(self.r, n_inits=80)
        if not branches:
            return
        
        centers, freqs = zip(*branches)
        
        new_fluctuation_center = random.choice(centers)
        outcome_state = self.interpret_branch(new_fluctuation_center)
        color = self.get_color_for_state(outcome_state)
        
        anti_state, anti_color = self.get_anti_state_and_color(outcome_state)
        chaos_level = random.uniform(0.0, 1.0) 
        
        x_pos = random.randint(100, WIDTH - 100)
        y_pos = random.randint(100, HEIGHT - 100)
        
        vx = random.uniform(-1, 1)
        vy = random.uniform(-1, 1)
        
        new_fluctuation = Fluctuation(x_pos - 50, y_pos - 50, new_fluctuation_center, color, self, chaos_level, vx=vx, vy=vy)
        self.fluctuations.append(new_fluctuation)

        anti_fluctuation = Fluctuation(x_pos + 50, y_pos + 50, new_fluctuation_center, anti_color, self, chaos_level, vx=-vx, vy=-vy)
        self.fluctuations.append(anti_fluctuation)

    def check_interactions(self, mouse_pressed):
        
        if mouse_pressed and self.mouse_pos:
            for particle in self.stable_particles:
                dist = math.hypot(particle.x - self.mouse_pos[0], particle.y - self.mouse_pos[1])
                force_magnitude = 1500 / (dist + 1)
                if dist < 150:
                    force_direction_x = (self.mouse_pos[0] - particle.x) / dist
                    force_direction_y = (self.mouse_pos[1] - particle.y) / dist
                    particle.vx += force_direction_x * force_magnitude * 0.005
                    particle.vy += force_direction_y * force_magnitude * 0.005

            for fluctuation in self.fluctuations:
                dist = math.hypot(fluctuation.x - self.mouse_pos[0], fluctuation.y - self.mouse_pos[1])
                force_magnitude = 1500 / (dist + 1)
                if dist < 150:
                    force_direction_x = (self.mouse_pos[0] - fluctuation.x) / dist
                    force_direction_y = (self.mouse_pos[1] - fluctuation.y) / dist
                    fluctuation.vx += force_direction_x * force_magnitude * 0.005
                    fluctuation.vy += force_direction_y * force_magnitude * 0.005
        
        # --- Lógica de Interação Eletromagnética e Gravitacional ---
        for i in range(len(self.stable_particles)):
            for j in range(i + 1, len(self.stable_particles)):
                p1 = self.stable_particles[i]
                p2 = self.stable_particles[j]

                dist = math.hypot(p1.x - p2.x, p1.y - p2.y)
                if dist == 0: continue
                
                # Interação Eletromagnética
                if p1.charge != 0 and p2.charge != 0:
                    force_em = (p1.charge * p2.charge * EM_CONSTANT) / (dist**2) 
                    p1.vx += force_em * (p2.x - p1.x) / dist
                    p1.vy += force_em * (p2.y - p1.y) / dist
                
                # Lógica de Força Nuclear Forte (para prótons e nêutrons)
                if p1.particle_type in ["Proton", "Neutron", "Deuterium"] and p2.particle_type in ["Proton", "Neutron", "Deuterium"]:
                    NUCLEAR_DISTANCE_THRESHOLD = NUCLEAR_THRESHOLD
                    NUCLEAR_ATTRACTION_CONSTANT = -2000 
                    
                    if dist < NUCLEAR_DISTANCE_THRESHOLD:
                        force_nuclear = (NUCLEAR_ATTRACTION_CONSTANT / dist)
                        p1.vx += force_nuclear * (p2.x - p1.x) / dist
                        p1.vy += force_nuclear * (p2.y - p1.y) / dist

                # Interação Gravitacional: Apenas para partículas sem carga (Neutrons, Hydrogens) e Flutuações
                if p1.charge == 0 and p2.charge == 0 and dist > 25:
                    force_grav = GRAVITY_CONSTANT / (dist**2)
                    p1.vx += force_grav * (p2.x - p1.x) / dist
                    p1.vy += force_grav * (p2.y - p1.y) / dist

        # Atração gravitacional entre partículas estáveis e flutuações
        if GRAVITY_CONSTANT > 0:
            for grav_source in self.stable_particles:
                if grav_source.particle_type in ["Hydrogen", "Proton"]:
                    for f_other in self.fluctuations:
                        dist = math.hypot(grav_source.x - f_other.x, grav_source.y - f_other.y)
                        if dist > 0:
                            force = GRAVITY_CONSTANT / (dist**2)
                            f_other.vx += force * (grav_source.x - f_other.x) / dist
                            f_other.vy += force * (grav_source.y - f_other.y) / dist

        fluctuations_to_remove = []
        new_fluctuations = []
        
        for i in range(len(self.fluctuations)):
            for j in range(i + 1, len(self.fluctuations)):
                f1 = self.fluctuations[i]
                f2 = self.fluctuations[j]
                if math.hypot(f1.x - f2.x, f1.y - f2.y) < f1.size + f2.size:
                    
                    if (f1.state.replace("Anti", "").lower() == f2.state.replace("Anti", "").lower() and f1.state != f2.state) and random.random() < 0.8:
                        self.stable_particles.append(StableParticle(f1.x, f1.y, (0, 255, 0), "Electron", vx=random.uniform(-1, 1), vy=random.uniform(-1, 1)))
                        self.stable_particles.append(StableParticle(f2.x, f2.y, (255, 165, 0), "Positron", vx=random.uniform(-1, 1), vy=random.uniform(-1, 1)))
                        self.matter_created += 2 # Nova partícula criada
                        fluctuations_to_remove.extend([f1, f2])
                        for _ in range(30):
                            self.sparks.append(QuantumSpark((f1.x + f2.x)/2, (f1.y + f2.y)/2, (255, 255, 255)))
                        continue
                    
                    if (f1.state == "Red" and f2.state == "Antigreen") or (f1.state == "Antigreen" and f2.state == "Red"):
                        new_vx = (f1.vx + f2.vx) / 2
                        new_vy = (f1.vy + f2.vy) / 2
                        self.stable_particles.append(StableParticle((f1.x + f2.x)/2, (f1.y + f2.y)/2, self.get_color_for_state("Red"), "Quark_RedAntigreen", vx=new_vx, vy=new_vy))
                        self.matter_created += 1 # Nova partícula criada
                        fluctuations_to_remove.extend([f1, f2])
                        continue
                    
                    elif (f1.state == "Blue" and f2.state == "Antigreen") or (f1.state == "Antigreen" and f2.state == "Blue"):
                        new_vx = (f1.vx + f2.vx) / 2
                        new_vy = (f1.vy + f2.vy) / 2
                        self.stable_particles.append(StableParticle((f1.x + f2.x)/2, (f1.y + f2.y)/2, self.get_color_for_state("Blue"), "Quark_BlueAntigreen", vx=new_vx, vy=new_vy))
                        self.matter_created += 1 # Nova partícula criada
                        fluctuations_to_remove.extend([f1, f2])
                        continue

                    elif (f1.state == "Green" and f2.state == "Antiblue") or (f1.state == "Antiblue" and f2.state == "Green"):
                        new_vx = (f1.vx + f2.vx) / 2
                        new_vy = (f1.vy + f2.y) / 2
                        self.stable_particles.append(StableParticle((f1.x + f2.x)/2, (f1.y + f2.y)/2, self.get_color_for_state("Green"), "Quark_GreenAntiblue", vx=new_vx, vy=new_vy))
                        self.matter_created += 1 # Nova partícula criada
                        fluctuations_to_remove.extend([f1, f2])
                        continue

                    diff = abs(f1.center_value - f2.center_value)
                    new_center_value = (f1.center_value + f2.center_value) / 2
                    
                    if diff > 0.5:
                        new_color = (int(random.uniform(0, 255)), int(random.uniform(0, 255)), int(random.uniform(0, 255)))
                        new_chaos = min(1.0, f1.chaos_level + f2.chaos_level)
                    else: 
                        new_color = (int((f1.color[0] + f2.color[0]) / 2), int((f1.color[1] + f2.color[1]) / 2), int((f1.color[2] + f2.color[2]) / 2))
                        new_chaos = max(0.0, f1.chaos_level + f2.chaos_level - 1)
                        
                    new_vx = (f1.vx + f2.vx) / 2
                    new_vy = (f1.vy + f2.vy) / 2

                    new_fluctuation = Fluctuation((f1.x + f2.x) / 2, (f1.y + f2.y) / 2, new_center_value, new_color, self, chaos_level=new_chaos, vx=new_vx, vy=new_vy)

                    if f1.quantum_circuit.num_qubits + f2.quantum_circuit.num_qubits <= 5: 
                        combined_circuit = QuantumCircuit(f1.quantum_circuit.num_qubits + f2.quantum_circuit.num_qubits, f1.quantum_circuit.num_qubits + f2.quantum_circuit.num_qubits)
                        combined_circuit = combined_circuit.compose(f1.quantum_circuit, qubits=range(f1.quantum_circuit.num_qubits))
                        combined_circuit = combined_circuit.compose(f2.quantum_circuit, qubits=range(f1.quantum_circuit.num_qubits, f1.quantum_circuit.num_qubits + f2.quantum_circuit.num_qubits))
                        combined_circuit.cx(0, 1)
                        new_fluctuation.quantum_circuit = combined_circuit
                    
                    new_fluctuations.append(new_fluctuation)
                    fluctuations_to_remove.extend([f1, f2])
                    for _ in range(20):
                        self.sparks.append(QuantumSpark((f1.x + f2.x) / 2, (f1.y + f2.y) / 2, (255, 255, 255)))
        
        for fluctuation in fluctuations_to_remove:
            if fluctuation in self.fluctuations:
                self.fluctuations.remove(fluctuation)

        self.fluctuations.extend(new_fluctuations)

        particles_to_remove = []
        new_particles = []

        for p1 in self.stable_particles:
            for p2 in self.stable_particles:
                if p1 == p2:
                    continue
                
                if (p1.particle_type == "Electron" and p2.particle_type == "Positron") or \
                   (p1.particle_type == "Positron" and p2.particle_type == "Electron"):
                    
                    dist = math.hypot(p1.x - p2.x, p1.y - p2.y)
                    if dist < p1.size + p2.size:
                        for _ in range(5):
                            self.photons.append(Photon((p1.x + p2.x) / 2, (p1.y + p2.y) / 2))
                        particles_to_remove.extend([p1, p2])
                        print("Aniquilação! Elétron e Pósitron se transformam em Fótons.")
                
                # --- Fusão de Próton e Nêutron para formar Deutério ---
                if (p1.particle_type == "Proton" and p2.particle_type == "Neutron") or \
                   (p1.particle_type == "Neutron" and p2.particle_type == "Proton"):
                    
                    dist = math.hypot(p1.x - p2.x, p1.y - p2.y)
                    combined_velocity = math.hypot(p1.vx + p2.vx, p1.vy + p2.vy)
                    
                    if dist < NUCLEAR_THRESHOLD and combined_velocity > 1:
                        particles_to_remove.extend([p1, p2])
                        new_particles.append(StableParticle(p1.x, p1.y, (100, 100, 255), "Deuterium"))
                        self.matter_stabilized += 1
                        print("Fusão Nuclear! Um núcleo de Deutério foi formado!")
                        continue
                
                # --- Formação de Átomo de Deutério ---
                if (p1.particle_type == "Deuterium" and p2.particle_type == "Electron") or \
                   (p1.particle_type == "Electron" and p2.particle_type == "Deuterium"):
                    
                    dist = math.hypot(p1.x - p2.x, p1.y - p2.y)
                    if dist < NUCLEAR_THRESHOLD + 10:
                        particles_to_remove.extend([p1, p2])
                        new_particles.append(StableParticle(p1.x, p1.y, (150, 150, 255), "Deuterium Atom"))
                        self.matter_stabilized += 1
                        print("Átomo de Deutério foi formado pela captura de um Elétron!")
                        continue

                if p1.particle_type.startswith("Quark_") and p2.particle_type.startswith("Quark_"):
                    dist = math.hypot(p1.x - p2.x, p1.y - p2.y)
                    if dist < p1.size + p2.size:
                        if (p1.particle_type == "Quark_RedAntigreen" and p2.particle_type == "Quark_BlueAntigreen") or \
                           (p1.particle_type == "Quark_BlueAntigreen" and p2.particle_type == "Quark_RedAntigreen"):
                            for _ in range(3):
                                self.photons.append(Photon((p1.x + p2.x) / 2, (p1.y + p2.y) / 2))
                            particles_to_remove.extend([p1, p2])
                            print("Aniquilação de Quarks para Fótons!")
                
                if p1.particle_type == "Neutron" and p2.particle_type == "Positron":
                    dist = math.hypot(p1.x - p2.x, p1.y - p2.y)
                    if dist < p1.size + p2.size:
                        particles_to_remove.extend([p1, p2])
                        new_particles.append(StableParticle(p1.x, p1.y, (255, 255, 0), "Proton"))
                        self.matter_stabilized += 1
                        print("Nêutron colide com Pósitron, virando um Próton!")

                if p1.particle_type == "Proton":
                    if p2.particle_type == "Electron":
                        dist = math.hypot(p1.x - p2.x, p1.y - p2.y)
                        
                        if dist < 100:
                            force_magnitude = 5 / (dist + 1)
                            force_x = (p2.x - p1.x) / dist * force_magnitude
                            force_y = (p2.y - p1.y) / dist * force_magnitude
                            p1.vx += force_x
                            p1.vy += force_y
                            p2.vx -= force_x
                            p2.vy -= force_y

                        if dist < p1.size + p2.size:
                            new_particles.append(StableParticle(p1.x, p1.y, (0, 0, 0), "Hydrogen"))
                            self.matter_stabilized += 1
                            particles_to_remove.extend([p1, p2])
                            print("Um átomo de Hidrogênio foi formado!")
        
        for p in particles_to_remove:
            if p in self.stable_particles:
                self.stable_particles.remove(p)
        self.stable_particles.extend(new_particles)
        
        self.check_for_neutron_formation()

    def check_for_neutron_formation(self):
        quarks = [p for p in self.stable_particles if p.particle_type.startswith("Quark_")]
        
        if len(quarks) >= 3:
            for i in range(len(quarks)):
                for j in range(i + 1, len(quarks)):
                    for k in range(j + 1, len(quarks)):
                        q1, q2, q3 = quarks[i], quarks[j], quarks[k]
                        
                        types = {q1.particle_type, q2.particle_type, q3.particle_type}
                        if len(types) == 3:
                            dist_ij = math.hypot(q1.x - q2.x, q1.y - q2.y)
                            dist_ik = math.hypot(q1.x - q3.x, q1.y - q3.y)
                            dist_jk = math.hypot(q2.x - q3.x, q2.y - q3.y)
                            
                            if dist_ij < 150 and dist_ik < 150 and dist_jk < 150:
                                neutron_x = statistics.mean([q1.x, q2.x, q3.x])
                                neutron_y = statistics.mean([q1.y, q2.y, q3.y])
                                neutron_vx = statistics.mean([q1.vx, q2.vx, q3.vx])
                                neutron_vy = statistics.mean([q1.vy, q2.vy, q3.vy])

                                self.stable_particles.remove(q1)
                                self.stable_particles.remove(q2)
                                self.stable_particles.remove(q3)
                                self.stable_particles.append(StableParticle(neutron_x, neutron_y, (100, 100, 100), "Neutron", 0, vx=neutron_vx, vy=neutron_vy))
                                self.matter_stabilized += 1
                                print("Um Nêutron foi formado!")
                                return
    
    def check_for_quantum_decay(self):
        particles_to_decay = []
        for p in self.stable_particles:
            if not p.is_long_lived and p.decay_countdown <= 0:
                qc = p.quantum_circuit
                circ = transpile(qc, self.sim, optimization_level=0)
                result = self.sim.run(circ, shots=1).result()
                counts = result.get_counts(circ)
                
                if '1' in counts:
                    print(f"Partícula {p.particle_type} decaiu!")
                    particles_to_decay.append(p)
        
        for p in particles_to_decay:
            if p.particle_type.startswith("Quark_"):
                self.stable_particles.remove(p)
                self.stable_particles.append(StableParticle(p.x, p.y, (0, 255, 0), "Electron", vx=random.uniform(-1, 1), vy=random.uniform(-1, 1)))
                self.stable_particles.append(StableParticle(p.x, p.y, (255, 255, 0), "Proton", vx=random.uniform(-1, 1), vy=random.uniform(-1, 1)))


# -----------------------
# Visual (pygame)
# -----------------------

pygame.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT))

pygame.display.set_caption("Laboratório Quântico")
font = pygame.font.SysFont("Arial", 20)
clock = pygame.time.Clock()

def draw_hud(game):
    hud_x_offset = 200
    y_offset = 130
    
    # Título
    mission_title = font.render("LABORATÓRIO: Manipule Partículas", True, (0, 255, 255))
    screen.blit(mission_title, (hud_x_offset, y_offset))
    y_offset += 40
    
    # Nível de Caos
    r_text = font.render(f"Nível de Caos (r): {game.r:.4f}", True, (255, 255, 255))
    screen.blit(r_text, (hud_x_offset, y_offset))
    y_offset += 40

    # Contagem de Partículas
    counts = {}
    for p in game.stable_particles:
        counts[p.particle_type] = counts.get(p.particle_type, 0) + 1

    # Partículas Estáveis
    stable_title = font.render("Partículas Estáveis", True, (0, 255, 255))
    screen.blit(stable_title, (hud_x_offset, y_offset))
    y_offset += 30
    for p_type in ["Proton", "Neutron", "Deuterium", "Deuterium Atom", "Hydrogen", "Electron", "Positron"]:
        count = counts.get(p_type, 0)
        text = font.render(f"  {p_type}: {count}", True, (200, 200, 200))
        screen.blit(text, (hud_x_offset, y_offset))
        y_offset += 25
    
    y_offset += 15

    # Quarks
    quark_title = font.render("Quarks", True, (0, 255, 255))
    screen.blit(quark_title, (hud_x_offset, y_offset))
    y_offset += 30
    quark_types = ["Quark_RedAntigreen", "Quark_BlueAntigreen", "Quark_GreenAntiblue"]
    for q_type in quark_types:
        count = counts.get(q_type, 0)
        text = font.render(f"  {q_type.replace('Quark_', '')}: {count}", True, (150, 150, 150))
        screen.blit(text, (hud_x_offset, y_offset))
        y_offset += 25

    # Nova métrica
    y_offset += 40
    metric_title = font.render("Métricas de Estabilização", True, (0, 255, 255))
    screen.blit(metric_title, (hud_x_offset, y_offset))
    y_offset += 30
    
    ratio = 0
    if game.matter_created > 0:
        ratio = game.matter_stabilized / game.matter_created * 100
    
    matter_text = font.render(f"Matéria Criada: {game.matter_created}", True, (200, 200, 200))
    screen.blit(matter_text, (hud_x_offset, y_offset))
    y_offset += 25
    
    stabilized_text = font.render(f"Matéria Estabilizada: {game.matter_stabilized}", True, (200, 200, 200))
    screen.blit(stabilized_text, (hud_x_offset, y_offset))
    y_offset += 25
    
    ratio_text = font.render(f"Taxa de Estabilização: {ratio:.2f}%", True, (0, 255, 0) if ratio > 0 else (200, 200, 200))
    screen.blit(ratio_text, (hud_x_offset, y_offset))

    # Dica
    tip_text = font.render("DICA: Arraste 3 quarks de cores diferentes para que eles colidam e formem um Nêutron!", True, (255, 255, 0))
    text_rect = tip_text.get_rect(center=(WIDTH // 2, HEIGHT - 30))
    screen.blit(tip_text, text_rect)

def main():
    game = QuantumCollectorGame()
    running = True
    mouse_pressed = False
    
    # Adicione a variável para rastrear o estado do mapa logístico
    game.logistic_x = random.uniform(0.1, 0.9)
    
    # Adicione a variável r para o nível de caos (se ainda não estiver na classe)
    # Se já estiver, remova esta linha
    game.r = 4.0 

    while running:
        current_time = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pressed = True
                game.mouse_pos = pygame.mouse.get_pos()
            
            if event.type == pygame.MOUSEBUTTONUP:
                mouse_pressed = False
                game.mouse_pos = None
        
        # --- Nova Lógica de Spawn ---
        # Atualiza o valor do mapa logístico a cada frame
        game.logistic_x = game.r * game.logistic_x * (1 - game.logistic_x)

        # Usa a probabilidade do mapa logístico para decidir se cria uma flutuação
        # O fator de 0.5 é um multiplicador para ajustar a frequência de spawn
        # Sinta-se à vontade para ajustar esse valor para o que funcionar melhor
        if random.random() < game.logistic_x * SPAWN_MULTIPLIER:
            game.spawn_fluctuation()

        game.check_interactions(mouse_pressed)
        game.check_for_quantum_decay()

        for f in game.fluctuations:
            f.update()
        for p in game.stable_particles:
            p.update()
        for s in game.sparks:
            s.update()
        for ph in game.photons:
            ph.update()

        # Desenho
        screen.fill(BG_COLOR)
        for f in game.fluctuations:
            f.draw(screen)
        for p in game.stable_particles:
            p.draw(screen)
        for s in game.sparks:
            s.draw(screen)
        for ph in game.photons:
            ph.draw(screen)

        game.sparks = [s for s in game.sparks if s.lifetime > 0]
        game.photons = [ph for ph in game.photons if ph.lifetime > 0]

        draw_hud(game)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()