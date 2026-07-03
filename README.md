# 🔗 URL Pública / Swagger

> **Publicação pendente:** após criar o serviço no Render (seção [Implantação](#-implantação-deploy)), substitua os endereços abaixo pela URL fornecida pela plataforma.
>
> - **API:** `https://<seu-servico>.onrender.com`
> - **Swagger UI:** `https://<seu-servico>.onrender.com/docs`

---

# API de Otimização — Problema de Corte Unidimensional

API RESTful desenvolvida com **FastAPI** e **Google OR-Tools (CP-SAT)** para resolver o
**Problema de Corte Unidimensional** (*One-Dimensional Cutting Stock Problem*), minimizando
o número de barras padrão utilizadas para atender uma demanda de subpeças.

Projeto Final — Laboratório de Otimização, Ciências de Dados, UFC (2026.1).

## Sumário

- [Formulação Matemática](#-formulação-matemática)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Instalação e Execução Local](#-instalação-e-execução-local)
- [Autenticação](#-autenticação)
- [Endpoints](#-endpoints)
- [Exemplos de Requisição/Resposta](#-exemplos-de-requisiçãoresposta)
- [Testes Automatizados](#-testes-automatizados)
- [Confiabilidade (Time Limit)](#-confiabilidade-time-limit)
- [Implantação (Deploy)](#-implantação-deploy)

---

## 📐 Formulação Matemática

Formulação de **Kantorovich** para o Problema de Corte Unidimensional.

**Conjuntos e índices**

- `i ∈ {1, ..., m}`: itens de demanda solicitados pelos clientes.
- `j ∈ {1, ..., N}`: barras padrão de estoque disponíveis (N é um limite superior do
  número máximo de barras necessárias).

**Parâmetros**

- `L`: comprimento útil de cada barra padrão em estoque.
- `l_i`: comprimento necessário do item `i`.
- `d_i`: demanda total exigida do item `i`.

**Variáveis de decisão**

- `y_j ∈ {0, 1}`: indica se a barra `j` foi utilizada.
- `x_ij ∈ ℤ≥0`: quantidade de vezes que o item `i` é cortado na barra `j`.

**Modelo**

```
Minimizar   Z = Σ_j y_j                                            (1)

sujeito a:
            Σ_j x_ij ≥ d_i,            ∀ i ∈ {1, ..., m}           (2)
            Σ_i l_i * x_ij ≤ L * y_j,  ∀ j ∈ {1, ..., N}           (3)
            y_j ∈ {0, 1},              ∀ j ∈ {1, ..., N}           (4)
            x_ij ∈ ℤ≥0,                ∀ i, j                      (5)
```

- A restrição **(2)** garante que toda a demanda seja suprida.
- A restrição **(3)** garante que o comprimento total dos cortes em cada barra não
  exceda o comprimento útil `L` (a barra só pode receber cortes se `y_j = 1`).

O limite superior `N` é calculado dinamicamente por uma heurística gulosa
**First-Fit Decreasing (FFD)** (ver `src/solver.py`), o que reduz o tamanho do modelo
exato em relação a usar `N = Σ_i d_i` diretamente, mantendo a formulação exata acima.

O modelo é resolvido com o **CP-SAT Solver** do Google OR-Tools, com quebra de simetria
(`y_0 ≥ y_1 ≥ ... ≥ y_{N-1}`) para acelerar a busca.

---

## 📁 Estrutura do Projeto

```
projeto_corte_api/
├── src/
│   ├── api.py          # Configuração do FastAPI e endpoints
│   ├── schemas.py       # Validadores Pydantic de entrada e saída
│   ├── auth.py          # Controle de acesso (API Key)
│   ├── solver.py         # Modelagem matemática no Google OR-Tools
│   └── config.py         # Configurações e ambiente (.env)
├── tests/
│   ├── test_solver.py    # Testes unitários do modelo matemático
│   └── test_api.py       # Testes de integração das rotas
├── .env                 # Segredos locais (NÃO versionado)
├── .env.example          # Modelo de variáveis de ambiente
├── .gitignore
├── requirements.txt
├── pytest.ini
├── conftest.py
├── api_requests.http     # Exemplos de requisições (REST Client)
├── render.yaml           # Configuração de deploy no Render
└── README.md
```

---

## 🚀 Instalação e Execução Local

### Pré-requisitos
- Python 3.10+

### Passo a passo

```bash
# 1. Clonar o repositório
git clone <url-do-repositorio>
cd projeto_corte_api

# 2. Criar e ativar o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# 3. Instalar as dependências
pip install -r requirements.txt

# 4. Configurar variáveis de ambiente
cp .env.example .env
# Edite o .env e defina uma API_KEY própria

# 5. Executar a aplicação
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

A API estará disponível em `http://127.0.0.1:8000`, com documentação interativa
(Swagger) em `http://127.0.0.1:8000/docs`.

---

## 🔐 Autenticação

Este projeto utiliza a **Opção A: API Key**.

- Cabeçalho obrigatório: `X-API-Key`.
- O valor esperado é lido da variável `API_KEY` no `.env`.
- Requisições sem a chave, ou com uma chave incorreta, recebem **HTTP 403 Forbidden**.

Exemplo:

```bash
curl -X POST http://127.0.0.1:8000/otimizar \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <sua-chave>" \
  -d @payload.json
```

---

## 📡 Endpoints

| Método | Rota         | Autenticação | Descrição                                   |
|--------|--------------|:------------:|----------------------------------------------|
| GET    | `/health`    | Não          | Verifica se a API está online.               |
| POST   | `/otimizar`  | Sim (API Key)| Resolve o problema de corte unidimensional.  |

### `POST /otimizar`

**Corpo da requisição:**

- `comprimento_padrao` (float, > 0): comprimento útil `L` da barra padrão.
- `itens` (lista, mín. 1 item): cada item possui `id`, `comprimento` (> 0) e
  `quantidade` (> 0).
- `time_limit` (float, opcional): tempo máximo (s) de execução do solver. Se omitido,
  usa o padrão de 60s; o valor é sempre limitado a no máximo 120s.

**Validações aplicadas (Pydantic):**

- `comprimento_padrao` e `quantidade` de cada item devem ser estritamente positivos.
- Nenhum item pode ter `comprimento` maior que `comprimento_padrao`.
- Ids de itens devem ser únicos dentro da mesma requisição.
- Qualquer falha de tipagem ou de schema retorna **HTTP 422 Unprocessable Entity**.

---

## 📨 Exemplos de Requisição/Resposta

### Entrada

```json
{
  "comprimento_padrao": 3000,
  "itens": [
    { "id": "item_A", "comprimento": 1150, "quantidade": 3 },
    { "id": "item_B", "comprimento": 800, "quantidade": 4 },
    { "id": "item_C", "comprimento": 450, "quantidade": 5 }
  ]
}
```

### Resposta (200 OK)

```json
{
  "status_solver": "OPTIMAL",
  "tempo_execucao_segundos": 0.045,
  "barras_utilizadas": 4,
  "desperdicio_total_mm": 3100,
  "plano_corte": [
    {
      "barra_id": 1,
      "itens_cortados": [{ "item_id": "item_A", "quantidade": 2 }],
      "comprimento_utilizado": 2300,
      "sobra": 700
    }
  ]
}
```

Mais exemplos (sucesso e erros) estão disponíveis em [`api_requests.http`](./api_requests.http).

---

## 🧪 Testes Automatizados

O projeto contém **23 testes** (10 unitários do solver + 13 de integração da API),
cobrindo casos de otimização, validações de schema, limite de tempo e segurança.

```bash
pytest -v
```

**`tests/test_solver.py`** — casos unitários do modelo matemático:
- barra preenchida exatamente (sem desperdício);
- múltiplos itens combinados em uma barra;
- instância clássica com desperdício conhecido;
- verificação de atendimento total da demanda;
- verificação de que nenhuma barra excede `L`;
- status `OPTIMAL`/`FEASIBLE` em instâncias pequenas;
- consistência entre `barras_utilizadas` e o tamanho do `plano_corte`;
- respeito ao `time_limit` informado.

**`tests/test_api.py`** — testes de integração das rotas:
- `GET /health` retorna 200;
- `POST /otimizar` sem `X-API-Key` retorna 403;
- `POST /otimizar` com `X-API-Key` inválida retorna 403;
- `POST /otimizar` com `X-API-Key` válida retorna 200;
- validações Pydantic inválidas (comprimento negativo, item maior que a barra,
  quantidade zero, lista vazia, tipagem incorreta, ids duplicados) retornam 422;
- `time_limit` customizado é aceito e respeitado;
- `time_limit` acima do máximo permitido é limitado internamente pela API.

---

## ⏱️ Confiabilidade (Time Limit)

O solver CP-SAT é sempre configurado com `max_time_in_seconds`:

- Se o cliente não informar `time_limit`, é usado o padrão **60s**
  (`DEFAULT_TIME_LIMIT` no `.env`).
- Se o cliente informar um valor, ele é respeitado até o teto de **120s**
  (`MAX_TIME_LIMIT` no `.env`); valores maiores são automaticamente reduzidos ao teto.
- Quando o tempo se esgota antes da prova de otimalidade, a API retorna a melhor
  solução encontrada até então, com `status_solver = "FEASIBLE"` (em vez de
  `"OPTIMAL"`).

---

## ☁️ Implantação (Deploy)

O serviço deve ser publicado em um provedor de nuvem gratuito, por exemplo
[Render](https://render.com), [Railway](https://railway.app), [Fly.io](https://fly.io)
ou [Hugging Face Spaces](https://huggingface.co/spaces).

### Render (Web Service)

O repositório inclui um arquivo `render.yaml`, portanto o serviço pode ser criado como
um **Blueprint** no Render. A plataforma detectará automaticamente o comando de build,
o comando de inicialização, a versão do Python e as variáveis de ambiente necessárias.

1. Suba o repositório para o GitHub (verifique que `.env` **não** foi versionado).
2. Em Render, crie um **Web Service** apontando para o repositório.
3. Caso prefira criar o Web Service manualmente, configure:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn src.api:app --host 0.0.0.0 --port $PORT`
4. Em **Environment**, cadastre as variáveis do `.env.example`. Defina uma `API_KEY`
   forte e diferente da chave local — nunca commitar segredos.
5. Após o deploy, atualize a seção [URL Pública / Swagger](#-url-pública--swagger)
   no topo deste README com o link gerado (`https://<serviço>.onrender.com/docs`).

O mesmo fluxo se aplica a Railway e Fly.io (ajustando o comando de start ao
respectivo `Procfile`/`fly.toml`); no Hugging Face Spaces, use o SDK "Docker" com um
`Dockerfile` mínimo que instale `requirements.txt` e execute o `uvicorn`.
