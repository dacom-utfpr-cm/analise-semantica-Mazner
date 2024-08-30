# Compilador para a linguagem Tpp

## Descrição

O código contido nesse repositório se diz respeito a um compilador feito para a linguagem Tpp, onde existem 4 funções principais para executar o processo
de compilação, sendo elas:
- Análise léxica (tpplex.py);
- Análise sintática (tppparser.py);
- Análise semântica (tppsema.py);
- Geração de código (Em construção).

## Funcionalidades

O código será capaz de gerar código para a llvm, podendo ser então compilado e executado de uma linguagem tpp para linguagem executável

## Pré-requisitos

- Biblioteca Ply e yacc;
- Anytree

## Instalação

- Para instalar o projeto basta clonar o repositório em sua máquina e instalar as dependências descritas nos pre requisitos
através dos comandos pip install <nome_da_biblioteca>. (Recomenda-se utilizar um ambiente virtual de python).

## Uso

Para executar o projeto, basta executar o seguinte comando no terminal:
python main.py tests/<nome_do_arquivo_de_teste>
