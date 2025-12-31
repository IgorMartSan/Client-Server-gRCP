
import time
import random

import time
import random
from datetime import datetime


class UMTracker:
    def __init__(self, threshold=30, error_timeout=1800):
        self.last_um = None
        self.can_update_um = False
        self.last_tracking_percent = None
        self.error_start_time = None
        self.last_error_hour = None
        self.threshold = threshold
        self.error_timeout = error_timeout

    def update(self, tracking_percent, current_um):
        now = datetime.now()

        # --- Inicialização da UM ---
        if self.last_um is None:
            if current_um is not None:
                self.last_um = current_um
                print(f"[{now}] Primeira leitura válida. Inicializando UM com: {self.last_um}")
                return self.last_um
            else:
                current_hour = now.replace(minute=0, second=0, microsecond=0)
                self.last_um = f"ERRO_{current_hour.strftime('%Y-%m-%d %H:%M:%S')}"
                self.error_start_time = now
                self.last_error_hour = current_hour
                print(f"[{now}] Primeira leitura inválida. Inicializando UM com erro: {self.last_um}")
                return self.last_um

        # --- Se voltaram valores válidos depois de erro, troca direto ---
        if tracking_percent is not None and current_um is not None:
            if isinstance(self.last_um, str) and self.last_um.startswith("ERRO_"):
                self.last_um = current_um
                self.error_start_time = None
                self.last_error_hour = None
                print(f"[{now}] Dados voltaram após erro. Restaurando UM para: {self.last_um}")
                return self.last_um

            # Transição válida de percent
            if (self.last_tracking_percent is not None and
                self.last_tracking_percent <= self.threshold and
                tracking_percent > self.threshold):
                self.can_update_um = True
                print(f"[{now}] Transição detectada: {self.last_tracking_percent} -> {tracking_percent}")

            self.last_tracking_percent = tracking_percent

            if self.can_update_um and current_um != self.last_um:
                self.last_um = current_um
                self.can_update_um = False
                self.error_start_time = None
                self.last_error_hour = None
                print(f"[{now}] Nova linha criada com UM válido: {current_um}")
                return self.last_um

        # --- Se valores inválidos ---
        else:
            if self.error_start_time is None:
                self.error_start_time = now
                self.last_error_hour = None
                print(f"[{now}] Estado de erro iniciado")

            elapsed = (now - self.error_start_time).total_seconds()

            if elapsed > self.error_timeout:
                current_hour = now.replace(minute=0, second=0, microsecond=0)
                new_um = f"ERRO_{current_hour.strftime('%Y-%m-%d %H:%M:%S')}"
                if self.last_um != new_um:
                    self.last_um = new_um
                    self.last_error_hour = current_hour
                    print(f"[{now}] Erro persistente. Atualizando UM para: {self.last_um}")
                    return self.last_um

        return self.last_um



# Test class

# def simulate_tracker_behavior():
#     tracker = UMTracker(error_timeout=5)  # 15s em vez de 30min para teste rápido
#     total_steps = 100

#     for step in range(total_steps):
#         now = datetime.now()

#         # Simula diferentes fases com base no tempo
#         if step < 5:
#             # 0–5s: início sem dados (None)
#             tracking_percent = None
#             current_um = None
#         elif step < 15:
#             # 5–15s: dados válidos entram
#             tracking_percent = random.randint(0, 100)
#             current_um = f"UM_{random.randint(1, 50)}"
#         elif step < 50:
#             # 15–25s: perde comunicação novamente
#             tracking_percent = None
#             current_um = None
#         else:
#             # 25–40s: dados válidos voltam
#             tracking_percent = random.randint(0, 100)
#             current_um = f"UM_{random.randint(51, 99)}"

#         # Atualiza o tracker e imprime o valor de UM
#         result = tracker.update(tracking_percent, current_um)

#         print(f"[{now.strftime('%H:%M:%S')}] Step {step} | "
#               f"tracking: {tracking_percent} | current_um: {current_um} | result: {result}")

#         time.sleep(1)


# # Executa o teste (Ctrl+C para interromper manualmente)
# simulate_tracker_behavior()