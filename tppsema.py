# Autor: Marcos Bezner Rampaso
# Entrega 3 - Implementação de Linguagens de Programação
# Data: 29/08/2024
# Descrição: Analisador Semântico para a linguagem T++.
#            Verifica regras semânticas do código, como declaração de variáveis, funções, uso de variáveis e funções, etc.
#            Realiza a poda da árvore sintática para simplificar a análise semântica.
#            Gera a tabela de símbolos a partir da árvore sintática.
#            Gera avisos e erros de acordo com as regras semânticas da linguagem.
#            Realiza a análise semântica do código e a poda da árvore sintática.

import sys
import os
from sys import argv, exit
import logging
import ply.yacc as yacc

from tpplex import tokens
from mytree import MyNode
from anytree.exporter import DotExporter, UniqueDotExporter
from anytree import RenderTree, AsciiStyle, findall_by_attr
from myerror import MyError

# Configuração do logger para registrar mensagens de depuração
logging.basicConfig(
    level=logging.DEBUG,
    filename="sema.log",
    filemode="w",
    format="%(filename)10s:%(lineno)4d:%(message)s"
)
log = logging.getLogger()

# Inicialização do analisador de erros
error_handler = MyError('SemaErrors')

# Raiz da árvore sintática
root = None

# Tabela de erros de variáveis
variablesError = []

# Adiciona uma variável com erro na tabela de erros
def adicionaErroVariavel(name, scope):
    variablesError.append({
        'name': name,
        'scope': scope
    })

# Verifica se uma variável já tem um erro associado em um escopo específico
def variavelComErro(name, scope):
    for variable in variablesError:
        if variable['name'] == name and variable['scope'] == scope:
            return True
    return False

# Gera a tabela de símbolos a partir da árvore sintática
def tabelaDeSimbolos():
    res = findall_by_attr(root, "declaracao")
    variables = []
    for p in res:
        item = [node for pre, fill, node in RenderTree(p)]
        if item[1].name == "declaracao_variaveis":
            variable = processaVariavel(node1=item[1], scope="global")
            if declaracaoVariavel(table=variables, name=variable['name'], scope='global'):
                typeVar = buscaTipo(table=variables, name=variable['name'], scope='global')
                print(error_handler.newError(False, 'WAR-SEM-VAR-DECL-PREV').format(variable['name'], typeVar))
            else:
                variables.append(variable)
        elif item[1].name == "declaracao_funcao":
            if item[2].name == "tipo":
                name = item[7].name
                token = item[6].name
                type = item[4].name
                line = item[4].line
            else:
                name = item[4].name
                token = item[3].name
                type = 'vazio'
                line = item[4].line

            variable = {
                "declarationType": 'func',
                "type": type,
                "line": line,
                "token": token,
                "name": name,
                "scope": "global",
                "used": "S" if name == "principal" else "N",
                "dimension": 0,
                "sizeDimension1": 1,
                "sizeDimension2": 0,
                "parameters": declaracaoParams(item)
            }
            if declaracaoVariavel(table=variables, name=name, scope='global'):
                typeVar = buscaTipo(table=variables, name=name, scope='global')
                print(error_handler.newError(False, 'WAR-SEM-FUNC-DECL-PREV').format(name, typeVar))
            else:
                variables.append(variable)
                declaracaoFunc(node1=item[1], scope=name, table=variables)
    return variables

# Gera a lista de parâmetros de uma função a partir da árvore sintática
def declaracaoParams(node1):
    parametros = []
    for item in node1:
        if item.name == 'cabecalho':
            # Obtém a lista de parâmetros
            lista_parametros = findall_by_attr(item.children[2], "parametro")
            for parametro in lista_parametros:
                # Extrai o tipo e o nome do parâmetro
                tipo = parametro.children[0].children[0].children[0].name
                nome = parametro.children[2].children[0].name
                parametros.append({
                    'type': tipo,
                    'name': nome
                })
    return parametros

