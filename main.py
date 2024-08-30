# Autor: Marcos Bezner Rampaso
# Entrega 3 - Implementação de Linguagens de Programação
# Data: 29/08/2024
# Descrição: Programa principal que chama o analisador léxico, sintático e semântico.
#            O programa chama o analisador léxico e sintático, e caso a árvore sintática
#            não seja vazia, chama o analisador semântico.

import tppparser
import tppsema

if __name__ == "__main__":
    tppparser.main()
    if tppparser.root is not None and tppparser.root.children != ():
        # Análise semântica
        tppsema.root = tppparser.root
        tppsema.checkRules()  # Realiza a análise semântica
        tppsema.podaArvore()   # Realiza a poda da árvore sintática
