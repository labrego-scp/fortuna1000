import psutil
import time

# Monitorar uso da CPU e RAM
def monitor():
    while True:
        cpu_percent = psutil.cpu_percent(interval=1)  # Uso da CPU (%)
        memory = psutil.virtual_memory()  # Informações de memória
        ram_usage = memory.used / (1024 ** 2)  # Conversão para MB
        print(f"Uso de CPU: {cpu_percent}% | Uso de RAM: {ram_usage:.2f} MB")
        time.sleep(1)  # Intervalo de atualização

if __name__ == "__main__":
    monitor()