# Processa a declaração de variáveis dentro do escopo de uma função
def declaracaoFunc(node1, scope, table):
    res = findall_by_attr(node1, "declaracao_variaveis")
    for p in res:
        variable = processaVariavel(node1=p, scope=scope)
        if declaracaoVariavel(table=table, name=variable['name'], scope=scope):
            typeVar = buscaTipo(table=table, name=variable['name'], scope=scope)
            print(error_handler.newError(False, 'WAR-SEM-VAR-DECL-PREV').format(variable['name'], typeVar))
        else:
            table.append(variable)

# Processa a declaração de uma variável, determinando suas propriedades
def processaVariavel(node1, scope):
    d1 = 1
    d2 = 0
    dimension = 0
    renderNodeTree = [node for pre, fill, node in RenderTree(node1)]
    for i in range(len(renderNodeTree)):
        if renderNodeTree[i].name == 'tipo':
            type = renderNodeTree[i+2].name
            line = renderNodeTree[i+2].line
        elif renderNodeTree[i].name == 'ID':
            token = renderNodeTree[i].name
            name = renderNodeTree[i+1].name
        elif renderNodeTree[i].name == 'fecha_colchete':
            dimension += 1
            if renderNodeTree[i-2].name == 'NUM_PONTO_FLUTUANTE':
                if not variavelComErro(name, scope):
                    adicionaErroVariavel(name, scope)
                    print(error_handler.newError(False, 'ERR-SEM-ARRAY-INDEX-NOT-INT').format(name))
            index = renderNodeTree[i-1].name
            if dimension == 2:
                d2 = index
            else:
                d1 = index

    variable = {
        'declarationType': 'var',
        'type': type,
        'line': line,
        'token': token,
        'name': name,
        'scope': scope,
        'init': 'N',
        'used': 'N',
        'dimension': dimension,
        'sizeDimension1': d1,
        'sizeDimension2': d2,
        'errors': 0
    }

    return variable

# Verifica se a função principal ("principal") existe na tabela de símbolos
def existeMain(table):
    for entry in table:
        if entry['declarationType'] == 'func' and entry['name'] == 'principal':
            return True
    return False

# Verifica se uma variável está declarada na tabela de símbolos dentro de um escopo específico
def declaracaoVariavel(table, name, scope):
    for entry in table:
        # Verifica se a variável está no escopo global ou no escopo especificado
        if entry['name'] == name and (entry['scope'] == 'global' or entry['scope'] == scope):
            return True
        # Verifica se a variável é um parâmetro de função no escopo especificado
        elif scope != 'global' and entry['declarationType'] == 'func':
            for param in entry['parameters']:
                if param['name'] == name:
                    return True
    return False

# Retorna o tipo de uma variável ou parâmetro de acordo com a tabela de símbolos
def buscaTipo(table, name, scope):
    for entry in table:
        # Verifica se a variável está no escopo global ou no escopo especificado
        if entry['name'] == name and (entry['scope'] == 'global' or entry['scope'] == scope):
            return entry['type']
        # Verifica se a variável é um parâmetro de função no escopo especificado
        elif scope != 'global' and entry['declarationType'] == 'func':
            for param in entry['parameters']:
                if param['name'] == name:
                    return param['type']
    return None

# Obtém o escopo de uma função a partir de um nó na árvore sintática
def buscaEscopo(node):
    for ancestor in node.anchestors:
        if ancestor.name == 'cabecalho' and ancestor.children[0].name == 'ID':
            return ancestor.children[0].children[0].name
    return 'global'

# Verifica se um valor está sendo usado como índice em uma expressão
def verificaIndice(node):
    return any(ancestor.name == 'indice' for ancestor in node.anchestors)

# Verifica se um valor está sendo usado como argumento em uma função
def verificaArgumento(node):
    anchestors = list(node.anchestors)
    for i in range(len(anchestors)):
        if anchestors[i].name == 'lista_argumentos':
            return True
    return False

