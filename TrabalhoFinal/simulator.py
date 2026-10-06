import sys
import heapq

# Gerador Congruente Linear (Park-Miller) para alta qualidade
a = 16807
c = 0
m = 2147483647
x = 7
count = 0

def nextDouble():
    global x, count
    x = (a * x + c) % m
    count += 1
    return x / m

class Evento:
    def __init__(self, tipo, tempo, origem, destino):
        self.tipo = tipo
        self.tempo = tempo
        self.origem = origem
        self.destino = destino

    def __lt__(self, other):
        return self.tempo < other.tempo

class Rota:
    def __init__(self, destino, probabilidade):
        self.destino = destino
        self.probabilidade = probabilidade

class Fila:
    def __init__(self, nome, servidores, capacidade, minChegada, maxChegada, minAtendimento, maxAtendimento):
        self.nome = nome
        self.servidores = servidores
        self.capacidade = capacidade
        self.minChegada = minChegada
        self.maxChegada = maxChegada
        self.minAtendimento = minAtendimento
        self.maxAtendimento = maxAtendimento
        self.clientes = 0
        self.perda = 0
        self.maxStateReached = 0
        self.tempos = {}
        self.rotas = []

    def addRota(self, destino, probabilidade):
        self.rotas.append(Rota(destino, probabilidade))

    def sortearRota(self, rnd):
        soma = 0.0
        for r in self.rotas:
            soma += r.probabilidade
            if rnd < soma:
                return r
        return self.rotas[-1]

    def updateTempos(self, delta):
        if self.clientes not in self.tempos:
            self.tempos[self.clientes] = 0.0
        self.tempos[self.clientes] += delta

    def In(self):
        self.clientes += 1
        if self.clientes > self.maxStateReached:
            self.maxStateReached = self.clientes

    def Out(self):
        self.clientes -= 1

    def hasSpace(self):
        return self.clientes < self.capacidade

    def hasCustomersWaiting(self):
        return self.clientes >= self.servidores


def load_config(filename):
    """ Parser leve de YML para nao depender de pacotes externos como PyYAML """
    config = {'queues': {}, 'arrivals': {}}
    with open(filename, 'r') as f:
        current_section = ""
        current_queue = ""
        current_target = False
        for line in f:
            line = line.split('#')[0]
            if not line.strip():
                continue
            
            indent = len(line) - len(line.lstrip())
            trimmed = line.strip()
            
            if indent == 0:
                current_section = trimmed.replace(':', '')
            elif indent == 2:
                current_queue = trimmed.replace(':', '')
                if current_section == 'queues':
                    config['queues'][current_queue] = {'target': {}}
                elif current_section == 'arrivals':
                    config['arrivals'][current_queue] = {}
            elif indent == 4:
                if trimmed == 'target:':
                    current_target = True
                else:
                    current_target = False
                    key, val = [x.strip() for x in trimmed.split(':')]
                    if current_section == 'queues':
                        if key == 'capacity':
                            config['queues'][current_queue][key] = 100000 if val == 'INF' else int(val)
                        elif key == 'servers':
                            config['queues'][current_queue][key] = int(val)
                        else:
                            config['queues'][current_queue][key] = float(val)
                    elif current_section == 'arrivals':
                        config['arrivals'][current_queue][key] = float(val)
            elif indent == 6 and current_target:
                key, val = [x.strip() for x in trimmed.split(':')]
                config['queues'][current_queue]['target'][key] = float(val)
    return config

def imprimirResultados(f, tempoTotal):
    print("\n*********************************************************")
    print(f"Queue:   {f.nome}")
    print("*********************************************************")
    print("   State               Time               Probability")
    
    limite = f.maxStateReached if f.capacidade >= 100000 else f.capacidade
    for i in range(limite + 1):
        tempo = f.tempos.get(i, 0.0)
        prob = (tempo / tempoTotal) * 100.0
        # Formatando para manter exata mesma casa decimal de consistência
        print(f"      {i}        {tempo:15.4f}               {prob:6.2f}%")
    print(f"\nNumber of losses: {f.perda}")

