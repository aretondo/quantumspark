# Quantum Spark: Uma Jornada pelo Caos Quântico

![Gameplay do Quantum Spark](https://raw.githubusercontent.com/aretondo/quantumspark/main/docs/example1.jpg)
(https://raw.githubusercontent.com/aretondo/quantumspark/main/docs/example2.jpg)

## Resumo do Projeto

O **Quantum Spark** é um jogo de simulação e estratégia que explora conceitos da mecânica quântica e do caos de forma interativa. Nele, você manipula flutuações quânticas que emergem do vácuo, guia-as para colisão e testemunha a criação e aniquilação de matéria. Seu objetivo é estabilizar as partículas recém-formadas para construir estruturas atômicas mais complexas, como prótons, nêutrons e átomos de deutério, tudo isso enquanto gerencia o nível de caos do seu sistema.

A simulação é baseada em princípios como a **teoria da bifurcação** para gerar as flutuações e interações que imitam as forças fundamentais da natureza, como a força nuclear forte e a eletromagnética. É uma experiência visualmente rica e desafiadora que une ciência e diversão.

## Instalação e Execução

Para rodar o **Quantum Spark**, você precisará ter o Python 3.10 ou superior instalado em seu sistema, juntamente com as bibliotecas necessárias.

### Pré-requisitos
* **Python 3.10+**

### Passo a Passo

1.  **Clone o Repositório:**
    ```bash
    git clone [https://github.com/aretondo/quantumspark.git](https://github.com/aretondo/quantumspark.git)
    cd quantumspark
    ```

2.  **Instale as Dependências:**
    O projeto utiliza as bibliotecas `Pygame`, `Numpy` e `Qiskit`. Você pode instalá-las usando o `pip`:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Execute o Jogo:**
    Com as bibliotecas instaladas, inicie o jogo com o seguinte comando:
    ```bash
    python game_main.py
    ```

## Mecânicas de Interação

O coração do jogo está na intrincada rede de interações entre as partículas. O nível de caos (`r`) determina a frequência e o tipo de flutuações que aparecem, influenciando diretamente a sua estratégia.

### Flutuações Quânticas

* **Geração:** As flutuações emergem constantemente do vácuo quântico, cada uma com um "estado de cor" (vermelho, verde, azul) ou "antimatéria" (anti-vermelho, anti-verde, anti-azul). Elas se movem erraticamente e pulsam de acordo com o nível de caos.
* **Aniquilação Mútua:** Quando uma flutuação de matéria colide com sua antipartícula correspondente (ex: Vermelho e Anti-vermelho), elas se aniquilam e liberam energia na forma de **Faíscas Quânticas**.

### Criação de Partículas

* **Formação de Partículas Estáveis:** A matéria é criada quando flutuações de matéria e antimatéria com **estados de cor diferentes** colidem.
    * **Matéria x Antimatéria:** A colisão entre flutuações, como `Vermelho` e `Antiverde`, gera partículas estáveis de quarks.
    * **Pares Elétron-Pósitron:** Se as flutuações colidem e seus estados não resultam em um quark, elas podem formar um par de elétrons e pósitrons.
* **Decaimento Quântico:** As partículas criadas não são totalmente estáveis. Elas possuem um circuito quântico que, após um tempo, pode "colapsar" e fazer a partícula decair.

### Estabilização da Matéria

Seu principal objetivo é estabilizar a matéria antes que ela decaia ou seja aniquilada. Para isso, você precisa guiar as partículas recém-formadas para interagir entre si:

1.  **Aniquilação Elétron-Pósitron:** A colisão entre um **Elétron** e um **Pósitron** resulta em aniquilação, gerando **Fótons**. Esta é uma perda de matéria, mas uma fonte de energia.
2.  **Fusão Nuclear:** A força nuclear forte entra em ação quando partículas se aproximam o suficiente, permitindo a fusão:
    * **Próton + Nêutron = Núcleo de Deutério**
3.  **Formação de Átomos:** As forças eletromagnéticas permitem a formação de átomos:
    * **Núcleo de Deutério + Elétron = Átomo de Deutério**
4.  **Formação de Nêutrons:** Em um evento raro, três quarks podem se unir para formar um **Nêutron**.
5.  **Formação de Hidrogênio:** Um **Nêutron** podem capturar um elétron para formar um **Hidrogênio**.