# Obtém os fatores (variáveis, números ou funções) de uma expressão
def buscaFator(node1, table, scope):
    res = findall_by_attr(node1, "fator")
    factors = []
    for p in res:
        # Filtra fatores que não são índices ou argumentos de função
        if not verificaIndice(p) and not verificaArgumento(p):
            factor = p.children[0].name
            factor = factor if factor != 'chamada_funcao' else 'func'
            
            value = p.children[0].children[0].children[0].name
            type = p.children[0].children[0].name
            real_scope = scope if factor != 'func' else 'global'
            # Determina o tipo do fator, seja ele uma variável, número ou função
            type = ('inteiro' if type == 'NUM_INTEIRO' else 'flutuante') if factor == 'numero' else buscaTipo(table, value, real_scope)
            
            if type is not None:
                factors.append({
                    'factor': factor,
                    'type': type,
                    'value': value
                })
    return factors

# Verifica se todos os fatores de uma expressão são do mesmo tipo; caso contrário, retorna o tipo predominante
def buscaTipoFator(factors, type):
    type_factor = type
    for factor in factors:
        if factor['type'] != type:
            type_factor = factor['type']
    return type_factor

# Conta o número de parâmetros em uma lista de argumentos
def contagemParametros(node):
    i = 1
    item = node
    while item.name == 'lista_argumentos':
        if item.name == 'lista_argumentos' and len(item.children) > 1 and item.children[1].name == 'VIRGULA':
            i += 1
        item = item.children[0]
    return i

# Verifica coerções de tipos em atribuições e operações, emitindo avisos se necessário
def verificarCoercao(table, name, scope, node):
    factors = buscaFator(node, table, scope)
    type = None
    for i in range(len(table)):
        type = None
        try:
            parameters = table[i]['parameters']
        except KeyError:
            parameters = None

        # Verifica o tipo da variável ou parâmetro na tabela de símbolos
        if table[i]['name'] == name and (table[i]['scope'] == 'global' or table[i]['scope'] == scope):
            type = table[i]['type']
        elif parameters is not None and len(parameters) > 0:
            for parameter in parameters:
                if parameter['name'] == name:
                    type = parameter['type']
        
        if type is not None:
            # Se a expressão contém um único fator, verifica se o tipo precisa de coerção
            if len(factors) == 1:
                type_factor = factors[0]['type']
                if type_factor != type:
                    value_factor = factors[0]['value']
                    factor = factors[0]['factor']
                    if factor == 'var':
                        print(error_handler.newError(False, 'WAR-SEM-ATR-DIFF-TYPES-IMP-COERC-OF-VAR').format(value_factor, type_factor, name, type))
                    elif factor == 'func':
                        print(error_handler.newError(False, 'WAR-SEM-ATR-DIFF-TYPES-IMP-COERC-OF-RET-VAL').format(value_factor, type_factor, name, type))
                    else:
                        print(error_handler.newError(False, 'WAR-SEM-ATR-DIFF-TYPES-IMP-COERC-OF-NUM').format(value_factor, type_factor, name, type))
            else:
                # Se a expressão contém múltiplos fatores, determina o tipo predominante
                type_factor = buscaTipoFator(factors, type)
                if type_factor != type:
                    value_factor = 'expressao'
                    print(error_handler.newError(False, 'WAR-SEM-ATR-DIFF-TYPES-IMP-COERC-OF-EXP').format(value_factor, type_factor, name, type))

