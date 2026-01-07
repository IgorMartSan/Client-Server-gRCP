# Client-Server-gRCP

## Objetivo
Este projeto demonstra a comunicacao gRPC com Protocol Buffers e aplica o mesmo padrao para inferencia de modelos de machine learning. Ha um servico base com os 4 tipos de RPC e um servico de inferencia para enviar imagem e receber bounding boxes e dados extras.

## O que foi feito para entender a comunicacao gRPC
- Servico base `CoreServices` com exemplos de Unary, Server Streaming, Client Streaming e Bidirectional Streaming.
- Cliente com chamadas de teste para cada tipo de RPC.
- Servico de inferencia com payload binario (imagem) e resposta estruturada (bbox, lista de defeitos, segmentacao opcional).
- Configuracao de tamanho maximo de mensagem para trafegar imagens.
- Execucao via containers para reproduzir o ambiente de rede.

## gRPC e Protocol Buffers (resumo)
- gRPC e um framework de RPC sobre HTTP/2, com suporte nativo a streaming e baixa latencia.
- Protocol Buffers (proto) define o contrato (mensagens e servicos). A partir do `.proto` sao gerados stubs para cliente e servidor.
- O contrato e a fonte de verdade: cliente e servidor conversam usando os mesmos tipos e servicos.

## Estrutura do projeto
- `client/` cliente de testes e chamadas gRPC.
- `server/` servidor gRPC base (CoreServices).
- `server_with_gpu/` servidor gRPC para inferencia com modelo (YOLO).
- `docker-compose.yml` sobe os containers e expõe portas.

## Protocolos (arquivos .proto)
### CoreServices (basico gRPC)
Arquivo: `server/src/protos/service.proto` e `client/src/protos/service.proto`

RPCs:
- `Ping`: Unary (req -> resp)
- `StreamNumbers`: Server Streaming (req -> stream de respostas)
- `UploadNumbers`: Client Streaming (stream de req -> resp)
- `Chat`: Bidirectional Streaming (stream <-> stream)

### InferenceMethods (ML)
Arquivo: `server_with_gpu/src/protos/inference.proto` e `client/src/protos/inference.proto`

RPC:
- `Infer`: Unary com `image_bytes` e parametros de inferencia, retorna lista de bbox, lista de defeitos e segmentacao opcional.

## Fluxo de comunicacao (alto nivel)
1) Cliente cria channel gRPC (HTTP/2).
2) Cliente usa o stub gerado pelo proto para chamar o metodo.
3) Servidor recebe a mensagem, processa e retorna a resposta tipada.
4) Para inferencia, o servidor decodifica bytes da imagem, roda o modelo e devolve os resultados.

## Como rodar (exemplo com Docker)
1) Subir os containers:
```
docker-compose up --build
```
2) Testes do servico base:
```
python client/src/main.py
```
3) Teste do servidor GPU:
```
python client/src/main_test_server_gpu.py
```

## Gerar stubs (proto -> Python)
Para regenerar os arquivos gerados a partir do `.proto`, use os comandos descritos em:
- `client/README.md`
- `server/README.md`
- `server_with_gpu/README.md`
