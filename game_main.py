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

# Reduza este valor se o lag persistir.
MAX_OBJECTS = 1000
PHOTON_SPEED = 50

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
        self.size = 3
        self.color = (255, 255, 0) # Amarelo, representando a luz
        self.lifetime = PHOTON_LIFETIME

        # --- CORREÇÃO DE VELOCIDADE ---
        # 1. Gera um ângulo de ejeção aleatório (isótropo)
        angle = random.uniform(0, 2 * math.pi)
        
        # 2. Atribui a velocidade ALTA e CONSTANTE
        self.vx = PHOTON_SPEED * math.cos(angle)
        self.vy = PHOTON_SPEED * math.sin(angle)

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

        #self.quantum_circuit = self.create_quantum_circuit(self.state)
        self.quantum_circuit = None
        self.creation_time = pygame.time.get_ticks()
   
    def get_complexity_proxy(self):
        """
        Substitui f.quantum_circuit.num_qubits para fins de desempenho.
        Retorna um valor constante seguro se o circuito for None.
        """
        # Como o circuito padrão teria 1 qubit, retornamos 1
        if self.quantum_circuit is None:
            return 1 
        else:
            return self.quantum_circuit.num_qubits

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
    def __init__(self, x, y, color, particle_type, magnetic_field_strength=0.1, vx=0, vy=0, is_captured=False, game_ref=None):
        self.x = x
        self.y = y
        self.color = color
        self.particle_type = particle_type
        self.magnetic_field_strength = magnetic_field_strength
        self.angle = random.uniform(0, 360)
        self.spin_speed = random.uniform(-3, 3)
        self.vx = vx
        self.vy = vy
        self.is_captured = is_captured
        self.game = game_ref # Referência para o objeto Game (para decaimento)

        # --- Atributos Padrão ---
        self.mass = 1.0 # Base de massa
        self.charge = 0.0
        self.size = 10
        self.is_dead = False
        
        # --- Lógica de Vida e Decaimento ---
        self.lifetime = 0
        self.is_long_lived = True
        self.decay_countdown = 0

        # --- Lógica de Criação (is_new) para evitar aniquilação imediata ---
        self.is_new = False
        self.new_timer = 60 # 1 segundo a 60 FPS
        self.blink_state = True
        
        # --- Definição Centralizada de Atributos ---
        self.set_attributes()
        
        # Lógica de decaimento Quântico (Quark)
        if self.particle_type.startswith("Quark_"):
            self.is_long_lived = False
            # self.decay_countdown = random.randint(QUARK_DECAY_MAX_LIFETIME // 3, QUARK_DECAY_MAX_LIFETIME)
            # self.decay_chance = 0.5 
            # self.quantum_circuit = self.create_decay_circuit()

    def set_attributes(self):
        """Define massa, carga, cor e tamanho com base no tipo de partícula."""
        
        # --- BÁRIONS (Prótons, Nêutrons, Lambda) ---
        if self.particle_type in ["Proton", "Neutron", "Lambda", "Deuterium"]:
            self.mass = 1836.0 
            self.size = 10 
            if self.particle_type == "Proton": self.charge = 1.0; self.color = (255, 255, 0)
            if self.particle_type == "Neutron": self.charge = 0.0; self.color = (100, 100, 100)
            if self.particle_type == "Lambda": self.charge = 0.0; self.color = (150, 50, 150) # Cor Strange
            if self.particle_type == "Deuterium": self.charge = 1.0; self.color = (100, 100, 255)
        
        # --- LÉPTONS ---
        elif self.particle_type == "Electron":
            self.mass = 1.0; self.charge = -1.0; self.size = 3; self.color = (0, 255, 0)
        elif self.particle_type == "Positron":
            self.mass = 1.0; self.charge = 1.0; self.size = 3; self.color = (255, 165, 0)
        elif self.particle_type == "Muon_MINUS":
            self.mass = 207.0; self.charge = -1.0; self.color = (0, 255, 255); self.size = 5; self.is_long_lived = False

        # --- MÉSons (Píon) ---
        elif self.particle_type == "Pion_MINUS":
            self.mass = 273.0; self.charge = -1.0; self.size = 6; self.color = (255, 100, 100); self.is_long_lived = False

        # --- ÁTOMOS ---
        elif self.particle_type in ["Hydrogen Atom", "Deuterium Atom"]:
            self.mass = 1837.0; self.charge = 0.0; self.size = 15; self.is_long_lived = True

        # --- QUARKS ---
        elif self.particle_type.startswith("Quark_"):
            self.is_long_lived = False; self.size = 4
            if self.particle_type == "Quark_UP": self.charge = 2/3
            elif self.particle_type == "Quark_DOWN": self.charge = -1/3
            # A cor do Quark deve ser definida pelo estado de cor (Red, Green, Blue)


    def create_decay_circuit(self):
        # Implementação do Qiskit (omito o código Qiskit aqui)
        pass

    def update(self):
        if self.is_dead:
            return 
            
        self.angle += self.spin_speed
        
        # 1. Aplica o Movimento
        if not self.is_captured:
            # self.vx *= 0.985 # Damping
            # self.vy *= 0.985 # Damping
            self.x += self.vx
            self.y += self.vy

        # 2. Lógica de Reversão de Borda (Wrap-around)
        # Assume que WIDTH e HEIGHT estão definidos globalmente
        # if self.x < 0: self.x = WIDTH
        # elif self.x > WIDTH: self.x = 0
        # if self.y < 0: self.y = HEIGHT
        # elif self.y > HEIGHT: self.y = 0
            
        # 3. Contagem regressiva para partículas instáveis
        if not self.is_long_lived:
            self.decay_countdown -= 1
        
        # 4. Lógica de Piscar (Invulnerabilidade de Criação)
        if self.is_new:
            self.new_timer -= 1
            if self.new_timer % 10 == 0:
                self.blink_state = not self.blink_state
            if self.new_timer <= 0:
                self.is_new = False
                self.blink_state = True
                
        self.lifetime += 1

    # REMOVIDO: A função determine_size, pois a lógica foi para set_attributes
    # REMOVIDO: A função determine_color, pois a lógica foi para set_attributes

    def draw(self, screen):
        # Lembre-se: esta função requer o módulo pygame e as constantes de cor e tamanho.
        
        # Nao desenha se estiver piscando
        if self.is_new and not self.blink_state:
            return

        # 1. Desenho para Átomos
        if self.particle_type == "Hydrogen Atom":
            pygame.draw.circle(screen, (100, 100, 100), (int(self.x), int(self.y)), 12)
            pygame.draw.circle(screen, (50, 50, 50), (int(self.x), int(self.y)), 25, 1)
            orbit_angle = pygame.time.get_ticks() * 0.1
            electron_x = self.x + 25 * math.cos(math.radians(orbit_angle))
            electron_y = self.y + 25 * math.sin(math.radians(orbit_angle))
            pygame.draw.circle(screen, (0, 255, 0), (int(electron_x), int(electron_y)), 5)
            return

        if self.particle_type == "Deuterium Atom":
            pygame.draw.circle(screen, (150, 150, 255), (int(self.x), int(self.y)), 15)
            pygame.draw.circle(screen, (50, 50, 50), (int(self.x), int(self.y)), 30, 1)
            orbit_angle = pygame.time.get_ticks() * 0.1
            electron_x = self.x + 30 * math.cos(math.radians(orbit_angle))
            electron_y = self.y + 30 * math.sin(math.radians(orbit_angle))
            pygame.draw.circle(screen, (0, 255, 0), (int(electron_x), int(electron_y)), 5)
            return
        
        # 2. Desenho para Lambda (Bárion Estranho)
        if self.particle_type == "Lambda":
            pygame.draw.circle(screen, (150, 50, 150), (int(self.x), int(self.y)), 15)
            points = []
            size = 18 
            for i in range(3):
                angle = math.radians(i * 120 + self.angle + 180)
                px = self.x + size * math.cos(angle)
                py = self.y + size * math.sin(angle)
                points.append((px, py))
            pygame.draw.polygon(screen, (0, 255, 255), points) 
            return
        
        # 3. Desenho para Próton
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
            # Continua para desenhar o campo EM
        
        # 4. Desenho para Deutério (Núcleo)
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
            # Continua para desenhar o campo EM
            
        # 5. Desenho para Nêutron (usando forma de onda, se aplicável)
        if self.particle_type == "Neutron":
            num_points = 6
            distortion = 1 
            # points = generate_wave_shape(self.x, self.y, self.size, num_points, distortion, self.angle)
            
            # Substitua a chamada acima por um desenho simples, se generate_wave_shape não for fornecida:
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.size) 
            
            if self.is_captured:
                 final_color = (self.color[0] + 50, self.color[1] + 50, self.color[2] + 50)
                 pygame.draw.circle(screen, final_color, (int(self.x), int(self.y)), self.size + 2)


        # 6. Desenho Genérico (Léptons, Mésons e Quarks)
        # Inclui: Electron, Positron, Muon_MINUS, Pion_MINUS e Quarks
        if self.particle_type in ["Electron", "Positron", "Muon_MINUS", "Pion_MINUS"] or self.particle_type.startswith("Quark_"):
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.size)
            
        # 7. Desenho do Campo Eletromagnético (Aplica-se a todas as carregadas não atômicas)
        if self.charge != 0 and not self.particle_type.endswith("Atom"):
            field_radius = self.size * 2 + self.magnetic_field_strength * 10
            field_color = (0, 0, 255) # Azul padrão para carga negativa
            if self.charge > 0:
                field_color = (255, 165, 0) # Laranja para carga positiva
            
            pygame.draw.circle(screen, field_color, 
                               (int(self.x), int(self.y)), 
                               int(field_radius), 
                               1)
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
        self.force_update_counter = 0
        self.baryon_check_counter = 0 
        self.quantum_decay_counter = 0
        self.message_log = []
        self.max_messages = 5 # Limita o número de linhas exibidas na tela
        self.message_duration = 300 # Tempo de vida da mensagem (em frames)

    def add_message(self, text):
        """Adiciona uma nova mensagem ao log com um contador de frames."""
        self.message_log.append({"text": text, "timer": self.message_duration})
        
        # Limita o log para manter apenas as mensagens mais recentes
        if len(self.message_log) > self.max_messages * 2: # Limite um pouco maior para evitar picos
            self.message_log = self.message_log[-self.max_messages:]
        
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
        # 30% chance total para Antileptons (flutuações que formam elétrons/pósitrons)
        if center_value < 0.1: 
            return "Antired"
        elif center_value < 0.2: 
            return "Antigreen"
        elif center_value < 0.3: 
            return "Antiblue" 
        
        # 30% chance para Quark UP (essencial para Prótons e Nêutrons)
        elif center_value < 0.6: 
            return "Red"   
        
        # 10% chance total para Quark DOWN (o mais necessário para Nêutrons)
        elif center_value < 0.7: 
            return "Blue"  # 20% aqui
        
        # 20% chance para Quark STRANGE (para manter a variedade, mas não dominante)
        elif center_value < 0.9: 
            return "Green" 
        
        # 10% extra chance para Quark DOWN (garante a proporção 4:1 de D:U)
        else: 
            return "Blue"

    def spawn_fluctuation(self):
        self.spawn_counter += 1
        if len(self.fluctuations) + len(self.stable_particles) >= MAX_OBJECTS:
             return
        
        if self.spawn_counter >= R_DECAY_INTERVAL:
            self.r = max(3.0, self.r - R_DECAY_RATE) 
            self.spawn_counter = 0
        
        branches = sample_branches_for_r(self.r, n_inits=80)
        if not branches:
            return
        
        centers, freqs = zip(*branches)
        
        # A nova lógica para favorecer a criação de quarks down foi adicionada aqui
        # Ajustando a lógica de escolha para dar peso a "Blue" (Quark Down)
        # Assumindo que o "Blue" é o Quark_DOWN, a probabilidade está agora maior
        if random.random() < 0.5: # 50% de chance de priorizar quarks
            quark_centers = [c for c in centers if self.interpret_branch(c) in ["Red", "Blue", "Green"]]
            if quark_centers:
                new_fluctuation_center = random.choice(quark_centers)
                outcome_state = self.interpret_branch(new_fluctuation_center)
            else:
                new_fluctuation_center = random.choice(centers)
                outcome_state = self.interpret_branch(new_fluctuation_center)
        else:
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

        new_log = []
        for msg in self.message_log:
            # Diminui o timer (countdown)
            msg['timer'] -= 1
            
            # Mantém apenas as mensagens que ainda têm tempo de vida
            if msg['timer'] > 0:
                new_log.append(msg)

        self.message_log = new_log
        
        # Lógica de Interação com o Mouse (Sem Alterações)
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
        FORCE_UPDATE_FREQUENCY = 3 # Recalcula forças a cada 3 frames

        self.force_update_counter += 1
        
        # Note: EM_CONSTANT, GRAVITY_CONSTANT, NUCLEAR_THRESHOLD precisam estar definidos (do .env)
        if self.force_update_counter % FORCE_UPDATE_FREQUENCY == 0:
            self.force_update_counter = 0
            for i in range(len(self.stable_particles)):
                for j in range(i + 1, len(self.stable_particles)):
                    p1 = self.stable_particles[i]
                    p2 = self.stable_particles[j]

                    dist = math.hypot(p1.x - p2.x, p1.y - p2.y)
                    if dist == 0: continue
                    
                    # Interação Eletromagnética
                    if p1.charge != 0 and p2.charge != 0:
                        safe_dist = max(dist, 5.0) 
                        
                        # Cálculo da magnitude da força (já com o sinal de atração/repulsão)
                        force_em_mag = (p1.charge * p2.charge * EM_CONSTANT) / (safe_dist**2)
                        
                        # Vetor de Força (aponta de p1 para p2, escalado pela magnitude)
                        force_x = force_em_mag * (p2.x - p1.x) / dist
                        force_y = force_em_mag * (p2.y - p1.y) / dist
                        
                        # CORREÇÃO CRÍTICA DO SINAL:
                        # Aceleração de p1: Aplica-se o vetor de força INVERSO
                        p1.vx -= force_x
                        p1.vy -= force_y
                        
                        # Aceleração de p2: Aplica-se o vetor de força ORIGINAL
                        p2.vx += force_x
                        p2.vy += force_y
                    
                    # Lógica de Força Nuclear Forte (para prótons e nêutrons)
                    if p1.particle_type in ["Proton", "Neutron"] and p2.particle_type in ["Proton", "Neutron"]:
                        NUCLEAR_DISTANCE_THRESHOLD = NUCLEAR_THRESHOLD
                        NUCLEAR_ATTRACTION_CONSTANT = -2000 
                        
                        if dist < NUCLEAR_DISTANCE_THRESHOLD:
                            force_nuclear = (NUCLEAR_ATTRACTION_CONSTANT / dist)
                            force_x = force_nuclear * (p2.x - p1.x) / dist
                            force_y = force_nuclear * (p2.y - p1.y) / dist
                            p1.vx += force_x
                            p1.vy += force_y
                            p2.vx -= force_x
                            p2.vy -= force_y

                    # Interação Gravitacional
                    if p1.charge == 0 and p2.charge == 0 and dist > 25:
                        force_grav = GRAVITY_CONSTANT / (dist**2)
                        force_x = force_grav * (p2.x - p1.x) / dist
                        force_y = force_grav * (p2.y - p1.y) / dist
                        p1.vx += force_x
                        p1.vy += force_y
                        p2.vx -= force_x
                        p2.vy -= force_y
            
        # Atração gravitacional entre partículas estáveis e flutuações
        if GRAVITY_CONSTANT > 0:
            for grav_source in self.stable_particles:
                if grav_source.particle_type in ["Hydrogen Aton", "Proton", "Neutron","Deuterium", "Deuterium Atom"]:
                    for f_other in self.fluctuations:
                        dist = math.hypot(grav_source.x - f_other.x, grav_source.y - f_other.y)
                        if dist > 0:
                            force = GRAVITY_CONSTANT / (dist**2)
                            f_other.vx += force * (grav_source.x - f_other.x) / dist
                            f_other.vy += force * (grav_source.y - f_other.y) / dist


        particles_to_remove = []
        new_particles = []
        
        self.check_for_baryon_formation()

        # --- Lógica de Colisão de Partículas Estáveis (Corrigida) ---
        for i in range(len(self.stable_particles)):
            for j in range(i + 1, len(self.stable_particles)):
                p1 = self.stable_particles[i]
                p2 = self.stable_particles[j]
                
                dist = math.hypot(p1.x - p2.x, p1.y - p2.y)
                if dist < p1.size + p2.size:
                    
                    # 1. Aniquilação de Elétron-Pósitron
                    if (p1.particle_type == "Electron" and p2.particle_type == "Positron") or \
                       (p1.particle_type == "Positron" and p2.particle_type == "Electron"):
                        for _ in range(5):
                            self.photons.append(Photon((p1.x + p2.x) / 2, (p1.y + p2.y) / 2))
                        particles_to_remove.extend([p1, p2])
                        print("Aniquilação! Elétron e Pósitron se transformam em Fótons.")
                        self.add_message("Aniquilação! Elétron e Pósitron se transformam em Fótons.")
                        continue
                    
                    # 2. Fusão de Próton e Nêutron para formar Deutério (PRIORIDADE)
                    if (p1.particle_type == "Proton" and p2.particle_type == "Neutron") or \
                       (p1.particle_type == "Neutron" and p2.particle_type == "Proton"):
                        combined_velocity = math.hypot(p1.vx + p2.vx, p1.vy + p2.vy)
                        if dist < NUCLEAR_THRESHOLD and combined_velocity > 1:
                            particles_to_remove.extend([p1, p2])
                            new_particles.append(StableParticle(p1.x, p1.y, (100, 100, 255), "Deuterium"))
                            self.matter_stabilized += 1
                            print("Fusão Nuclear! Um núcleo de Deutério foi formado!")
                            self.add_message("Fusão Nuclear! Um núcleo de Deutério foi formado!")
                            continue
                            
                    # 3. Formação de Átomo de Hidrogênio
                    if (p1.particle_type == "Proton" and p2.particle_type == "Electron") or \
                       (p1.particle_type == "Electron" and p2.particle_type == "Proton"):
                        if dist < NUCLEAR_THRESHOLD + 10:
                            particles_to_remove.extend([p1, p2])
                            new_particles.append(StableParticle(p1.x, p1.y, (255, 255, 255), "Hydrogen Atom"))
                            self.matter_stabilized += 1
                            print("Um átomo de Hidrogênio foi formado!")
                            self.add_message("Um átomo de Hidrogênio foi formado!")
                            continue

                    # 4. Formação de Átomo de Deutério
                    if (p1.particle_type == "Deuterium" and p2.particle_type == "Electron") or \
                       (p1.particle_type == "Electron" and p2.particle_type == "Deuterium"):
                        if dist < NUCLEAR_THRESHOLD + 10:
                            particles_to_remove.extend([p1, p2])
                            new_particles.append(StableParticle(p1.x, p1.y, (150, 150, 255), "Deuterium Atom"))
                            self.matter_stabilized += 1
                            print("Átomo de Deutério foi formado pela captura de um Elétron!")
                            self.add_message("Átomo de Deutério foi formado pela captura de um Elétron!")
                            continue
                            
        # Aplica a remoção e adição de partículas estáveis
        for p in particles_to_remove:
            if p in self.stable_particles:
                self.stable_particles.remove(p)
        self.stable_particles.extend(new_particles)

        # --- Lógica de interação entre flutuações ---
        fluctuations_to_remove_set = set()
        new_fluctuations = []
        
        for i in range(len(self.fluctuations)):
            for j in range(i + 1, len(self.fluctuations)):
                f1 = self.fluctuations[i]
                f2 = self.fluctuations[j]
                
                # Pula flutuações já marcadas para remoção
                if f1 in fluctuations_to_remove_set or f2 in fluctuations_to_remove_set:
                    continue
                    
                if math.hypot(f1.x - f2.x, f1.y - f2.y) < f1.size + f2.size:
                    
                    # 1. Aniquilação de Flutuação (Matéria + Anti-Matéria)
                    if (f1.state.replace("Anti", "").lower() == f2.state.replace("Anti", "").lower() and f1.state != f2.state) and random.random() < 0.8:
                        
                        # 1. GERAÇÃO DE ÂNGULO E VELOCIDADE
                        # Gera um ângulo de ejeção aleatório (0 a 360 graus)
                        angle = random.uniform(0, 2 * math.pi) 
                        # Define a magnitude da velocidade (o "espirro" suave)
                        speed_magnitude = random.uniform(1, 2) 
                        
                        # 2. CÁLCULO DAS VELOCIDADES
                        # Elétron: Usa o ângulo gerado (Vx e Vy positivos/negativos dependem do seno/cosseno do ângulo)
                        e_vx = speed_magnitude * math.cos(angle)
                        e_vy = speed_magnitude * math.sin(angle)
                        
                        # Pósitron: Usa o ângulo OPOSITO (adicionamos PI = 180 graus), garantindo que seja radialmente oposto
                        p_vx = speed_magnitude * math.cos(angle + math.pi)
                        p_vy = speed_magnitude * math.sin(angle + math.pi)
                        
                        # 3. CRIAÇÃO DO ELÉTRON 
                        self.stable_particles.append(StableParticle(f1.x, f1.y, (0, 255, 0), "Electron", 
                                                                vx=e_vx, 
                                                                vy=e_vy)) 
                        
                        # 4. CRIAÇÃO DO PÓSITRON
                        self.stable_particles.append(StableParticle(f2.x, f2.y, (255, 165, 0), "Positron", 
                                                                vx=p_vx, 
                                                                vy=p_vy))
                        
                        self.matter_created += 2
                        fluctuations_to_remove_set.add(f1)
                        fluctuations_to_remove_set.add(f2)
                        print("Aniquilação de Flutuação (Matéria + Anti-Matéria) -> Matéria Sobrevivente")
                        self.add_message("Aniquilação de Flutuação (Matéria + Anti-Matéria) -> Matéria Sobrevivente")
                        for _ in range(30):
                            self.sparks.append(QuantumSpark((f1.x + f2.x)/2, (f1.y + f2.y)/2, (255, 255, 255)))
                        continue
                        
                    # 2. Formação de Quark UP (Red + Antigreen)
                    elif (f1.state == "Red" and f2.state == "Antigreen") or (f1.state == "Antigreen" and f2.state == "Red"):
                        new_vx = (f1.vx + f2.vx) / 2
                        new_vy = (f1.vy + f2.vy) / 2
                        self.stable_particles.append(StableParticle((f1.x + f2.x)/2, (f1.y + f2.y)/2, self.get_color_for_state("Red"), "Quark_UP", vx=new_vx, vy=new_vy))
                        self.matter_created += 1
                        fluctuations_to_remove_set.add(f1)
                        fluctuations_to_remove_set.add(f2)
                        continue
                        
                    # 3. Formação de Quark DOWN (Blue + Antigreen)
                    elif (f1.state == "Blue" and f2.state == "Antigreen") or (f1.state == "Antigreen" and f2.state == "Blue"):
                        new_vx = (f1.vx + f2.vx) / 2
                        new_vy = (f1.vy + f2.vy) / 2
                        self.stable_particles.append(StableParticle((f1.x + f2.x)/2, (f1.y + f2.y)/2, self.get_color_for_state("Blue"), "Quark_DOWN", vx=new_vx, vy=new_vy))
                        self.matter_created += 1
                        fluctuations_to_remove_set.add(f1)
                        fluctuations_to_remove_set.add(f2)
                        continue

                    # 4. Formação de Quark STRANGE (Green + Antiblue)
                    elif (f1.state == "Green" and f2.state == "Antiblue") or (f1.state == "Antiblue" and f2.state == "Green"):
                        new_vx = (f1.vx + f2.vx) / 2
                        # CORREÇÃO: f2.y trocado para f2.vy
                        new_vy = (f1.vy + f2.vy) / 2 
                        self.stable_particles.append(StableParticle((f1.x + f2.x)/2, (f1.y + f2.y)/2, self.get_color_for_state("Green"), "Quark_STRANGE", vx=new_vx, vy=new_vy))
                        self.matter_created += 1
                        fluctuations_to_remove_set.add(f1)
                        fluctuations_to_remove_set.add(f2)
                        #print("Quark Strange formado!")
                        continue

                    # 5. Fusão Caótica
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

                    # CORREÇÃO DE PERFORMANCE/ERRO: Usa proxy e protege o bloco Qiskit
                    if f1.get_complexity_proxy() + f2.get_complexity_proxy() <= 5: 
                        if f1.quantum_circuit is not None and f2.quantum_circuit is not None:
                            combined_circuit = QuantumCircuit(f1.quantum_circuit.num_qubits + f2.quantum_circuit.num_qubits, f1.quantum_circuit.num_qubits + f2.quantum_circuit.num_qubits)
                            combined_circuit = combined_circuit.compose(f1.quantum_circuit, qubits=range(f1.quantum_circuit.num_qubits))
                            combined_circuit = combined_circuit.compose(f2.quantum_circuit, qubits=range(f1.quantum_circuit.num_qubits, f1.quantum_circuit.num_qubits + f2.quantum_circuit.num_qubits))
                            combined_circuit.cx(0, 1)
                            new_fluctuation.quantum_circuit = combined_circuit
                    
                    new_fluctuations.append(new_fluctuation)
                    fluctuations_to_remove_set.add(f1)
                    fluctuations_to_remove_set.add(f2)
                    
                    for _ in range(20):
                        self.sparks.append(QuantumSpark((f1.x + f2.x) / 2, (f1.y + f2.y) / 2, (255, 255, 255)))
        
        # Remoção de flutuações marcadas
        for fluctuation in fluctuations_to_remove_set:
            if fluctuation in self.fluctuations:
                self.fluctuations.remove(fluctuation)

        self.fluctuations.extend(new_fluctuations)