# Inicializa a variável na tabela de símbolos e verifica coerção de tipos
def inicializarVariavel(table, name, scope, node):
    if declaracaoVariavel(table=table, name=name, scope=scope):
        verificarCoercao(table=table, name=name, scope=scope, node=node)
        for i in range(len(table)):
            if table[i]['name'] == name and (table[i]['scope'] == 'global' or table[i]['scope'] == scope):
                table[i]['init'] = 'Y'  # Marca a variável como inicializada
    else:
        # Se a variável não está declarada, verifica se não é uma chamada de função antes de reportar erro
        res = findall_by_attr(node, 'chamada_funcao')
        if not res and not variavelComErro(name, scope):
            adicionaErroVariavel(name, scope)
            print(error_handler.newError(False, 'ERR-SEM-VAR-NOT-DECL').format(name))

# Marca a variável como usada na tabela de símbolos
def variavelUsada(table, name, scope, node):
    if declaracaoVariavel(table=table, name=name, scope=scope):
        for i in range(len(table)):
            if table[i]['name'] == name and (table[i]['scope'] == 'global' or table[i]['scope'] == scope):
                table[i]['used'] = 'Y'  # Marca a variável como usada
    else:
        # Se a variável não está declarada, verifica se não é uma chamada de função antes de reportar erro
        res = findall_by_attr(node, 'chamada_funcao')
        if not res and not variavelComErro(name, scope):
            adicionaErroVariavel(name, scope)
            print(error_handler.newError(False, 'ERR-SEM-VAR-NOT-DECL').format(name))

# Verifica todas as variáveis em uso no código, identificando e inicializando ou marcando-as como usadas
def verificarVariavel(table):
    res = findall_by_attr(root, "acao")
    for p in res:
        renderNodeTree = [node for pre, fill, node in RenderTree(p)]
        for node1 in renderNodeTree:
            renderNode1Tree = [node for pre, fill, node in RenderTree(node1)]
            if node1.name == 'expressao':
                if renderNode1Tree[1].name == 'atribuicao':
                    scope = buscaEscopo(node1)
                    name = renderNode1Tree[4].name
                    inicializarVariavel(table=table, name=name, scope=scope, node=node1)
                else:
                    for index in range(len(renderNode1Tree)):
                        if renderNode1Tree[index].name == 'ID':
                            scope = buscaEscopo(node1)
                            name = renderNode1Tree[index+1].name
                            variavelUsada(table=table, name=name, scope=scope, node=node1)
            elif node1.name == 'leia':
                for index in range(len(renderNode1Tree)):
                    if renderNode1Tree[index].name == 'ID':
                        scope = buscaEscopo(node1)
                        name = renderNode1Tree[index+1].name
                        inicializarVariavel(table=table, name=name, scope=scope, node=node1)
            elif node1.name in ['se', 'repita', 'escreva', 'retorna']:
                for index in range(len(renderNode1Tree)):
                    if renderNode1Tree[index].name == 'ID':
                        scope = buscaEscopo(node1)
                        name = renderNode1Tree[index+1].name
                        variavelUsada(table=table, name=name, scope=scope, node=node1)
            elif node1.name == 'chamada_funcao':
                scope = buscaEscopo(node1)
                name = node1.children[0].children[0].name
                variavelUsada(table=table, name=name, scope=scope, node=node1)

# Verifica se as variáveis declaradas estão em uso, e se foram inicializadas corretamente
def variavelEmUso(table):
    for i in range(len(table)):
        name = table[i]['name']
        scope = table[i]['scope']
        if table[i]['declarationType'] == 'var' and table[i]['errors'] <= 0 and not variavelComErro(name, scope):
            if table[i]['init'] == 'N' and table[i]['used'] == 'N':
                print(error_handler.newError(False, 'WAR-SEM-VAR-DECL-NOT-USED').format(name))
            elif table[i]['init'] == 'Y' and table[i]['used'] == 'N':
                print(error_handler.newError(False, 'WAR-SEM-VAR-DECL-INIT-NOT-USED').format(name))
            elif table[i]['init'] == 'N':
                print(error_handler.newError(False, 'WAR-SEM-VAR-DECL-NOT-INIT').format(name))