def main():
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'config.yml'
    try:
        config = load_config(config_file)
    except Exception as e:
        print(f"Erro ao ler configuracao: {e}")
        return
    
    listaDeFilas = []
    mapFilas = {}
    
    # Inicializando objetos de Fila
    for qName, defs in config['queues'].items():
        arr_defs = config['arrivals'].get(qName, {})
        f = Fila(qName, 
                 defs['servers'], 
                 defs['capacity'], 
                 arr_defs.get('min', 0.0), 
                 arr_defs.get('max', 0.0), 
                 defs['minService'], 
                 defs['maxService'])
        mapFilas[qName] = f
        listaDeFilas.append(f)
        
    # Inicializando as Rotas de cada Fila
    for qName, defs in config['queues'].items():
        f = mapFilas[qName]
        for targetName, prob in defs['target'].items():
            if targetName == 'Out':
                f.addRota(None, prob)
            else:
                f.addRota(mapFilas[targetName], prob)
                
    eventos = []
    globalTime = 0.0
    global count
    
    for f in listaDeFilas:
        if f.maxChegada > 0:
            heapq.heappush(eventos, Evento('CHEGADA', 2.0, None, f))
            
    while eventos:
        e = heapq.heappop(eventos)
        
        delta = e.tempo - globalTime
        for f in listaDeFilas:
            f.updateTempos(delta)
        globalTime = e.tempo
        
        if e.tipo == 'CHEGADA':
            dest = e.destino
            if dest.maxChegada > 0:
                rArr = nextDouble()
                tArr = dest.minChegada + (dest.maxChegada - dest.minChegada) * rArr
                heapq.heappush(eventos, Evento('CHEGADA', globalTime + tArr, None, dest))
            
            if count >= 100000: break
            
            if dest.hasSpace():
                dest.In()
                if dest.clientes <= dest.servidores:
                    if count >= 100000: break
                    rota = dest.sortearRota(nextDouble())
                    if count >= 100000: break
                    
                    rServ = nextDouble()
                    tServ = dest.minAtendimento + (dest.maxAtendimento - dest.minAtendimento) * rServ
                    
                    if rota.destino is not None:
                        heapq.heappush(eventos, Evento('PASSAGEM', globalTime + tServ, dest, rota.destino))
                    else:
                        heapq.heappush(eventos, Evento('SAIDA', globalTime + tServ, dest, None))
                    if count >= 100000: break
            else:
                dest.perda += 1
                
        elif e.tipo == 'PASSAGEM':
            orig = e.origem
            dest = e.destino
            
            orig.Out()
            
            # Trata o proximo da origem
            if orig.hasCustomersWaiting():
                rota = orig.sortearRota(nextDouble())
                if count >= 100000: break
                rServ = nextDouble()
                tServ = orig.minAtendimento + (orig.maxAtendimento - orig.minAtendimento) * rServ
                if rota.destino is not None:
                    heapq.heappush(eventos, Evento('PASSAGEM', globalTime + tServ, orig, rota.destino))
                else:
                    heapq.heappush(eventos, Evento('SAIDA', globalTime + tServ, orig, None))
                if count >= 100000: break
                
            # Trata a entrada no destino
            if dest.hasSpace():
                dest.In()
                if dest.clientes <= dest.servidores:
                    rota = dest.sortearRota(nextDouble())
                    if count >= 100000: break
                    rServ = nextDouble()
                    tServ = dest.minAtendimento + (dest.maxAtendimento - dest.minAtendimento) * rServ
                    if rota.destino is not None:
                        heapq.heappush(eventos, Evento('PASSAGEM', globalTime + tServ, dest, rota.destino))
                    else:
                        heapq.heappush(eventos, Evento('SAIDA', globalTime + tServ, dest, None))
                    if count >= 100000: break
            else:
                dest.perda += 1
                
        elif e.tipo == 'SAIDA':
            orig = e.origem
            orig.Out()
            if orig.hasCustomersWaiting():
                rota = orig.sortearRota(nextDouble())
                if count >= 100000: break
                rServ = nextDouble()
                tServ = orig.minAtendimento + (orig.maxAtendimento - orig.minAtendimento) * rServ
                if rota.destino is not None:
                    heapq.heappush(eventos, Evento('PASSAGEM', globalTime + tServ, orig, rota.destino))
                else:
                    heapq.heappush(eventos, Evento('SAIDA', globalTime + tServ, orig, None))
                if count >= 100000: break

    for f in listaDeFilas:
        imprimirResultados(f, globalTime)
        
    print("\n=========================================================")
    print(f"Simulation average time: {globalTime:.4f}")
    print(f"Aleatorios consumidos: {count}")
    print("=========================================================\n")

if __name__ == "__main__":
    main()