# NOVO: Implementação completa da formação de bárions, incluindo Lambda
    def check_for_baryon_formation(self):
        quarks = [p for p in self.stable_particles if p.particle_type.startswith("Quark_")]
        
        particles_to_remove = []
        new_particles = []
        
        # Itera sobre todos os trios de quarks para checar por combinações
        for i in range(len(quarks)):
            for j in range(i + 1, len(quarks)):
                for k in range(j + 1, len(quarks)):
                    q1, q2, q3 = quarks[i], quarks[j], quarks[k]
                    
                    # Simples verificação de proximidade (dentro de 3x o NUCLEAR_THRESHOLD)
                    center_x = (q1.x + q2.x + q3.x) / 3
                    center_y = (q1.y + q2.y + q3.y) / 3
                    
                    if math.hypot(q1.x - center_x, q1.y - center_y) < NUCLEAR_THRESHOLD * 3 and \
                       math.hypot(q2.x - center_x, q2.y - center_y) < NUCLEAR_THRESHOLD * 3 and \
                       math.hypot(q3.x - center_x, q3.y - center_y) < NUCLEAR_THRESHOLD * 3:
                        
                        # Usa um multiset para verificar a composição do trio
                        types = sorted([q1.particle_type, q2.particle_type, q3.particle_type])
                        
                        # Evita processar quarks que já foram marcados para remoção
                        if q1 in particles_to_remove or q2 in particles_to_remove or q3 in particles_to_remove:
                            continue

                        # --- Lambda Baryon (Up + Down + Strange) ---
                        if types == ['Quark_DOWN', 'Quark_STRANGE', 'Quark_UP']:
                            particles_to_remove.extend([q1, q2, q3])
                            avg_vx = (q1.vx + q2.vx + q3.vx) / 3
                            avg_vy = (q1.vy + q2.vy + q3.vy) / 3
                            # Cor roxa para o Lambda (UDS, carga zero)
                            new_particles.append(StableParticle(center_x, center_y, (180, 0, 180), "Lambda", vx=avg_vx, vy=avg_vy))
                            self.matter_stabilized += 1
                            print("Bárion Lambda (Up, Down, Strange) formado!")
                            self.add_message("Bárion Lambda (Up, Down, Strange) formado!")
                            
                        # --- Proton (Up + Up + Down) ---
                        elif types == ['Quark_DOWN', 'Quark_UP', 'Quark_UP']: 
                            particles_to_remove.extend([q1, q2, q3])
                            avg_vx = (q1.vx + q2.vx + q3.vx) / 3
                            avg_vy = (q1.vy + q2.vy + q3.vy) / 3
                            # Cor amarela para o Próton (UUD, carga +1)
                            new_particles.append(StableParticle(center_x, center_y, (255, 255, 0), "Proton", vx=avg_vx, vy=avg_vy))
                            self.matter_stabilized += 1
                            print("Próton (Up, Up, Down) formado!")
                            self.add_message("Próton (Up, Up, Down) formado!")
                            
                        # --- Neutron (Up + Down + Down) ---
                        elif types == ['Quark_DOWN', 'Quark_DOWN', 'Quark_UP']:
                            particles_to_remove.extend([q1, q2, q3])
                            avg_vx = (q1.vx + q2.vx + q3.vx) / 3
                            avg_vy = (q1.vy + q2.vy + q3.vy) / 3
                            # Cor cinza para o Nêutron (UDD, carga 0)
                            new_particles.append(StableParticle(center_x, center_y, (150, 150, 150), "Neutron", vx=avg_vx, vy=avg_vy))
                            self.matter_stabilized += 1
                            print("Nêutron (Up, Down, Down) formado!")
                            self.add_message("Nêutron (Up, Down, Down) formado!")
                            
        # Aplica as remoções e adições
        self.stable_particles = [p for p in self.stable_particles if p not in particles_to_remove]
        self.stable_particles.extend(new_particles)

    def run_quantum_decay_check(self, decay_chance):
        """
        Calcula a probabilidade de decaimento usando o gerador de números aleatórios padrão (random).
        
        Args:
            decay_chance (float): A probabilidade desejada de decaimento (entre 0 e 1).
            
        Returns:
            bool: True se o decaimento ocorreu.
        """
        # Esta é a checagem padrão, sem o overhead de compilação e execução do Qiskit.
        return random.random() < decay_chance

    def run_quantum_decay_check_qiskit(self, decay_chance):
        """
        Calcula a probabilidade de decaimento usando um circuito quântico (Qiskit).
        
        Args:
            decay_chance (float): A probabilidade desejada de decaimento (entre 0 e 1).
            
        Returns:
            bool: True se o decaimento ocorreu (medida '1'), False caso contrário.
        """
        # Limita a probabilidade para evitar erros de domínio em arcsin (ex: chance > 1.0)
        P1 = min(max(decay_chance, 0.0), 1.0)
        
        # Calcula o ângulo de rotação R_Y: theta = 2 * arcsin(sqrt(P1))
        if P1 <= 0:
            angle = 0
        else:
            angle = 2 * math.asin(math.sqrt(P1))
        
        qc = QuantumCircuit(1, 1)
        # Aplica a rotação R_Y para colocar o qubit no estado |1> com probabilidade P1
        qc.ry(angle, 0)
        # Realiza a medição
        qc.measure(0, 0)
        
        # Compila e executa no simulador (self.sim = AerSimulator())
        compiled_circuit = transpile(qc, self.sim)
        # Roda apenas 1 shot, pois queremos simular o resultado único para este frame
        job = self.sim.run(compiled_circuit, shots=1)
        result = job.result()
        counts = result.get_counts(qc)
        
        # Se a medição for '1', o decaimento ocorreu
        return '1' in counts

    # NOVO: Implementação completa do decaimento de quarks e nêutrons
    def check_for_quantum_decay(self):

        # >>> NOVO: LÓGICA DE PULAR FRAMES PARA A CHECAGEM QUÂNTICA <<<
        # A checagem pesada (Qiskit) só deve rodar a cada N frames.
        QUANTUM_DECAY_FREQUENCY = 10 # Roda 10 vezes mais devagar (a cada 10 frames)

        self.quantum_decay_counter += 1
        
        if self.quantum_decay_counter < QUANTUM_DECAY_FREQUENCY:
            return # Sai do método sem fazer a checagem de decaimento
            
        # Se chegamos aqui, é hora de rodar o Qiskit
        self.quantum_decay_counter = 0 
        
        particles_to_remove = []
        new_particles = []
        
        # Chance por frame para decaimento (~1 minuto de meia-vida a 60 FPS)
        NEUTRON_DECAY_CHANCE = 0.0005  
        # Chance por frame para decaimento do Strange
        STRANGE_DECAY_CHANCE = 0.002
        # Chance por frame para decaimento do Lambda
        LAMBDA_DECAY_CHANCE = 0.005
        # Chance por frame para decaimento do Pion minus
        PION_DECAY_CHANCE = 0.01 # Chance muito alta de decaimento (ex: 1% por checagem)
        # Chance por frame para decaimento do Pion minus
        MUON_DECAY_CHANCE = 0.002
        
        for p in self.stable_particles:
            
            # 1. Decaimento Beta do Nêutron (Neutron -> Proton + Electron)
            if p.particle_type == "Neutron" and self.run_quantum_decay_check(NEUTRON_DECAY_CHANCE):
                particles_to_remove.append(p)
                # Cria um Próton no lugar
                new_particles.append(StableParticle(p.x, p.y, (255, 255, 0), "Proton", vx=p.vx, vy=p.vy))
                # Cria um Elétron (Beta)
                new_particles.append(StableParticle(p.x + 5, p.y + 5, (0, 255, 0), "Electron", vx=random.uniform(-1, 1), vy=random.uniform(-1, 1)))
                print("Decaimento Beta: Nêutron -> Próton + Elétron (e Antineutrino, simplificado)")
                self.add_message("Decaimento Beta: Nêutron -> Próton + Elétron (e Antineutrino, simplificado)")
                # Faísca para representar a energia liberada
                for _ in range(5): self.sparks.append(QuantumSpark(p.x, p.y, (100, 100, 255)))
                
            # 2. Decaimento do Quark Estranho (Strange -> Up/Down)
            elif p.particle_type == "Quark_STRANGE" and self.run_quantum_decay_check(STRANGE_DECAY_CHANCE):
                particles_to_remove.append(p)
                
                # Strange decai principalmente para UP (cerca de 94% de chance)
                if random.random() < 0.94:
                    new_type = "Quark_UP"
                    new_color = self.get_color_for_state("Red")
                else:
                    new_type = "Quark_DOWN"
                    new_color = self.get_color_for_state("Blue")

                # Cria o novo Quark (mais leve)
                new_particles.append(StableParticle(p.x, p.y, new_color, new_type, vx=p.vx, vy=p.vy))
                
                # Energia liberada (W boson, leptons, etc.) simplificada para um fóton
                self.photons.append(Photon(p.x, p.y))
                print(f"Decaimento Fraco: Quark Estranho -> {new_type.replace('Quark_', '')}")
                self.add_message(f"Decaimento Fraco: Quark Estranho -> {new_type.replace('Quark_', '')}")
            
            # 3. Decaimento do Bárion Lambda (Lambda -> Proton + Pion Negativo)
            elif p.particle_type == "Lambda" and self.run_quantum_decay_check(LAMBDA_DECAY_CHANCE):
                particles_to_remove.append(p)
                
                # Cria um Próton (carga +1, cor amarela)
                new_particles.append(StableParticle(p.x, p.y, (255, 255, 0), "Proton", vx=p.vx, vy=p.vy))
                
                # Cria um Píon Negativo (carga -1, cor rosa para contraste)
                new_particles.append(StableParticle(p.x + 5, p.y + 5, (255, 100, 100), "Pion_MINUS", vx=random.uniform(-1, 1), vy=random.uniform(-1, 1)))

                print("Decaimento Fraco: Bárion Lambda -> Próton + Píon Negativo")
                self.add_message("Decaimento Fraco: Bárion Lambda -> Próton + Píon Negativo")
                # Faísca para representar a energia liberada
                for _ in range(10): self.sparks.append(QuantumSpark(p.x, p.y, (180, 0, 180)))

            # 5. Decaimento do Pion Minus (Pion -> Antineutrino + Muon Negativo)  
            elif p.particle_type == "Pion_MINUS" and self.run_quantum_decay_check(PION_DECAY_CHANCE):
                particles_to_remove.append(p)
                # Cria um Múon Negativo (cor diferente, ex: ciano)
                new_particles.append(StableParticle(p.x, p.y, (0, 255, 255), "Muon_MINUS", vx=p.vx, vy=p.vy))
                
                # Adicionamos uma faísca/fóton para o Antineutrino (invisível)
                self.photons.append(Photon(p.x, p.y)) 
                
                print("Decaimento Fraco: Píon Negativo -> Múon Negativo (+ Antineutrino, simplificado)")
                self.add_message("Decaimento Fraco: Píon Negativo -> Múon Negativo (+ Antineutrino, simplificado)")

            # 5 Decaimento do Muon Negativo (Muon -> Eletron + Antineutrino)  
            elif p.particle_type == "Muon_MINUS" and self.run_quantum_decay_check(MUON_DECAY_CHANCE):
                particles_to_remove.append(p)
                
                # Cria o Elétron! (o produto final da cadeia)
                # Lembre-se de dar uma velocidade de ejeção isótropa
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(1, 2)
                new_particles.append(StableParticle(p.x, p.y, (0, 255, 0), "Electron", 
                                                    vx=speed * math.cos(angle), 
                                                    vy=speed * math.sin(angle)))
                
                # Faísca para representar os neutrinos
                for _ in range(3): self.sparks.append(QuantumSpark(p.x, p.y, (0, 0, 255)))
                
                print("Decaimento Fraco Final: Múon Negativo -> Elétron (+ 2 Neutrinos, simplificado)")
                self.add_message("Decaimento Fraco Final: Múon Negativo -> Elétron (+ 2 Neutrinos, simplificado)")
                
        # Aplica as alterações
        self.stable_particles = [p for p in self.stable_particles if p not in particles_to_remove]
        self.stable_particles.extend(new_particles)