# Verifica se as funções têm o retorno adequado ao seu tipo declarado
def buscaRetornoFuncao(table):
    res = findall_by_attr(root, 'declaracao_funcao')
    for p in res:
        renderNodeTree = [node for pre, fill, node in RenderTree(p)]
        for node1 in renderNodeTree:
            if node1.name == 'cabecalho':
                renderNode1Tree = [node for pre, fill, node in RenderTree(node1)]
                returns = findall_by_attr(node1, 'retorna')
                funcName = renderNode1Tree[2].name
                if not returns:
                    for i in range(len(table)):
                        if table[i]['name'] == funcName and table[i]['declarationType'] == 'func' and table[i]['type'] != 'vazio':
                            print(error_handler.newError(False, 'ERR-SEM-FUNC-RET-TYPE-ERROR').format(funcName, table[i]['type'], 'vazio'))
                else:
                    for return1 in returns:
                        if return1.children:
                            expression = return1.children[2]
                            if expression.name == 'expressao':
                                scope = buscaEscopo(return1)
                                factors = buscaFator(expression, table, scope)
                                for i in range(len(table)):
                                    if table[i]['name'] == funcName and table[i]['declarationType'] == 'func':
                                        type = table[i]['type']
                                        type_factor = buscaTipoFator(factors, type)
                                        if type_factor != type:
                                            print(error_handler.newError(False, 'ERR-SEM-FUNC-RET-TYPE-ERROR').format(funcName, type, type_factor))

# Verifica se as funções são chamadas corretamente e se os argumentos correspondem aos parâmetros
def verificaChamada(table):
    res = findall_by_attr(root, 'chamada_funcao')
    for p in res:
        renderNodeTree = [node for pre, fill, node in RenderTree(p)]
        name = renderNodeTree[2].name
        if declaracaoVariavel(table=table, name=name, scope='global'):
            scopeCall = buscaEscopo(p)
            if name == 'principal':
                if scopeCall == 'principal':
                    print(error_handler.newError(False, 'WAR-SEM-CALL-REC-FUNC-MAIN').format(name))
                print(error_handler.newError(False, 'ERR-SEM-CALL-FUNC-MAIN-NOT-ALLOWED'))
            else:
                node1 = renderNodeTree[5]
                if node1.name == 'lista_argumentos':
                    if node1.children[0].name != 'vazio':
                        numberArguments = contagemParametros(node1)
                        for i in range(len(table)):
                            if table[i]['name'] == name and table[i]['declarationType'] == 'func':
                                parameters = table[i]['parameters']
                                if numberArguments < len(parameters):
                                    print(error_handler.newError(False, 'ERR-SEM-CALL-FUNC-WITH-FEW-ARGS').format(name))
                                elif numberArguments > len(parameters):
                                    print(error_handler.newError(False, 'ERR-SEM-CALL-FUNC-WITH-MANY-ARGS').format(name))
        else:
            print(error_handler.newError(False, 'ERR-SEM-CALL-FUNC-NOT-DECL').format(name))

# Verifica se as funções declaradas foram usadas em algum ponto do código
def verificaUsoFuncao(table):
    for i in range(len(table)):
        if table[i]['declarationType'] == 'func':
            name = table[i]['name']
            if table[i]['used'] == 'N':
                print(error_handler.newError(False, 'WAR-SEM-FUNC-DECL-NOT-USED').format(name))

# Realiza as verificações de retorno, chamada e uso de funções
def verificarFuncoes(table):
    buscaRetornoFuncao(table)
    verificaChamada(table)
    verificaUsoFuncao(table)

# Função principal para verificar as regras semânticas do código
def checkRules():
    table = tabelaDeSimbolos()
    if not existeMain(table):
        print(error_handler.newError(False, 'ERR-SEM-MAIN-NOT-DECL'))
    verificarVariavel(table)
    variavelEmUso(table)
    verificarFuncoes(table)