# -----------------------
# Visual (pygame)
# -----------------------

pygame.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT))

pygame.display.set_caption("Laboratório Quântico")
font = pygame.font.SysFont("Arial", 20)
clock = pygame.time.Clock()

def draw_hud(game):
    hud_x_offset = 20
    y_offset = 30
    
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
    for p_type in ["Proton", "Neutron", "Lambda", "Deuterium", "Deuterium Atom", "Hydrogen Atom", "Electron", "Positron"]:
        count = counts.get(p_type, 0)
        text = font.render(f"  {p_type}: {count}", True, (200, 200, 200))
        screen.blit(text, (hud_x_offset, y_offset))
        y_offset += 25
    
    y_offset += 15

    # Assume que a lista de fótons é game.photons
    photon_count = len(game.photons) 
    
    photon_title = font.render("Partículas de Campo", True, (0, 255, 255))
    screen.blit(photon_title, (hud_x_offset, y_offset))
    y_offset += 30
    
    photon_text = font.render(f"  Fótons: {photon_count}", True, (255, 255, 0)) # Fótons em amarelo para destaque
    screen.blit(photon_text, (hud_x_offset, y_offset))
    y_offset += 25
    
    y_offset += 15

    # Quarks
    quark_title = font.render("Quarks", True, (0, 255, 255))
    screen.blit(quark_title, (hud_x_offset, y_offset))
    y_offset += 30
    quark_types = ["Quark_UP", "Quark_DOWN", "Quark_STRANGE"]
    for q_type in quark_types:
        count = counts.get(q_type, 0)
        text = font.render(f"  {q_type.replace('Quark_', '')}: {count}", True, (150, 150, 150))
        screen.blit(text, (hud_x_offset, y_offset))
        y_offset += 25

    # Mesons
    meson_title = font.render("Mésons e Léptons Instáveis", True, (0, 255, 255)) # Renomeei o título para ser mais preciso
    screen.blit(meson_title, (hud_x_offset, y_offset))
    y_offset += 30
    quark_types = ["Pion_MINUS","Muon_MINUS"]
    for q_type in quark_types:
        count = counts.get(q_type, 0)
        # Substituí 'Meson_' por um prefixo vazio ou 'Pion'/'Muon' para simplificar a exibição:
        display_name = q_type.replace('Pion_MINUS', 'Píon-').replace('Muon_MINUS', 'Múon-') 
        text = font.render(f"  {display_name}: {count}", True, (150, 150, 150))
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

    # --- NOVO: Área de Log Dinâmico (Substituindo a DICA) ---
    
    log_line_height = 20
    max_log_lines = 3
    
    # Pega as últimas 'max_log_lines' mensagens (as mais recentes)
    messages_to_draw = game.message_log[-max_log_lines:] 
    
    # Desenha as mensagens de baixo para cima
    for i, msg in enumerate(reversed(messages_to_draw)):
        
        # 1. Calcula o fade-out (alpha)
        # O timer é definido na adição da mensagem; 60 frames = 1 segundo de fade
        # Assumindo que o game.message_duration seja 300 (5 segundos)
        alpha = min(255, int(255 * (msg['timer'] / 60)))
        
        # 2. Renderiza o texto
        text_surface = font.render(msg['text'], True, (255, 255, 255))
        text_surface.set_alpha(alpha)
        
        # 3. Calcula a posição centralizada na parte inferior da tela
        # As mensagens mais novas (i=0) ficam mais acima.
        y_pos = HEIGHT - 30 - (i * log_line_height) 
        text_rect = text_surface.get_rect(center=(WIDTH // 2, y_pos))
        
        # 4. Desenha na tela
        screen.blit(text_surface, text_rect)
    
    # --------------------------------------------------------


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
        clock.tick(30)

    pygame.quit()

if __name__ == "__main__":
    main()