# Lista de tokens relevantes para a poda
string_tokens = [
    'ID',
    'ABRE_PARENTESE',
    'FECHA_PARENTESE',
    'FIM',
    'abre_colchete',
    'fecha_colchete'
]

# Função principal para podar a lista de declarações
def podaDeclaracoes(tree):
    item = tree.children[0]
    dec = ()
    
    # Navega pela lista de declarações, acumulando nós relevantes
    while item.name == 'lista_declaracoes':
        if item.name == 'lista_declaracoes':
            if len(item.children) == 1:
                node = item.children[0]
            else:
                node = item.children[1]
            dec = node.children + dec
        item = item.children[0]
    
    # Realiza a poda em cada tipo de declaração
    for i in dec:
        if i.name == 'declaracao_funcao':
            PodaDeclaracaoFuncao(i)
        elif i.name == 'declaracao_variaveis':
            podaDeclaracaoVariavel(i)
        else:
            podaInicilizacaoVariavel(i)
    
    # Atualiza os filhos da árvore com as declarações podadas
    tree.children[0].children = dec

# Função para podar a declaração de função
def PodaDeclaracaoFuncao(tree):
    dec = ()
    
    # Caso a função tenha apenas um nó filho
    if len(tree.children) == 1:
        dec += tree.children[0].children
    else:
        dec += tree.children[0].children[0].children
        # Processa os filhos da função
        for child in tree.children[1].children:
            if child.name in string_tokens:
                dec += child.children
            elif child.name == 'corpo':
                dec += (podaCorpo(child),)
            elif child.name == 'lista_parametros':
                item = child
                dec1 = ()
                # Poda da lista de parâmetros
                while item.name == 'lista_parametros':
                    if item.children[0].name == 'vazio':
                        aux = item.children[0]
                        dec1 = (aux,) + dec1
                    elif len(item.children) == 1:
                        dec1 = (podaParametros(item.children[0]),) + dec1
                    else:
                        dec1 = (podaParametros(item.children[2]),) + dec1
                    item = item.children[0]
                child.children = dec1
                dec += (child,)
            else:
                dec += (child,)
    
    # Atualiza os filhos da árvore com a função podada
    tree.children = dec

# Função para podar a declaração de variáveis
def podaDeclaracaoVariavel(tree):
    dec = ()
    
    # Adiciona o tipo da variável e sua inicialização
    dec += tree.children[0].children[0].children
    dec += tree.children[1].children

    # Processa a lista de variáveis
    dec1 = ()
    item = tree.children[2]
    while item.name == 'lista_variaveis':
        if item.name == 'lista_variaveis':
            if len(item.children) == 1:
                dec1 = (podaVariavel(item.children[0]),) + dec1
            else:
                dec1 = (podaVariavel(item.children[2]),) + dec1
        item = item.children[0]
    
    # Atualiza a lista de variáveis podada
    tree.children[2].children = dec1
    dec += (tree.children[2],)
    
    # Retorna a declaração de variável podada
    tree.children = dec
    return tree

# Função para podar a inicialização de variáveis
def podaInicilizacaoVariavel(tree):
    podaInicializacao(tree.children[0])

# Função para podar uma inicialização de variável
def podaInicializacao(tree):
    dec = ()
    dec += (podaVariavel(tree.children[0]),)
    dec += (tree.children[1].children[0],)
    
    # Poda da expressão de inicialização
    tree.children[2].children = podaExpressao(tree.children[2])
    dec += (tree.children[2],)
    
    # Atualiza a árvore com a inicialização podada
    tree.children = dec
    return tree

# Função para podar uma variável
def podaVariavel(tree):
    aux = tree
    dec = ()
    dec1 = ()

    dec += (aux.children[0].children[0],)
    
    # Verifica se a variável é um array (possui colchetes)
    if len(aux.children) > 1:
        aux1 = aux.children[1].children
        
        # Poda do array com dois colchetes
        if len(aux.children[1].children) == 4:
            dec1 += aux1[0].children[0].children
            aux1[0].children[1].children = podaExpressao(aux1[0].children[1])
            dec1 += (aux1[0].children[1],)
            dec1 += aux1[0].children[2].children
            dec1 += aux1[1].children
            aux1[2].children = podaExpressao(aux1[2])
            dec1 += (aux1[2],)
            dec1 += aux1[3].children
        else:
            dec1 += aux1[0].children
            aux1[1].children = podaExpressao(aux1[1])
            dec1 += (aux1[1],)
            dec1 += aux1[2].children
        
        # Atualiza os filhos da variável com a expressão podada
        aux.children[1].children = dec1
        dec += (aux.children[1],)
    
    # Atualiza a árvore com a variável podada
    tree.children = dec
    return tree

# Função para podar expressões
def podaExpressao(tree):
    aux = tree.children
    name = tree.name
    
    # Condensa a expressão em uma forma mais simples
    while len(aux) == 1 and name != 'expressao_unaria':
        name = aux[0].name
        aux = aux[0].children
    
    dec = ()
    
    # Verifica se a expressão é unária
    if aux[0].parent.name == 'expressao_unaria':
        if len(aux) == 1:
            if aux[0].children[0].name == 'chamada_funcao':
                dec += (podaChamadaFuncao(aux[0].children[0]),)
            elif aux[0].children[0].name == 'var':
                dec += (podaVariavel(aux[0].children[0]),)
            elif aux[0].children[0].name == 'numero':
                dec += aux[0].children[0].children
            else:
                dec += aux[0].children[0].children
                dec += podaExpressao(aux[0].children[1])
                dec += aux[0].children[2].children
        else:
            dec += aux[0].children[0].children
            dec += aux[1].children[0].children
        aux = dec
    else:
        dec += podaExpressao(aux[0])
        dec += (aux[1].children[0].children[0],)
        dec += podaExpressao(aux[2])
        aux = dec
    
    # Retorna a expressão podada
    return aux

# Função para podar a chamada de função
def podaChamadaFuncao(tree):
    dec = ()
    
    # Processa a chamada de função com base nos filhos
    if len(tree.children) == 1:
        dec += tree.children[0].children
    else:
        dec += tree.children[0].children[0].children
        for child in tree.children:
            if child.name in string_tokens:
                dec += child.children
            elif child.name == 'lista_argumentos':
                item = child
                dec1 = ()
                # Poda da lista de argumentos
                while item.name == 'lista_argumentos':
                    if item.children[0].name == 'vazio':
                        aux = item.children[0]
                        dec1 = (aux,) + dec1
                    elif len(item.children) == 1:
                        aux = item.children[0]
                        aux.children = podaExpressao(item.children[0])
                        dec1 = (aux,) + dec1
                    else:
                        aux = item.children[2]
                        aux.children = podaExpressao(item.children[2])
                        dec1 = (aux,) + dec1
                    item = item.children[0]
                child.children = dec1
                dec += (child,)
            else:
                dec += (child,)
    
    # Retorna a chamada de função podada
    tree.children = dec
    return tree

# Função para podar a lista de parâmetros de uma função
def podaParametros(tree):
    dec = ()
    item = tree
    
    # Itera sobre os parâmetros e os condensa
    while item.name == 'parametro':
        if item.children[0].name == 'parametro':
            dec = item.children[2].children + dec
            dec = item.children[1].children + dec
        else:
            dec = item.children[2].children + dec
            dec = item.children[1].children + dec
            dec = item.children[0].children[0].children + dec
        item = item.children[0]
    
    # Atualiza a árvore com os parâmetros podados
    tree.children = dec
    return tree

# Função para podar as funções de entrada e saída (leia, escreva, retorna)
def podaFuncoesEntradaSaida(tree):
    dec = ()
    
    # Adiciona o token inicial e a expressão/variável correspondente
    dec += tree.children[0].children
    dec += tree.children[1].children
    
    # Verifica se é a função 'leia'
    if tree.name == 'leia':
        dec += (podaVariavel(tree.children[2]),)
    else:
        tree.children[2].children = podaExpressao(tree.children[2])
        dec += (tree.children[2],)
    
    # Adiciona o token final
    dec += tree.children[3].children
    
    # Atualiza a árvore com a função podada
    tree.children = dec
    return tree

# Função para podar a estrutura de controle 'se'
def podaSe(tree):
    dec = ()
    
    # Adiciona o token 'SE' e a expressão condicional
    dec += tree.children[0].children
    tree.children[1].children = podaExpressao(tree.children[1])
    dec += (tree.children[1],)
    
    # Adiciona o token 'ENTAO' e o corpo correspondente
    dec += tree.children[2].children
    dec += (podaCorpo(tree.children[3]),)
    
    # Verifica se há um bloco 'SENAO'
    if len(tree.children) == 5:
        dec += (tree.children[4],) # Adiciona 'FIM'
    else:
        dec += (tree.children[4],) # Adiciona 'SENAO'
        dec += (podaCorpo(tree.children[5]),) # Adiciona corpo do 'SENAO'
        dec += (tree.children[6],) # Adiciona 'FIM'
    
    # Atualiza a árvore com a estrutura 'se' podada
    tree.children = dec
    return tree

# Função para podar a estrutura de repetição 'repita'
def podaRepita(tree):
    dec = ()
    
    # Adiciona o token 'REPITA' e o corpo correspondente
    dec += tree.children[0].children
    dec += (podaCorpo(tree.children[1]),)
    
    # Adiciona o token 'ATE' e a expressão condicional
    dec += tree.children[2].children
    tree.children[3].children = podaExpressao(tree.children[3])
    dec += (tree.children[3],)
    
    # Atualiza a árvore com a estrutura 'repita' podada
    tree.children = dec
    return tree

# Função para podar o corpo das funções e estruturas
def podaCorpo(tree):
    dec = ()
    item = tree
    
    # Itera sobre o corpo da função/estrutura
    while item.name == 'corpo':
        if len(item.children) == 2:
            action = item.children[1].children[0]
            
            # Identifica o tipo de ação e realiza a poda correspondente
            if action.name == 'expressao':
                if action.children[0].name == 'atribuicao':
                    dec = (podaInicializacao(action.children[0]),) + dec
                else:
                    action.children = podaExpressao(action)
                    dec = (action,) + dec
            elif action.name == 'declaracao_variaveis':
                dec = (podaDeclaracaoVariavel(action),) + dec
            elif action.name == 'se':
                dec = (podaSe(action),) + dec
            elif action.name == 'repita':
                dec = (podaRepita(action),) + dec
            else:
                dec = (podaFuncoesEntradaSaida(action),) + dec
        
        # Passa para o próximo nó
        item = item.children[0]
    
    # Atualiza a árvore com o corpo podado
    tree.children = dec
    return tree

# Função principal para iniciar a poda da árvore
def podaArvore():
    tree = root
    podaDeclaracoes(tree)
    UniqueDotExporter(tree).to_picture("prunedTree.png")

# Função principal do programa
def main():
    if(len(sys.argv) < 2):
        raise TypeError(error_handler.newError(False, 'ERR-SEM-USE'))
    
    aux = argv[1].split('.')
    
    # Verifica se o arquivo fornecido é do tipo '.tpp'
    if aux[-1] != 'tpp':
        raise IOError(error_handler.newError(False, 'ERR-SEM-NOT-TPP'))
    elif not os.path.exists(argv[1]):
        raise IOError(error_handler.newError(False, 'ERR-SEM-FILE-NOT-EXISTS'))
    else:
        # Lê o arquivo fonte
        data = open(argv[1])
        source_file = data.read()

if __name__ == "__main__":
    main()
